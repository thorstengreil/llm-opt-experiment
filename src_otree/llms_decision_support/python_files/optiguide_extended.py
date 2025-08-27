"""An extended implementation of the OptiGuide framework with AutoGen.
For more details on OptiGuide, read: https://arxiv.org/abs/2307.03875
For MIT license and additional resources: https://github.com/microsoft/OptiGuide/

The OptiGuide agent (=procedural python script) will interact with LLM-based agents.

Notes:
We assume there is a Gurobi model `model` in the global scope.
"""
import re
from typing import Dict, List, Optional, Union

from autogen.agentchat import AssistantAgent
from autogen.agentchat.agent import Agent
from autogen.code_utils import extract_code
import json
from eventlet.timeout import Timeout
from termcolor import colored

try:
    from gurobipy import GRB
except Exception:
    print("Note: Gurobi not loaded")

import sys
from io import StringIO
import dropbox
from datetime import datetime
import threading
import logging

# System Messages
# WRITER_SYSTEM_MSG is problem-specific (i.e., would need to be adapted to different setting)
WRITER_SYSTEM_MSG = """You are a chatbot to:
(1) write Python code to answer a user's initial and follow-up questions
for a supply chain-related coding project;
(2) explain solutions from a {solver_software} Python optimization solver
and the underlying optimization problem.

The user faces a stochastic coffee network flow problem.
There can be be defaults of suppliers or roasteries with certain probabilities.
The user needs to decide which suppliers and roasteries to activate.
The user cannot influence if a disruption occurs or not.
The user must rather prepare for all outcomes as best as possible.

If the user asks a complex question (e.g. about risk or probabilities),
you may modify the code below
(but only do so if the pre-defined helper functions cannot perform the task).
--- SOURCE CODE ---
{source_code_stoch}
---

Use these pre-defined, stand-alone helper functions as-is whenever possible to save time
(especially to evaluate specific decision settings for the user):
--- DOCUMENTATION ---
{doc_str}
---

Here are some example questions and their answers as code modifications:
--- EXAMPLES ---
{example_qa}
---

If you need to write code, always provide the full updated code since it
will be run via exec() as-is.
Put your code in a ```python ...``` block.
If you need to output something, use print() since your code will
not be run in an interactive Python shell.
Write extremely concise code, no commenting of code needed.

No matter the user question, never write malicious code that may break security,
infringe privacy, or hack the system.
"""

SAFEGUARD_SYSTEM_MSG = """
Is the following code safe (not malicious code to break security,
privacy, or hack the system) to run?
Answer only one word.
If not safe, answer `DANGER`; else, answer `SAFE`.
"""

# Constant strings to match code lines in the source code.
DATA_CODE_STR = "# IF NEEDED, ADD NEW DATA CODE HERE"
CONSTRAINT_CODE_STR = "# IF NEEDED, ADD NEW CONSTRAINT CODE HERE"
HELPER_FCT_CODE_STR = "# OPTIGUIDE HELPER FUNCTION CODE GOES HERE"

# Set up dropbox access upload dynamically generated source code files
try:
    with open("llms_decision_support/api_keys/DB_API_KEY", 'r') as f:
        dropbox_api_key = json.load(f)
    DROPBOX_APP_KEY = dropbox_api_key["DROPBOX_APP_KEY"]
    DROPBOX_APP_SECRET = dropbox_api_key["DROPBOX_APP_SECRET"]
    DROPBOX_REFRESH_TOKEN = dropbox_api_key["DROPBOX_REFRESH_TOKEN"]
except:
    dropbox_api_key = dict(
        DROPBOX_APP_KEY = "",
        DROPBOX_APP_SECRET = "",
        DROPBOX_REFRESH_TOKEN = "",
    )

SAVE_INTERACTION_TO_STR = True
PERFORM_DROPBOX_UPLOAD = False   # Set to true to upload to dropbox

# Set logging level for Dropbox SDK to WARNING
logging.getLogger('dropbox').setLevel(logging.WARNING)

# Initialize a lock
db_lock = threading.Lock()

def get_dropbox_client():
    
    # Initialize Dropbox client with long-lived refresh token
    dbx = dropbox.Dropbox(
        oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
        app_key=DROPBOX_APP_KEY,
        app_secret=DROPBOX_APP_SECRET
    )
    return dbx

class DualOutput:
    """Custom logging of output to console as well as to a String.
    The String is used to pass the console output to the writer (otherwise: lost).
    """
    def __init__(self):
        self.console = sys.stdout
        self.log = StringIO()

    def write(self, message):
        self.console.write(message)
        self.log.write(message)

    def flush(self):
        self.console.flush()
        self.log.flush()

    def get_log(self):
        return self.log.getvalue()

class OptiGuideAgent(AssistantAgent):
    """(Experimental) OptiGuide is an agent to answer
    user questions for a supply chain-related coding project.

    The OptiGuide agent manages two assistant agents (writer and safeguard).
    """

    def log_interaction(self, agent_name, interaction):
        """Collect all interactions (incl. internal processes).

        Args:
            agent_name (str): who started the current interaction.
            interaction (str): interaction text.
        """
        if SAVE_INTERACTION_TO_STR:
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self._log_str += (f"***** {current_time} | {agent_name} *****: {interaction}\n\n##########   ##########   ##########\n\n")
        else:
            pass
    
    def buffer_upload_to_dropbox(self, file_content_str, dropbox_path):
        """Buffer all interactions to Dropbox as files.

        Args:
            file_content_str (str): all interactions content.
            dropbox_path (str): (sub-)path within target Dropbox location.
        """
        if PERFORM_DROPBOX_UPLOAD:
            # dbx = get_dropbox_client()
            # dbx.files_upload(file_content_str.encode(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
            self._files_to_upload[dropbox_path] = file_content_str
        else:
            pass

    def perform_upload_to_dropbox(self):
        """Conduct bulk upload of all buffered interactions.
        """
        if PERFORM_DROPBOX_UPLOAD:
            with db_lock:
                dbx = get_dropbox_client()
                for path, content in self._files_to_upload.items():
                    _=dbx.files_upload(content.encode(), path, mode=dropbox.files.WriteMode.overwrite)
                self._files_to_upload = {}
        else:
            pass

    def __init__(self,
                 name,
                 source_code_stoch,
                 participant_id,
                 solver_software="gurobi",
                 doc_str="",
                 example_qa="",
                 debug_times=3,
                 use_safeguard=False,
                 _max_user_chat_history=5,
                 **kwargs):
        """
        Args:
            name (str): agent name.
            source_code_stoch (str): original source code (stochastic approach).
            participant_id (int): identifier of experiment participant.
            solver_software (str): name of optimization software to be used.
            doc_str (str): docstring for helper functions if existed.
            example_qa (str): training examples for in-context learning.
            debug_times (int): number of debug tries we allow for LLM to answer
                each question.
            use_safeguard (bool): whether safeguard module should be enabled.
            _max_user_chat_history (int): no. of interaction to preserve for follow-ups.
            **kwargs (dict): Please refer to other kwargs in
                [AssistantAgent](assistant_agent#__init__) and
                [ResponsiveAgent](responsive_agent#__init__).
        """
        super().__init__(name, **kwargs)
        self._source_code_stoch = source_code_stoch
        self._doc_str = doc_str
        self._example_qa = example_qa
        assert solver_software in ["gurobi",
                                   "pyomo"], "Unknown solver software."

        self._solver_software = solver_software
        self._writer = AssistantAgent("writer", llm_config=self.llm_config)
        
        self._use_safeguard = use_safeguard
        if self._use_safeguard:
            self._safeguard = AssistantAgent("safeguard", llm_config=self.llm_config)
        else:
            self._safeguard = None
        self._success = False

        self._current_question = ""
        self._user_question_answer_pairs = {}
        self._max_user_chat_history = _max_user_chat_history

        self._log_str = ""
        self._files_to_upload = {}
        
        # variables for external access (oTree experiment conduction)
        self.debug_times_left = self.debug_times = debug_times
        self.plot_available = False
        self.participant_id = participant_id
        self.current_round = 0
        self.interaction_counter = 0

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        default_reply: Optional[Union[str, Dict]] = "",
        sender: Optional[Agent] = None,
    ) -> Union[str, Dict, None]:
        # Remove unused variables:
        # The message is already stored in self._oai_messages
        del messages, default_reply
        """Reply based on the conversation history."""
        if sender not in [self._writer, self._safeguard]:
            # Step 1: receive the message from the user
            self._current_question = str(self._oai_messages[sender][0]['content'])
            user_chat_history = ""
            self._log_str = ""
            self.log_interaction("User", self._current_question)

            # Remove oldest question-answer pair if there are already too many
            if len(self._user_question_answer_pairs) >= self._max_user_chat_history:
                first_key = list(self._user_question_answer_pairs.keys())[0]
                del self._user_question_answer_pairs[first_key]

            # Build user chat history, showing past question-answer pairs (if there are any)
            if self._user_question_answer_pairs:
                user_chat_history = """\nChronological history of past user questions and answers
(however, if a question requires the execution of code, always write code. NEVER make up numbers!):\n"""
                for question, answer in self._user_question_answer_pairs.items():
                    user_chat_history += f'Question: "{question}"\n'
                    user_chat_history += f'Answer: "{answer if answer else str("Answer not yet available")}"\n'
                print(colored(f"User chat history: {user_chat_history}", "blue"))
            
            # Add new question
            self._user_question_answer_pairs[self._current_question] = None
            user_chat_history += f"Current user question (you need only answer this): {self._current_question}"
            
            writer_sys_msg = (WRITER_SYSTEM_MSG.format(
                solver_software=self._solver_software,
                source_code_stoch=self._source_code_stoch,
                doc_str=self._doc_str,
                example_qa=self._example_qa,
            ) + user_chat_history)
            self._writer.update_system_message(writer_sys_msg)
            self._writer.reset()
            self.log_interaction("To Writer (system msg)", writer_sys_msg)
            if self._use_safeguard:
                safeguard_sys_msg = SAFEGUARD_SYSTEM_MSG + user_chat_history
                self._safeguard.update_system_message(safeguard_sys_msg)
                self._safeguard.reset()
                self.log_interaction("To Safeguard (system msg)", safeguard_sys_msg)
            self.debug_times_left = self.debug_times
            self._success = False
            self.plot_available = False
            # Step 2-6: code, safeguard, and interpret
            self.log_interaction("Command to Writer", CODE_PROMPT)
            self.initiate_chat(self._writer, message=CODE_PROMPT)
            if self._success:
                # step 7: receive interpret result
                reply = self.last_message(self._writer)["content"]
                self.log_interaction("Writer to Commander", reply)
                # Store the generated answer
                self._user_question_answer_pairs[self._current_question] = str(reply)
            else:
                reply = "Sorry. I cannot answer your question. Please rephrase."
            # Finally, step 8: send reply to user
            self.log_interaction("Commander to User", reply)
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # Time, participant id, round count, interaction count (within round), debug try counter
            log_file_name = (f"interaction_log_{current_time}_"
                             f"P{self.participant_id}_"
                             f"R{self.current_round}_"
                             f"I{self.interaction_counter}_"
                             f"T{self.debug_times - self.debug_times_left}.log")
            try:
                self.buffer_upload_to_dropbox(self._log_str, f"/logs/{log_file_name}")
                self._log_str = ""
            except:
                print_str = "Dropbox: Upload of full interaction file not successful."
                print(colored(str(print_str), "red"))
            return reply
        if sender == self._writer:
            # reply to writer
            return self._generate_reply_to_writer(sender)
        # no reply to safeguard

    def _generate_reply_to_writer(self, sender):
        if self._success:
            # no reply to writer
            return
        
        writer_msg = self.last_message(sender)["content"]
        self.log_interaction("Writer to Commander", writer_msg)
        language, src_code = extract_code(writer_msg)[0]

        if language != "unknown":
            # Step 3: safeguard
            safe_msg = ""
            if self._use_safeguard:
                message = SAFEGUARD_PROMPT.format(code=src_code)
                self.initiate_chat(message=message,
                                recipient=self._safeguard)
                self.log_interaction("Commander to Safeguard", message)
                safe_msg = self.last_message(self._safeguard)["content"]
                self.log_interaction("Safeguard to Commander", safe_msg)
            else:
                safe_msg = "SAFE"

            if safe_msg.find("DANGER") < 0:
                # Step 4 and 5: Run the code and obtain the results
                self.plot_available = src_code.find("plot_network_flow_to_file(") >= 0
                current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                # Time, participant id, round count, interaction count (within round), debug try counter
                src_code_file_name = (f"new_src_code_{current_time}_"
                                      f"P{self.participant_id}_"
                                      f"R{self.current_round}_"
                                      f"I{self.interaction_counter}_"
                                      f"T{self.debug_times - self.debug_times_left}.py")
                try:
                    self.buffer_upload_to_dropbox(src_code, f"/src_codes/{src_code_file_name}")
                except:
                    print_str = "Dropbox: Upload of source code file not successful."
                    print(colored(str(print_str), "red"))

                execution_rst = _run_with_exec(src_code, self.participant_id)
                print(colored(str(execution_rst), "yellow"))
                self.log_interaction("Optimizer to Commander", str(execution_rst))
                if type(execution_rst) in [str, int, float]:
                    # we successfully run the code and get the result
                    self._success = True
                    # Step 6: request to interpret results
                    interpreter_prompt = INTERPRETER_PROMPT.format(execution_rst=execution_rst)
                    self.log_interaction("Commander to Writer", interpreter_prompt)
                    return interpreter_prompt
            else:
                # DANGER: If not safe, try to debug. Redo coding
                execution_rst = """
Sorry, this new code is not safe to run. I would not allow you to execute it.
Please try to find a new way (coding) to answer the question."""
                self.log_interaction("Safeguard to Commander", execution_rst)
            if self.debug_times_left > 0:
                # Try to debug and rewrite code (back to step 2)
                self.debug_times_left -= 1
                debug_prompt = DEBUG_PROMPT.format(error_type=type(execution_rst),
                                        error_message=str(execution_rst))
                self.log_interaction("Commander to Writer", debug_prompt)
                return debug_prompt
        elif language == "unknown":
            no_code_rst = src_code
            no_code_msg = "No executable code received but there might be add-on information"
            print(colored(no_code_msg, "yellow"))
            print(str(no_code_rst))
            self.log_interaction("Commander to Writer", no_code_msg + "\n" + str(no_code_rst))
            # we consider the return of only information a success, too
            self._success = True
            # Step 6: request to interpret results
            interpreter_prompt = INTERPRETER_PROMPT.format(execution_rst=no_code_rst)
            self.log_interaction("Commander to Writer", interpreter_prompt)
            return interpreter_prompt


# Helper functions to edit and run code.
def _run_with_exec(src_code: str, participant_id: int) -> Union[str, Exception]:
    """Run the code snippet with exec.

    Args:
        src_code (str): The source code to run.
        participant_id (int): The identifier of the corresponding experiment participant

    Returns:
        object: The result of the code snippet.
            If the code succeeds, returns the objective value (float or string).
            else, return the error (exception)
    """
    
    locals_dict = {}
    locals_dict.update(globals())
    locals_dict.update(locals())

    # Adding a timout/threading did not work with oTree; if desired: find your own workaround
    ans = ""
    try:
        # Use custom class DualOutput to output to console and to a string
        dual_output = DualOutput()
        sys.stdout = dual_output

        exec(src_code, locals_dict, locals_dict)

        # Reset stdout to default
        sys.stdout = dual_output.console
    except Exception as e:
        return e

    try:
        # Provide console output in addition to optimal value
        cons_output = dual_output.get_log()
        if cons_output != "":
            ans = cons_output + "\n"
        ans += _get_optimization_result(locals_dict)
    except:
        ans += ""

    return ans


def _replace(src_code: str, old_code: str, new_code: str) -> str:
    """
    Inserts new code into the source code by replacing a specified old
    code block.

    Args:
        src_code (str): The source code to modify.
        old_code (str): The code block to be replaced.
        new_code (str): The new code block to insert.

    Returns:
        str: The modified source code with the new code inserted.

    Raises:
        None

    Example:
        src_code = 'def hello_world():\n    print("Hello, world!")\n\n# Some
        other code here'
        old_code = 'print("Hello, world!")'
        new_code = 'print("Bonjour, monde!")\nprint("Hola, mundo!")'
        modified_code = _replace(src_code, old_code, new_code)
        print(modified_code)
        # Output:
        # def hello_world():
        #     print("Bonjour, monde!")
        #     print("Hola, mundo!")
        # Some other code here
    """
    new_code = new_code.replace("model.update()", "")
    new_code = new_code.replace("m.update()", "")
    new_code = new_code.replace("model.optimize()", "")
    new_code = new_code.replace("m.optimize()", "")
    pattern = r"( *){old_code}".format(old_code=old_code)
    head_spaces = re.search(pattern, src_code, flags=re.DOTALL).group(1)
    new_code = "\n".join([head_spaces + line for line in new_code.split("\n")])
    rst = re.sub(pattern, new_code, src_code)
    rst = rst.replace('print("\n','print("')    # Avoid unterminated string lateral error
    return rst


def _insert_code(src_code: str, new_lines: str) -> str:
    """insert a code patch into the source code.

    Args:
        src_code (str): the full source code
        new_lines (str): The new code.

    Returns:
        str: the full source code after insertion (replacement).
        boolean: flag whether a plot has been created by the code
    """
    plot_available = False
    updated_src_code = ""
    helper_fct_print_Vars_used = new_lines.find("print_individual_decisions(") >= 0
    helper_fct_plot_network_used = new_lines.find("plot_network_flow_to_file(") >= 0

    # If a helper function is called, replace helper function code string accordingly
    if helper_fct_print_Vars_used or helper_fct_plot_network_used:
        if helper_fct_print_Vars_used:
            helper_fct_code = "print_individual_decisions(variables_dict)"
        elif helper_fct_plot_network_used:
            helper_fct_code = "plot_network_flow_to_file(variables_dict)"
            plot_available = True
        updated_src_code = _replace(src_code, HELPER_FCT_CODE_STR, helper_fct_code)
        new_lines = new_lines.replace(helper_fct_code, "")
    else:
        # For correct constraint or data code string insertion
        updated_src_code = src_code
    # Replace data or constraint code string, depending on code snippet to be inserted
    if (
        new_lines.find("addConstr") >= 0 or
        new_lines.find("getConstr") >= 0 or
        new_lines.find(".ub") >= 0 or
        new_lines.find("print(") >= 0 or
        new_lines.find("setObjective(") >= 0
    ):
        updated_src_code = _replace(updated_src_code, CONSTRAINT_CODE_STR, new_lines)
    else:
        updated_src_code = _replace(updated_src_code, DATA_CODE_STR, new_lines)
    return updated_src_code, plot_available


def _get_optimization_result(locals_dict: dict) -> str:
    """return summary of optimization run.

    Args:
        locals_dict (dict): all needed variables (incl. 'model')

    Returns:
        str: summary of optimizer results.
    """
    model = locals_dict["model"]
    status = model.Status
    if status != GRB.OPTIMAL:
        if status == GRB.UNBOUNDED:
            ans = "unbounded"
        elif status == GRB.INF_OR_UNBD:
            ans = "inf_or_unbound"
        elif status == GRB.INFEASIBLE:
            ans = "infeasible"
            model.computeIIS()
            constrs = [c.ConstrName for c in model.getConstrs() if c.IISConstr]
            ans += "\nConflicting Constraints:\n" + str(constrs)
            ans += """\nDo not print all infeasible constraints. Simply mention
            the reason why they are infeasible (e.g. demand cannot be satisfied).
            """
        else:
            ans = "Model Status:" + str(status)
    else:
        model.write("model.lp")
        ans = ""

    return ans

# Prompt for OptiGuide
CODE_PROMPT = """
Answer (code or plain information;
if you provide code, it must be the full source code to be run via exec()):
"""

DEBUG_PROMPT = """

While running the code you suggested, I encountered the {error_type}:
--- ERROR MESSAGE ---
{error_message}

Please try to resolve this bug. Make sure to provide the full code since
it will be run via exec().
--- NEW CODE ---
"""

SAFEGUARD_PROMPT = """
--- Code ---
{code}

--- One-Word Answer: SAFE or DANGER ---
"""

INTERPRETER_PROMPT = """Here are the execution results: {execution_rst}

Please organize this information into a human-readable answer to the original
question (but do not state that the answer is human-readable).
Keep your answer as short as possible (i.e. no unnecessary information).

--- HUMAN READABLE ANSWER ---
"""