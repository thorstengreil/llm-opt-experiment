"""For the sake of readability, we do not document all page classes or their standard oTree 
function implementations here.
For details, please refer to the official oTree documentation: https://otree.readthedocs.io/
"""
from otree.api import *
import json
import numpy as np
from datetime import datetime

from llms_decision_support.python_files.constants import C
from llms_decision_support.python_files.utils import (set_page_start_time, set_page_end_time, get_participant_id,
                                          update_round_counter_in_agent, create_disruption_risks_info,
                                          get_provided_solution, get_p2_payoff_choices,
                                          p2_select_random_profit, update_payoff_uq_bonus,
                                          setup_llm_framework, get_llm_answer,
                                          sort_coffee_node_dict, calculate_realized_profit,
                                          get_p1_decisions_str, get_p2_decisions_str)
from llms_decision_support.python_files.utils import DummyAgent
from .. import Player
from .. import players_agent_dict

class A0_Idle_before_start(Page):  
    @staticmethod
    def is_displayed(player: Player):        
        set_page_start_time(player, player.participant._current_page_name)

        return player.round_number == 1
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class A1_Introduction(Page):
    form_model = "player"
    
    if C.REQUIRE_SUBJECT_ID:
        form_fields = ["informed_consent", "subject_id"]
        if C.CURRENCY == "EUR":
            form_fields += ["degree_program"]
    else:
        form_fields = ["informed_consent"]
        if C.CURRENCY == "EUR":
            form_fields += ["degree_program"]
    
    @staticmethod
    def is_displayed(player: Player):
        # group assignment
        if C.ALTERNATING_GROUP_ASSIGNMENT:
            if C.START_WITH_IN_TREATMENT_GROUP:
                player.in_treatment_group_toggle = get_participant_id(player) % 2 == 1
            else:
                player.in_treatment_group_toggle = get_participant_id(player) % 2 == 0
        else:
            # All players in one group
            player.in_treatment_group_toggle = C.START_WITH_IN_TREATMENT_GROUP
        
        set_page_start_time(player, player.participant._current_page_name)

        return player.round_number == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            REQUIRE_SUBJECT_ID=C.REQUIRE_SUBJECT_ID,
            BASE_PAYOFF=f"{C.BASE_PAYOFF:.2f}",
            TOTAL_MAX_PAYOFF=f"{C.TOTAL_MAX_PAYOFF:.2f}",
            MAX_UQ_BONUS=f"{C.UQ_BONUS_PER_PAGE*C.NR_OF_UQ_PAGES:.2f}",
            UQ_BONUS_PER_PAGE=f"{C.UQ_BONUS_PER_PAGE:.2f}",
            NR_OF_UQ_PAGES=C.NR_OF_UQ_PAGES,
            CURRENCY=C.CURRENCY,
        )  
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)
        
        if player.informed_consent == 2:
            player.termination_flag == True

class A2_Experiment_overview(Page):
    form_model = "player"
    
    @staticmethod
    def is_displayed(player: Player):              
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.round_number == 1 and player.informed_consent == 1
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class B_UQ1_Non_performance_payoff(Page):
    form_model = "player"

    if C.DEACTIVATE_UQS == False:
        form_fields = [
            "rules_bonus_for_understanding",
            "consequences_maximum_failures",
            "decisions_influence_on_payoff",
        ]
    else:
        form_fields = []

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.termination_flag == False and player.round_number == 1 and player.informed_consent == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        result = dict(
            MAX_UQ_TRIES=C.MAX_UQ_TRIES,
            NR_OF_UQ_PAGES=C.NR_OF_UQ_PAGES,
            BASE_PAYOFF=f"{C.BASE_PAYOFF:.2f}",
            UQ_BONUS_PER_PAGE=f"{C.UQ_BONUS_PER_PAGE:.2f}",
            MAX_UQ_BONUS=f"{C.UQ_BONUS_PER_PAGE*C.NR_OF_UQ_PAGES:.2f}",
            MAX_DECISIONS_PAYOFF=f"{C.MAX_DECISIONS_PAYOFF:.2f}",
            TOTAL_MAX_PAYOFF=f"{C.TOTAL_MAX_PAYOFF:.2f}",
            CURRENCY=C.CURRENCY,
        )

        return result

    @staticmethod
    def error_message(player, values):
        result = None
        
        if C.DEACTIVATE_UQS == False:
            player.uq1_tries_left -= 1
            result = dict()
            
            solutions = dict(
                rules_bonus_for_understanding=2,
                consequences_maximum_failures=1,
                decisions_influence_on_payoff=4,
            )

            for field_name in solutions:
                if values[field_name] != solutions[field_name]:
                    result[field_name] = 'Wrong answer'

            if result and player.uq1_tries_left == 0:
                player.termination_flag = True
                result = dict()

        return result

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)
        update_payoff_uq_bonus(player, player.participant._current_page_name)

class B_UQ2_Setting_and_task(Page):  
    form_model = "player"

    if C.DEACTIVATE_UQS == False:
        form_fields = [
            "parts_experiment",
            "network_structure",
            "task",
            "compensation_influence",
            "both_parts_payoff",
            "fictional_currency",
        ]
    else:
        form_fields = []

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.termination_flag == False and player.round_number == 1 and player.informed_consent == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            NR_OF_UQ_PAGES=C.NR_OF_UQ_PAGES,
            MAX_UQ_TRIES=C.MAX_UQ_TRIES,
            MAX_UQ_TRIES_EX_POST=C.MAX_UQ_TRIES-1,
            UQ_BONUS_PER_PAGE=f"{C.UQ_BONUS_PER_PAGE:.2f}",
            COFD_TO_CURRENCY=f"{C.COFD_TO_CURRENCY:.5f}",
            COFD_1000_TO_CURRENCY=f"{1000*C.COFD_TO_CURRENCY:,.2f}",
            CURRENCY=C.CURRENCY,
        )

    @staticmethod
    def error_message(player, values):
        result = None
        
        if C.DEACTIVATE_UQS == False:
            player.uq2_tries_left -= 1
            result = dict()
            
            solutions = dict(
                parts_experiment=2,
                network_structure=2,
                task=4,
                compensation_influence=2,
                both_parts_payoff=4,
                fictional_currency=3,
            )

            for field_name in solutions:
                if values[field_name] != solutions[field_name]:
                    result[field_name] = 'Wrong answer'

            if result and player.uq2_tries_left == 0:
                player.termination_flag = True
                result = dict()

        return result

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)
        update_payoff_uq_bonus(player, player.participant._current_page_name)

class B_UQ3_Decisions_profit_etc(Page):
    form_model = "player"

    if C.DEACTIVATE_UQS == False:
        form_fields = [
            "activation_requirement",
            "profit_definition",
            "supplier_fixed_cost",
            "roastery_fixed_cost",
            "suppliers_total_capacity",
            "roasteries_total_capacity",
            "bonus_pool",
        ]
    else:
        form_fields = []
    
    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.termination_flag == False and player.round_number == 1 and player.informed_consent == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            NR_OF_UQ_PAGES=C.NR_OF_UQ_PAGES,
            MAX_UQ_TRIES=C.MAX_UQ_TRIES,
            MAX_UQ_TRIES_EX_POST=C.MAX_UQ_TRIES-1,
            UQ_BONUS_PER_PAGE=f"{C.UQ_BONUS_PER_PAGE:.2f}",
            ENDOWMENT=f"{C.ENDOWMENT:,.0f}",
            CURRENCY=C.CURRENCY,
        )

    @staticmethod
    def error_message(player, values):
        result = None
        
        if C.DEACTIVATE_UQS == False:
            player.uq3_tries_left -= 1
            result = dict()
        
            solutions = dict(
                activation_requirement=2,
                profit_definition=1,
                supplier_fixed_cost=2,
                roastery_fixed_cost=5,
                suppliers_total_capacity=4,
                roasteries_total_capacity=4,
                # fulfill_demand=4,
                bonus_pool=1,
            )

            for field_name in solutions:
                if values[field_name] != solutions[field_name]:
                    result[field_name] = 'Wrong answer'

            if result and player.uq3_tries_left == 0:
                player.termination_flag = True
                result = dict()

        return result

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)
        update_payoff_uq_bonus(player, player.participant._current_page_name)

class B_UQ4_Decision_selection(Page):
    form_model = "player"

    if C.DEACTIVATE_UQS == False:
        form_fields = [
            "fixed_cost_impact",
            "shipping_influence",
            "decisions_selection_test",
        ]
    else:
        form_fields = []

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)

        return player.termination_flag == False and player.round_number == 1 and player.informed_consent == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            NR_OF_UQ_PAGES=C.NR_OF_UQ_PAGES,
            MAX_UQ_TRIES=C.MAX_UQ_TRIES,
            MAX_UQ_TRIES_EX_POST=C.MAX_UQ_TRIES-1,
            UQ_BONUS_PER_PAGE=f"{C.UQ_BONUS_PER_PAGE:.2f}",
            DEACTIVATE_UQS=C.DEACTIVATE_UQS,
            CURRENCY=C.CURRENCY,
        )

    @staticmethod
    def error_message(player, values):
        result = None
        
        if C.DEACTIVATE_UQS == False:
            player.uq4_tries_left -= 1
            result = dict()
            
            solutions = dict(
                fixed_cost_impact=1,
                shipping_influence=4,
                decisions_selection_test="1100H"
            )

            for field_name in solutions:
                if values[field_name] != solutions[field_name]:
                    result[field_name] = 'Wrong answer'

            if result and player.uq4_tries_left == 0:
                player.termination_flag = True
                result = dict()

        return result
    
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)
        update_payoff_uq_bonus(player, player.participant._current_page_name)

class B_UQ5_Disruptions(Page):
    form_model = "player"

    if C.DEACTIVATE_UQS == False:
        form_fields = [
            "disruption_timing",
            "disruption_impact",
            "disruption_definition",
            "disruption_examples_1",
            "disruption_examples_2",
            "performance_evaluation",
        ]
    else:
        form_fields = []

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)

        return player.termination_flag == False and player.round_number == 1 and player.informed_consent == 1

    @staticmethod
    def vars_for_template(player: Player):
        disruption_risks_info_UQ_1 = {
            "supplier2": 0.2,
            "supplier3": 0.3,
            "roastery2": 0.4,
        }
        disruption_risks_info_UQ_2 = {
            "supplier3": 0.2,
            "roastery1": 0.1,
        }
        disruption_risks_info_UQ_1 = {key: int(value*100) for key, value in disruption_risks_info_UQ_1.items()}
        disruption_risks_info_UQ_2 = {key: int(value*100) for key, value in disruption_risks_info_UQ_2.items()}
        return dict(
            NR_OF_UQ_PAGES=C.NR_OF_UQ_PAGES,
            MAX_UQ_TRIES=C.MAX_UQ_TRIES,
            MAX_UQ_TRIES_EX_POST=C.MAX_UQ_TRIES-1,
            UQ_BONUS_PER_PAGE=f"{C.UQ_BONUS_PER_PAGE:.2f}",
            disruption_risks_info_UQ_1=disruption_risks_info_UQ_1,
            disruption_risks_info_UQ_2=disruption_risks_info_UQ_2,
            DEACTIVATE_UQS=C.DEACTIVATE_UQS,
            CURRENCY=C.CURRENCY,
        )

    @staticmethod
    def error_message(player, values):
        result = None
        
        if C.DEACTIVATE_UQS == False:
            player.uq5_tries_left -= 1
            result = dict()
        
            solutions = dict(
                disruption_timing=2,
                disruption_impact=4,
                disruption_definition=4,
                disruption_examples_1=1,
                disruption_examples_2=4,
                performance_evaluation=4,
            )           

            for field_name in solutions:
                if values[field_name] != solutions[field_name]:
                    result[field_name] = "Wrong answer"
            
            if result and player.uq5_tries_left == 0:
                player.termination_flag = True
                result = dict()

        return result

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)
        update_payoff_uq_bonus(player, player.participant._current_page_name)

class B_UQ6_Decision_support(Page):
    form_model = "player"

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.termination_flag == False and player.round_number == 1 and player.informed_consent == 1

    @staticmethod
    def get_form_fields(player: Player):
        result = []

        if C.DEACTIVATE_UQS == False:
            result += [
                    "provided_setting_basis",
                    "provided_setting_risk",
                    "risk_judgement",
                ]
            if player.in_treatment_group_toggle:
                result += [
                    "decision_support_system_role",
                    "test_question",
                ]

        return result

    @staticmethod
    def vars_for_template(player: Player):
        disruption_risks_info_UQ_2 = {
            "supplier3": 0.2,
            "roastery1": 0.1,
        }
        disruption_risks_info_UQ_2 = {key: int(value*100) for key, value in disruption_risks_info_UQ_2.items()}
        return dict(
            NR_OF_UQ_PAGES=C.NR_OF_UQ_PAGES,
            MAX_UQ_TRIES=C.MAX_UQ_TRIES,
            MAX_UQ_TRIES_EX_POST=C.MAX_UQ_TRIES-1,
            UQ_BONUS_PER_PAGE=f"{C.UQ_BONUS_PER_PAGE:.2f}",
            disruption_risks_info_UQ_2=disruption_risks_info_UQ_2,
            DEACTIVATE_UQS=C.DEACTIVATE_UQS,
            CURRENCY=C.CURRENCY,
        )

    @staticmethod
    def error_message(player, values):
        result = None
        
        if C.DEACTIVATE_UQS == False:
            player.uq6_tries_left -= 1
            result = dict()
        
            solutions = dict(
                provided_setting_basis=2,
                provided_setting_risk=1,
                risk_judgement=3,
            )
            if player.in_treatment_group_toggle:
                # Add form field if player in treatment group
                solutions["decision_support_system_role"]=3

            result = dict()

            for field_name in solutions:
                if values[field_name] != solutions[field_name]:
                    result[field_name] = "Wrong answer"

            if result and player.uq6_tries_left == 0:
                player.termination_flag = True
                result = dict()

        return result

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)
        update_payoff_uq_bonus(player, player.participant._current_page_name)

class B_UQX_Summary(Page):
    form_model = "player"

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.termination_flag == False and player.round_number == 1 and player.informed_consent == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            MAX_UQ_TRIES_EX_POST=C.MAX_UQ_TRIES-1,
            UQ_BONUS_PER_PAGE=f"{C.UQ_BONUS_PER_PAGE:.2f}",
            payoff_uq_bonus_currency=f"{player.payoff_uq_bonus_currency:.2f}",
            DEACTIVATE_UQS=C.DEACTIVATE_UQS,
            CURRENCY=C.CURRENCY,
        )
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class C_P1_Decision_making(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player: Player):
        global players_agent_dict

        participant_id = get_participant_id(player)
        if not participant_id in players_agent_dict.keys():
            if C.FLAG_LLM_ACTIVE and player.in_treatment_group_toggle:
                setup_llm_framework(player)
            else:
                # Create agent setting
                players_agent_dict[participant_id] = {}

                players_agent_dict[participant_id]["agent"] = DummyAgent(
                    source_code_stoch = C.SRC_CODE_STOCH,
                    participant_id=participant_id,
                )
                players_agent_dict[participant_id]["user"] = {}

        page_name = player.participant._current_page_name
        field_name = f"{page_name}_start_time"
        if player.field_maybe_none(field_name) == None:
            update_round_counter_in_agent(player)

        set_page_start_time(player, page_name)

        return player.termination_flag == False and player.informed_consent == 1
    
    @staticmethod
    def vars_for_template(player: Player):       
        disruption_risks_info = create_disruption_risks_info(player)
        p1_provided_solution = get_provided_solution(player, disruption_risks_info)
        disruption_risks_info = {key: int(value*100) for key, value in disruption_risks_info.items()}
        p1_provided_decisions = p1_provided_solution["decisions"]
        provided_profit = p1_provided_solution["profit"]
        p1_provided_scenarios_raw = p1_provided_solution["provided_scenarios"]
        p1_provided_scenarios = {key: int(np.round(100*value)) for key, value in p1_provided_scenarios_raw.items()}
        
        # Variables for instructions (from _UQ{x}_instructions.html files)
        uq1_vars = B_UQ1_Non_performance_payoff.vars_for_template(player)
        uq2_vars = B_UQ2_Setting_and_task.vars_for_template(player)
        uq3_vars = B_UQ3_Decisions_profit_etc.vars_for_template(player)
        uq5_vars = B_UQ5_Disruptions.vars_for_template(player)
        uq6_vars = B_UQ6_Decision_support.vars_for_template(player)
        
        vars = dict(
            disruption_risks_info=disruption_risks_info, p1_provided_decisions=p1_provided_decisions,
            provided_profit=provided_profit,
            p1_provided_scenarios=p1_provided_scenarios,
            in_treatment_group_toggle=player.in_treatment_group_toggle,
            ENABLE_REMINDER_POPUP=C.ENABLE_REMINDER_POPUP,
            CURRENCY=C.CURRENCY,
        )
        
        return vars | uq1_vars | uq2_vars | uq3_vars | uq5_vars | uq6_vars
    
    @staticmethod
    def live_method(player, data):
        info_type = data["information_type"]
        if info_type == "question":
            player.questions_counter += 1
            questions_id = player.questions_counter
            question = data["message"]
            participant_id = get_participant_id(player)
            player.current_question_to_llm = question
            if questions_id > 1:
                all_questions = json.loads(player.all_questions_to_llm)
                all_questions[questions_id] = question

                all_answers = json.loads(player.all_answers_from_llm)
                all_answers[questions_id] = {}
                start_time = datetime.now().isoformat()
                all_answers[questions_id] = {"latency_in_s": start_time}
            else:
                # first question
                all_questions = {
                    questions_id: question
                }
                # store start of request for answer
                all_answers = {
                    questions_id: {
                        "latency_in_s": datetime.now().isoformat(),
                    }
                }
            player.all_questions_to_llm = json.dumps(all_questions)
            player.all_answers_from_llm = json.dumps(all_answers)

            try:
                answer = get_llm_answer(player)
            except:
                answer = C.FAILED_ANSWER
                # Reset LLM (if necessary)
                if C.FLAG_LLM_ACTIVE and player.in_treatment_group_toggle:
                    setup_llm_framework(player)
                else:
                    players_agent_dict[participant_id]["agent"] = DummyAgent(
                        source_code_stoch = C.SRC_CODE_STOCH,
                        participant_id=participant_id,
                    )
                    players_agent_dict[participant_id]["user"] = {}

            all_answers = json.loads(player.all_answers_from_llm)
            
            start_time_str = all_answers[str(questions_id)]["latency_in_s"]
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.now()
            latency = abs((end_time - start_time).total_seconds())
            all_answers[str(questions_id)]["latency_in_s"] = latency
            all_answers[str(questions_id)]["answer"] = answer
            player.all_answers_from_llm = json.dumps(all_answers)

            try:
                return {participant_id: answer}
            finally:
                # first: display answer, then: save logs and codes
                players_agent_dict[participant_id]["agent"].perform_upload_to_dropbox()

        elif info_type == "decisions":
            decisions = data["supplierStates"] | data["roasteryStates"]
            player.p1_decisions = json.dumps(sort_coffee_node_dict(decisions))
            player.p1_outcome = calculate_realized_profit(player)
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class D_P2_Decision_making(Page):
    form_model = 'player'

    form_fields = ["p2_decisions"]

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)

        return player.termination_flag == False and player.informed_consent == 1

    @staticmethod
    def vars_for_template(player: Player):
        p2_payoff_choices = get_p2_payoff_choices()

        return dict(
            p2_payoff_choices=p2_payoff_choices,
            ENABLE_REMINDER_POPUP=C.ENABLE_REMINDER_POPUP,
        )
    
    @staticmethod
    def error_message(player, values):
        result = {}

        if not values.get("p2_decisions"):
            result["p2_decisions"] = "You must select one option."

        return result

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)
        
        id = int(player.p2_decisions)
        player.p2_outcome = int(p2_select_random_profit(id))

        # Randomly determine realized profit to use for final payoff
        rng = np.random.default_rng()

        player.payoff_experiment_currency = int(rng.choice([player.p1_outcome, player.p2_outcome]))

class E_Post_decision_questions(Page):
    form_model = 'player'

    form_fields = [
        "change_p1_decision",
    ]

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)

        try:
            p1_decisions_str = get_p1_decisions_str(json.loads(player.p1_decisions))
            p2_decisions_str = get_p2_decisions_str(player.p2_decisions)
        except:
            p1_decisions_str = "NONE_P1"
            p2_decisions_str = "NONE_P2"
            # If participant failed the understanding questions, p1_decisions and p2_decisions are None
            pass

        return player.termination_flag == False and player.informed_consent == 1 and not p1_decisions_str == p2_decisions_str
    
    @staticmethod
    def vars_for_template(player: Player):
        p1_decisions_str = get_p1_decisions_str(json.loads(player.p1_decisions))
        p1_scenarios_and_probs_unformatted = C.SCENARIOS_PROBS_DICT[p1_decisions_str]
        p1_image_path = f'llms_decision_support/{p1_decisions_str}.svg'
        player.p1_scenarios = json.dumps(p1_scenarios_and_probs_unformatted)
        p1_scenarios_and_probs = {}
        for profit, prob in p1_scenarios_and_probs_unformatted.items():
            p1_scenarios_and_probs[f"${float(profit):,.0f}"] = f"{int(np.round(100*float(prob),0))}%"
        
        p2_decisions_integer_val = int(player.p2_decisions)
        p2_decisions_str = get_p2_decisions_str(int(player.p2_decisions))
        p2_payoff_choices = get_p2_payoff_choices()
        for option in p2_payoff_choices:
            if option['id'] == p2_decisions_integer_val:
                p2_scenarios_and_probs = option['scenarios']

        p2_image_path = f'llms_decision_support/{p2_decisions_str}.svg'
    
        return dict(
            p1_scenarios_and_probs=p1_scenarios_and_probs,
            p1_image_path=p1_image_path,
            p2_scenarios_and_probs=p2_scenarios_and_probs,
            p2_image_path=p2_image_path,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class F_P1_Outcome(Page):
    form_model = 'player'
    
    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.termination_flag == False and player.informed_consent == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        decisions = json.loads(player.p1_decisions)
        p1_realized_disruptions = json.loads(player.p1_realized_disruptions)
        disruption_risks_info = json.loads(player.disruption_risks_info)
        disruption_risks_info = {key: int(value*100) for key, value in disruption_risks_info.items()}
        p1_provided_decisions = json.loads(player.p1_provided_decisions)
        p1_provided_scenarios_raw = json.loads(player.p1_provided_scenarios)
        p1_provided_scenarios = {key: int(np.round(100*value)) for key, value in p1_provided_scenarios_raw.items()}
        return dict(
            decisions=decisions, p1_realized_disruptions=p1_realized_disruptions,
            disruption_risks_info=disruption_risks_info,
            p1_provided_decisions=p1_provided_decisions,
            p1_provided_scenarios=p1_provided_scenarios,
            p1_outcome=f"{player.p1_outcome:,.0f}",
        )
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class G_P2_Outcome(Page):
    form_model = 'player'
    
    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.termination_flag == False and player.informed_consent == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        decisions = json.loads(player.p1_decisions)
        p1_realized_disruptions = json.loads(player.p1_realized_disruptions)
        disruption_risks_info = json.loads(player.disruption_risks_info)
        disruption_risks_info = {key: int(value*100) for key, value in disruption_risks_info.items()}
        p1_provided_decisions = json.loads(player.p1_provided_decisions)
        p1_provided_scenarios = json.loads(player.p1_provided_scenarios)
        p1_provided_scenarios = {key: int(np.round(100*value)) for key, value in p1_provided_scenarios.items()}
        
        r2_choice_id = player.p2_decisions
        r2_choice_info = next((item for item in C.CUSTOM_TEST_CHOICES if item['id'] == r2_choice_id), None)
        r2_possible_scenarios = r2_choice_info["scenarios"]
        r2_possible_scenarios = {f"{key:,.0f}": int(np.round(100*value)) for key, value in r2_possible_scenarios.items()}

        return dict(
            decisions=decisions, p1_realized_disruptions=p1_realized_disruptions,
            disruption_risks_info=disruption_risks_info, p1_provided_decisions=p1_provided_decisions,
            p1_provided_scenarios=p1_provided_scenarios,
            p2_outcome=f"{player.p2_outcome:,.0f}",
            r2_possible_scenarios=r2_possible_scenarios,
            p1_outcome=f"{player.p1_outcome:,.0f}",
            CURRENCY=C.CURRENCY,
        )
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class H_Add_experiment_questions(Page):
    form_model = 'player'

    form_fields_start = [
        "ev_knowledge",
        "variability_knowledge",
        "general_risk_question",
        "chatgpt_experience",
        "optimization_experience",
    ]
    
    form_fields_mid_1 = []

    form_fields_mid_2 = []
    
    form_fields = form_fields_start + form_fields_mid_1 + form_fields_mid_2

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.round_number == C.NUM_ROUNDS and player.termination_flag == False and player.informed_consent == 1
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class I_Demographics(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.round_number == C.NUM_ROUNDS and player.informed_consent == 1
    
    @staticmethod
    def get_form_fields(player: Player):
        result = []

        form_fields_start = [
            "age",
            "sex",
            "nationality",
            "education",
            "position",
        ]
        if C.CURRENCY == "USD":
            form_fields_start += ["degree_program"]
        form_fields_mid = []
        if C.CURRENCY == "EUR":
            if player.degree_program == "Management & Technology (B.Sc.)":
                form_fields_mid = [
                    "degree_specialization_tech_bsc",
                ]
            elif player.degree_program == "Management & Technology (M.Sc.)":
                form_fields_mid = [
                    "degree_specialization_tech_msc",
                    "degree_specialization_mgmt_msc",
                ]
        form_fields_end = [
            "english_native_speaker",
            "english_proficiency",
            "open_feedback",
        ]
        result = form_fields_start + form_fields_mid + form_fields_end

        return result

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            CURRENCY=C.CURRENCY,
        )
        
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class J_Final_page(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.round_number == C.NUM_ROUNDS and player.informed_consent == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        if not player.termination_flag:
            decisions_payoff_currency_rounded = np.round((player.payoff_experiment_currency / C.CURRENCY_TO_COFD), 2)
            player.payoff_decisions_currency = decisions_payoff_currency_rounded
        else:
            player.payoff_experiment_currency = 0
            player.payoff_decisions_currency = 0.0
        player.payoff_currency = np.round(max(0, C.BASE_PAYOFF + player.payoff_uq_bonus_currency + player.payoff_decisions_currency),2)
        player.payoff_currency_unrounded = player.payoff_currency 
        player.payoff_currency = np.ceil(10*player.payoff_currency)/10

        # Return this data to the template
        result = dict(
            BASE_PAYOFF=f"{C.BASE_PAYOFF:.2f}",
            COFD_TO_CURRENCY=f"{np.round(C.COFD_TO_CURRENCY,5):.5f}",
            CURRENCY_TO_COFD=f"{C.CURRENCY_TO_COFD:.0f}",
            payoff_decisions_currency=f"{player.payoff_decisions_currency:.2f}",
            payoff_uq_bonus_currency=f"{player.payoff_uq_bonus_currency:.2f}",
            payoff_currency=f"{player.payoff_currency:.2f}",
            payoff_currency_unrounded=f"{player.payoff_currency_unrounded:.2f}",
            NUM_ROUNDS_GREATER_ONE=C.NUM_ROUNDS>1,
            CURRENCY=C.CURRENCY,
        )
        if not player.termination_flag:
            result = result | dict(
                p1_outcome=f"{player.p1_outcome:,.0f}",
                p2_outcome=f"{player.p2_outcome:,.0f}",
                payoff_experiment_currency=f"{player.payoff_experiment_currency:,.0f}",
            )

        return result
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)

class K_No_consent(Page):
    @staticmethod
    def is_displayed(player: Player):
        set_page_start_time(player, player.participant._current_page_name)
        
        return player.informed_consent == 2
    
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            SHOW_UP_FEE=f"{C.SHOW_UP_FEE:,.2f}",
            CURRENCY=C.CURRENCY,
        )
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        set_page_end_time(player, player.participant._current_page_name)