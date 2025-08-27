from otree.api import *
from llms_decision_support.python_files.constants import C
from .. import Player
from .. import players_agent_dict
from llms_decision_support.python_files.coffee_deterministic_evaluation import evaluate_deterministic
from autogen.agentchat import UserProxyAgent
from .optiguide_extended import OptiGuideAgent      # local modified version
from .optiguide_extended import _replace
import json
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
from io import StringIO

class DummyAgent:
    """Empty hull with necessary variables in case LLM access is disabled.
    """
    def __init__(self, source_code_det="", source_code_stoch="", participant_id=-1, **kwargs):
        self._source_code_stoch = source_code_stoch
        self.participant_id = participant_id
        self.debug_times = 2
        self.debug_times_left = self.debug_times
        self.plot_available = False
        self.current_round = 0
        self.interaction_counter = 0
    
    def perform_upload_to_dropbox(self):
        # Do nothing
        pass

def get_participant_id(player: Player):
    """Get participant identifier.

    Args:
        player (Player): Reference to player for which ID is desired.

    Returns:
        int: identifying number of participant.
    """
    return player.participant.id_in_session

def setup_llm_framework(player: Player):
    """Configure LLM access for participant with chat access upfront.

    Args:
        player (Player): Reference to experiment participant.
    """
    global players_agent_dict
    participant_id = get_participant_id(player)

    # Create agent setting
    players_agent_dict[participant_id] = {}

    players_agent_dict[participant_id]["agent"] = OptiGuideAgent(
        name="optiGuide_coffee_network_flow",
        source_code_stoch=C.SRC_CODE_STOCH,
        participant_id=participant_id,
        debug_times=2,
        doc_str=C.HELPER_DOC,
        example_qa=C.EXAMPLE_QA,
        use_safeguard=False,
        # Define model here, instead of in OAI_CONFIG_LIST (due to gitignore for license key)
        llm_config={
            "seed": 42,
            "config_list": [],
                                             # context len;  cost per 1 m tokens of input (output)  (as of Dec 2024)
            "model": "gpt-4o"                # 128 k tokens; USD 5 (USD 15)
            #"model": "gpt-4-turbo"          # 128 k tokens; USD 10 (USD 30)
            #"model": "gpt-4"                # 8 k tokens;   USD 30 (USD 60)
            #"model": "gpt-4-32k"            # 32 k tokens;  USD 60 (USD 120)
            #"model": "gpt-3.5-turbo-0125"   # 16 k tokens;  USD 0.5 (USD 1.5)
        }   # 1 m tokens = ca. 1300 pages
    )

    players_agent_dict[participant_id]["user"] = UserProxyAgent(
        "user",
        max_consecutive_auto_reply=0,
        human_input_mode="NEVER",
        code_execution_config=False
    )

def get_llm_answer(player: Player):
    """Get answer from LLM-optimization framework.

    Args:
        player (Player): Reference to experiment participant.

    Returns:
        str: LLM-optimization framework answer as text.

    Note: To be able to send multiple LLM API requests in parallel,
    instead of sending and receiving sequentially, we tried to implement
    parallelization here, but failed (oTree does not allow it).
    Hence, with long API wait times (>30-45 s), a ConnectionClosed error can happen.
    """
    result = ""
    
    participant_id = get_participant_id(player)

    # Retrieve user and agent for current player from overall dictionary
    user = players_agent_dict[participant_id]["user"]
    agent = players_agent_dict[participant_id]["agent"]
    user_question = player.current_question_to_llm
    
    # Update interaction counter in agent
    agent.interaction_counter += 1

    if C.FLAG_LLM_ACTIVE:
        # Send question to OptiGuide framework
        user.initiate_chat(agent, message=user_question)
        last_msg = user.last_message(agent)["content"]
        result = last_msg
        player.number_of_debug_iterations = agent.debug_times - agent.debug_times_left
    else:
        # Dummy code to bypass LLM calls for development
        result = "Dummy answer (LLM framework is deactivated on purpose)"
    return result

def update_round_counter_in_agent(player: Player):
    """Update/reset round and interactions (=no. of questions) counter.

    Args:
        player (Player): Reference to experiment participant.
    """
    participant_id = get_participant_id(player)

    agent = players_agent_dict[participant_id]["agent"]
    
    # Update round and interaction counter in agent (however, we only play 1 round in our implementation)
    agent.current_round += 1
    agent.interaction_counter = 0

def create_disruption_risks_info(player: Player):
    """Get disruption probabilities.

    Args:
        player (Player): Reference to experiment participant.

    Returns:
        dict: nodes with their disruption risks as dict entries.
    """
    if C.FLAG_RANDOM_DISRUPTIONS:
        # Step 1: Determine a random integer between 1 and 4 with specified probabilities
        nr_of_defaults = np.random.choice([1, 2, 3], p=[1/3, 1/3, 1/3])             # max 3 nodes default

        # Step 2: Randomly draw 'nr_of_defaults' from the list without replacement
        nodes = list(C.SUPPLIERS) + list(C.ROASTERIES)
        selected_nodes = np.random.choice(nodes, nr_of_defaults, replace=False)

        # Step 3: Assign a random probability to each selected string
        probabilities = np.array([0.1, 0.2, 0.3, 0.4])
        selected_probabilities = np.random.choice(probabilities, nr_of_defaults, replace=True)

        # Step 4: Create a dictionary with the selected strings and their probabilities
        risks_unsorted = {nodes: prob for nodes, prob in zip(selected_nodes, selected_probabilities)}

        # Step 5: Sort the dictionary
        risks = sort_coffee_node_dict(risks_unsorted)
    else:
        risks = {
            "supplier1": 0.3,
            "roastery1": 0.1,
        }
    
    player.disruption_risks_info = json.dumps(risks)

    return risks

def sort_coffee_node_dict(input_dict):
    """Sort node dictinary for correct order.

    Args:
        input_dict (dict): Unsorted dictionary of nodes in network and their probabilities.

    Returns:
        dict: Sorted dictionary.
    """
    sorted_input = {key: input_dict[key] for key in sorted(input_dict)}
    result = {}
    for node, prob in sorted_input.items():
        if node in C.SUPPLIERS:
            result[node] = prob
    for node, prob in sorted_input.items():
        if node in C.ROASTERIES:
            result[node] = prob
    return result

def calculate_realized_profit(player: Player):
    """Based on randomness, determine realized profit.

    Args:
        player (Player): Reference to experiment participant.

    Returns:
        float: objective value for given disruption outcome.
    """
    decisions = json.loads(player.p1_decisions)
    disruption_risks_info = json.loads(player.disruption_risks_info)
    
    # Realize disruptions
    # Function to determine if an entity defaults based on its risk
    def determine_default(risk):
        # Create a random number generator
        rng = np.random.default_rng()
        return rng.random() < risk

    # Determine if each entity defaults
    p1_realized_disruptions = {entity: determine_default(risk) for entity, risk in disruption_risks_info.items()}
    
    # Sort disruptions dictionary
    p1_realized_disruptions = sort_coffee_node_dict(p1_realized_disruptions)

    player.p1_realized_disruptions = json.dumps(p1_realized_disruptions)

    result = evaluate_deterministic(decisions, p1_realized_disruptions)

    return result

def get_provided_solution(player, disruption_risks_info):
    """Get solution that is provided ex-ante to participants.

    Args:
        player (Player): Reference to experiment participant.
        disruption_risks_info (str): Flattened dictionary of nodes with disruption risk.

    Returns:
        result (dict): A dictionary containing
            - "decisions" (dict): decisions of the solution that will be shown to participants.
            - "provided_scenarios" (dict): profit scenarios and probabilities of this solution.
            - "profit" (str): Expected profit for this solution.
    """
    result = {}
    
    if C.FLAG_CALCULATE_PROVIDED_SOLUTION == True:
        stoch_prog_filename = f"coffee_stochastic_evaluation.py"

        try:
            code_path = Path(__file__).with_name(stoch_prog_filename)
        except:
            route_dir = Path.cwd()
            code_path = fr"{route_dir}\llms_decision_support\{stoch_prog_filename}"
        source_code = open(code_path, "r").read()
        locals_dict = {}
        locals_dict.update(globals())
        locals_dict.update(locals())

        old_code = "disruption_risks_info = {}"
        new_code = "disruption_risks_info = " + json.dumps(disruption_risks_info)
        updated_source_code = _replace(source_code, old_code, new_code)

        # Save the original stdout and stderr
        original_stdout = sys.stdout

        # Suppress output by redirecting stdout and stderr
        sys.stdout = StringIO()

        try:
            exec(updated_source_code, locals_dict, locals_dict)
        finally:
            # Restore original stdout and stderr
            sys.stdout = original_stdout
        
        p1_provided_decisions = dict.fromkeys(list(C.SUPPLIERS) + list(C.ROASTERIES))
        if True:
            model = locals_dict["model"]
            supplier_activation = locals_dict["supplier_activation"]
            roastery_activation = locals_dict["roastery_activation"]

            for s in C.SUPPLIERS:
                if supplier_activation[s].X:
                    p1_provided_decisions[s] = "activate"
                else:
                    p1_provided_decisions[s] = "do not activate"
            for r in C.ROASTERIES:
                if roastery_activation[(r, 'low')].X + roastery_activation[(r, 'high')].X == 0:
                    p1_provided_decisions[r] = "do not activate"
                elif roastery_activation[(r, 'low')].X == 1:
                    p1_provided_decisions[r] = 'activate (low)'
                elif roastery_activation[(r, 'high')].X == 1:
                    p1_provided_decisions[r] = 'activate (high)'
            result["decisions"] = p1_provided_decisions
            player.p1_provided_decisions = json.dumps(p1_provided_decisions)

            result["profit"] = "{:,}".format(int(np.round(model.objVal)))
    else:
        result["decisions"] = {
            'supplier1': "activate",
            'supplier2': "do not activate",
            'supplier3': "activate",
            'roastery1': "activate (high)",
            'roastery2': "do not activate",
        }
        sp_solution_id = 1
        sp_solution_info = next((item for item in C.CUSTOM_TEST_CHOICES if item['id'] == sp_solution_id), None)
        sp_solution_scenarios = sp_solution_info["scenarios"]
        result["provided_scenarios"] = {
            f"{(key):,.0f}": value for key, value in sp_solution_scenarios.items()
        }
        result["profit"] = sp_solution_info["ev"]
        player.p1_provided_scenarios = json.dumps(result["provided_scenarios"])
        player.p1_provided_decisions = json.dumps(result["decisions"])
    return result

def update_payoff_uq_bonus(player: Player, page_name_str: Page):
    """Update bonus for an understanding questions page.

    Args:
        player (Player): Reference to experiment participant.
        page_name_str (Page): Page that participant has just completed.
    """
    if C.DEACTIVATE_UQS == False:
        # Get the class by name
        page_class = getattr(C.MODULE, page_name_str)

        try:
            uq_tries_dict = [
                player.uq1_tries_left, player.uq2_tries_left,
                player.uq3_tries_left, player.uq4_tries_left,
                player.uq5_tries_left, player.uq6_tries_left,
            ]
            # Import only possible here due to oTree (otherwise: circular ImportError)
            from .. import B_UQ1_Non_performance_payoff, B_UQ2_Setting_and_task, B_UQ3_Decisions_profit_etc, B_UQ4_Decision_selection, B_UQ5_Disruptions, B_UQ6_Decision_support
            page_sequence_bonus = [
                B_UQ1_Non_performance_payoff,
                B_UQ2_Setting_and_task,
                B_UQ3_Decisions_profit_etc,
                B_UQ4_Decision_selection,
                B_UQ5_Disruptions,
                B_UQ6_Decision_support,
            ]
            index = page_sequence_bonus.index(page_class)
            # index = uq_pages.index(page_class)

            if uq_tries_dict[index] == C.MAX_UQ_TRIES - 1:     # -1 since the first (correct) try counts as well
                player.payoff_uq_bonus_currency += C.UQ_BONUS_PER_PAGE
                player.achieved_nr_of_uq_bonuses += 1
                #print(f"Bonus payoff for player {get_participant_id(player)} updated on page {page_name_str}: {player.payoff_uq_bonus_currency:.2f}")
        except:
            pass
            #print("Error in bonus updating. Payoff remains unchanged.")

def p2_select_random_profit(id):
    """Get random outcome for Part 2.

    Args:
        id (int): Reference to chosen payout scheme for Part 2.

    Returns:
        result (int): Randomly selected profit
    """
    # Find the dictionary with the given id
    choice = next((item for item in C.CUSTOM_TEST_CHOICES if item['id'] == id), None)
    
    if not choice:
        raise ValueError("Invalid id")
    
    scenarios = choice['scenarios']
    profits = list(scenarios.keys())
    probabilities = list(scenarios.values())

    # Create a Generator instance
    rng = np.random.default_rng()
    
    # Randomly select a profit based on the given probabilities
    result = int(rng.choice(a=profits, p=probabilities))
    
    return result

def set_page_start_time(player, page_name):
    """
    Records the start time of the page in a dynamically named field on the Player model.
    Should be called in the is_displayed method of each page.
    
    Args:
        player (Player): The Player instance (self in is_displayed or before_next_page).
        page_name (str): The name of the page.
    """
    try:
        field_name = f"{page_name}_start_time"
        if player.field_maybe_none(field_name) == None:
            setattr(player, field_name, datetime.now().isoformat())
    except:
        # Worst case, time is not recorded
        pass

def set_page_end_time(player, page_name):
    """
    Records the end time of the page in a dynamically named field on the Player model.
    Should be called in the before_next_page method of each page.
    
    Args:
        player (Player): The Player instance (self in is_displayed or before_next_page).
        page_name (str): The name of the page.
    """
    try:
        field_name = f"{page_name}_end_time"
        if player.field_maybe_none(field_name) == None:
            setattr(player, field_name, datetime.now().isoformat())
    except:
        # Worst case, time is not recorded
        pass

def get_p2_payoff_choices():
    """Get scenarios and probabilities for Part 2 decision-making.

    Returns:
        result (dict): Dictionary of profit scenarios and their probabilities.
        (min and max are not used/displayed in our implementation)
    """
    result = []
    counter = 0

    for subdict in C.CUSTOM_TEST_CHOICES:
        result.append(dict())
        
        for key, value in subdict.items():
            result[counter][key] = value

        formatted_scenarios = {}
        for profit, prob in subdict["scenarios"].items():
            formatted_scenarios[f"${profit:,.0f}"] = f"{int(np.round(100*prob,0))}%"
        #result[counter]["scenarios"] = ", ".join(f"{key}: <i>{value}%</i>" for key, value in formatted_scenarios.items())
        result[counter]["scenarios"] = formatted_scenarios

        result[counter]["min"] = f"${(min(subdict['scenarios'].keys())):,.0f}"
        result[counter]["max"] = f"${(max(subdict['scenarios'].keys())):,.0f}"

        counter += 1
    
    return result

def get_p1_decisions_str(decisions_dict):
    """Get standardized string representation for Part 1 decision.

    Args:
        decisions_dict (dict): Dictionary of chosen decisions (which nodes to activate).

    Returns:
        result (str): standardized string of Part 1 decision.
    """
    result = '______________'
    result = 'S1_S2_S3___R1-x_R2-x'

    mapping_to_str_index = {
        'supplier1': (0,1),
        'supplier2': (3,4),
        'supplier3': (6,7),
        'roastery1': (11,14),
        'roastery2': (16,19),
    }
    for node, activation in decisions_dict.items():
        if activation == 'do not activate':
            start, end = mapping_to_str_index[node]
            replacement = "_" + (end-start) * "_"
            result = result[:start] + replacement + result[(end+1):]
        else:
            if 'roastery' in node:
                _, end = mapping_to_str_index[node]
                if 'low' in activation:
                    l_or_h = 'l'
                else:
                    l_or_h = 'h'
                result = result[:end] + l_or_h + result[(end+1):]

    return result

def get_p2_decisions_str(decisions_id:int):
    """Get standardized string representation for Part 2 decision.

    Args:
        decisions_dict (dict): Dictionary of chosen decisions (which nodes to activate;
        based on the chosen corresponding payout scheme).

    Returns:
        result (str): standardized string of Part 2 decision.
    """
    result = None

    ROUND = 0.000000001
    CUSTOM_TEST_CHOICES = [
        {'id': 1, 'ev': '$4,253', "cv": "29%", "sd": "$1,242", "scenarios": {4800: 0.613-ROUND, 4380: 0.285+ROUND, 610: 0.102}, 'decisions': "S1    S3   R1-h     "},
        {'id': 2, 'ev': "$4,250", "cv": "16%", "sd": "$678", "scenarios": {4690: 0.613-ROUND, 3925: 0.285+ROUND, 2600: 0.078, 2225: 0.024}, 'decisions': "S1    S3   R1-l R2-l"},
        {'id': 3, 'ev': "$4,208", "cv": "9%", "sd": "$385", "scenarios": {4490: 0.613-ROUND, 4110: 0.078, 3725: 0.285+ROUND, 3050: 0.024}, 'decisions': "   S2 S3   R1-l R2-h"},
        {'id': 4, 'ev': "$4,148", "cv": "6%", "sd": "$228", "scenarios": {4225: 0.898, 3470: 0.102}, 'decisions': "   S2 S3   R1-l R2-h"},
        {'id': 5, 'ev': "$3,938", "cv": "4%", "sd": "$151", "scenarios": {3990: 0.613-ROUND, 3975: 0.285+ROUND, 3610: 0.078, 3220: 0.024}, 'decisions': "S1 S2 S3   R1-l R2-h"},
        {'id': 6, 'ev': "$3,870", "cv": "0%", "sd": "$0", "scenarios": {3870: 1.0}, 'decisions': "   S2 S3        R2-h"},
    ]
    for i in range(len(CUSTOM_TEST_CHOICES)):
        if CUSTOM_TEST_CHOICES[i]['id'] == decisions_id:
            result = CUSTOM_TEST_CHOICES[i]['decisions'].replace(" ", "_")
    return result