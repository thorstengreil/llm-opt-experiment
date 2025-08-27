from otree.api import *
from otree.api import BaseConstants
from autogen import config_list_from_json 
import os
import json
from pathlib import Path
import importlib
import numpy as np

class C(BaseConstants):
    NAME_IN_URL = 'llms_decision_support'
    PLAYERS_PER_GROUP = None
    CURRENCY = "EUR"
    NUM_ROUNDS = 1

    REQUIRE_SUBJECT_ID = True

    # If True, alternatingly put players in treatment group or control group 
    # If False, all players are in one group, dependent on START_WITH_IN_TREATMENT_GROUP
    ALTERNATING_GROUP_ASSIGNMENT = False
    START_WITH_IN_TREATMENT_GROUP = True

    # Problem data (entity names)
    SUPPLIERS = ["supplier1", "supplier2", "supplier3"]
    ROASTERIES = ["roastery1", "roastery2"]
    CUSTOMERS = ["customer1", "customer2", "customer3"]

    FLAG_RANDOM_DISRUPTIONS = False
    FLAG_CALCULATE_PROVIDED_SOLUTION = False
    ENABLE_REMINDER_POPUP = False
    
    # LLM settings and relevant data
    FLAG_LLM_ACTIVE = True
    FAILED_ANSWER = "A technical error occurred. Please try again."

    # Load (private) OpenAI API key (needs to be put in a separate file named OAI_CONFIG_LIST in this json format: [{"api_key": "sk-xxxx..."}])
    openai_api_key = config_list_from_json(
        env_or_file="llms_decision_support/api_keys/OAI_CONFIG_LIST",
    )
    os.environ["OPENAI_API_KEY"] = openai_api_key[0]["api_key"]

    # Get the source code from a local file in the same directory
    code_path_stoch = Path(__file__).with_name("coffee_stochastic.py")
    SRC_CODE_STOCH = open(code_path_stoch, "r").read()

    # Get example questions for in-context learning (i.e. add to prompt)
    try:
        with open("llms_decision_support/data_files/icl_questions_llms_decision_support.json", 'r') as f:
            icl_qs = json.load(f)
            EXAMPLE_QA = json.dumps(icl_qs)
    except:
        EXAMPLE_QA = ""

    # Get helper documentation
    try:
        with open("llms_decision_support/data_files/helper_doc.txt", 'r') as f:
            HELPER_DOC = f.read()
    except:
        HELPER_DOC = ""

    MODULE = importlib.import_module(NAME_IN_URL)

    # PAYOFF DATA
    if CURRENCY == "EUR":
        SHOW_UP_FEE = 5.00                  # For non-consenting participants
        BASE_PAYOFF = 5.00                  # For all consenting participants
    else:
        SHOW_UP_FEE = 0.0                  # Adapt as needed
        BASE_PAYOFF = 0.0                  # Adapt as needed
    
    # Settings for bonus regarding understanding questions
    DEACTIVATE_UQS = False   # Answering understanding questions not required if True
    NR_OF_UQ_PAGES = 6
    MAX_UQ_TRIES = 2
    if CURRENCY == "EUR":
        UQ_BONUS_PER_PAGE = 0.20
    else:
        UQ_BONUS_PER_PAGE = 0.0            # Adapt as needed
    
    # For provided Stochastic Programming Solution (max EV) excl. endowment
    if CURRENCY == "EUR":
        DESIRED_AVG_MAX_PAYOFF = 16.25
    else:
        DESIRED_AVG_MAX_PAYOFF = 10.0       # Adapt as needed
    
    # Problem-specific; adapt if different setting is used
    EXP_VALUE_OF_SP_SOLUTION = 2043     # [COF$]
    MAX_POSSIBLE_PROFIT = 3050          # [COF$]
    MIN_PROFIT = -2200                  # [COF$]

    # Adjust endowment to get strightly positive payoffs (i.e. not == 0)
    ENDOWMENT_ADJUSTMENT = 10           # [COF$]
    
    # Calculate share of endowment
    AVAILABLE_FOR_DECISIONS_PAYOFF = DESIRED_AVG_MAX_PAYOFF - BASE_PAYOFF - UQ_BONUS_PER_PAGE * NR_OF_UQ_PAGES
    DISTANCE_MIN_TO_SP_MAX_EV_PROFIT = abs(MIN_PROFIT) + EXP_VALUE_OF_SP_SOLUTION
    MIN_PROFIT_SHARE_OF_DISTANCE = abs(MIN_PROFIT / DISTANCE_MIN_TO_SP_MAX_EV_PROFIT)

    ENDOWMENT_CURRENCY = AVAILABLE_FOR_DECISIONS_PAYOFF * MIN_PROFIT_SHARE_OF_DISTANCE
    EV_DECISIONS_ADD_ON_PAYOFF_CURRENCY = AVAILABLE_FOR_DECISIONS_PAYOFF - ENDOWMENT_CURRENCY

    # Calculate conversion rates
    CURRENCY_TO_COFD = EXP_VALUE_OF_SP_SOLUTION / EV_DECISIONS_ADD_ON_PAYOFF_CURRENCY
    COFD_TO_CURRENCY = 1 / CURRENCY_TO_COFD

    ENDOWMENT = ENDOWMENT_CURRENCY * CURRENCY_TO_COFD + ENDOWMENT_ADJUSTMENT

    # Calculate max payoffs
    MAX_DECISIONS_PAYOFF = (ENDOWMENT + MAX_POSSIBLE_PROFIT) * COFD_TO_CURRENCY
    TOTAL_MAX_PAYOFF = np.ceil((BASE_PAYOFF + UQ_BONUS_PER_PAGE * NR_OF_UQ_PAGES + MAX_DECISIONS_PAYOFF) * 10) / 10

    # Self-defined risk-aversion test (=Part 2)
    # 000001 added/subtracted to force rounding up (otherwise, sum is not 100% for this example when rounding to percentages with 0 decimal digits)
    # (numpy uses "banker's rounding", i.e. .5 figures are rounded up (down) if they are odd (even))
    # => we only have one .5 case (i.e. 0.285 or 28.5%) so it does not cancel out...
    ROUND = 0.000000001
    CUSTOM_TEST_CHOICES = [
        {'id': 1, 'ev': '$4,253', "cv": "29%", "sd": "$1,242", "scenarios": {4800: 0.613-ROUND, 4380: 0.285+ROUND, 610: 0.102}},
        {'id': 2, 'ev': "$4,250", "cv": "16%", "sd": "$678", "scenarios": {4690: 0.613-ROUND, 3925: 0.285+ROUND, 2600: 0.078, 2225: 0.024}},
        {'id': 3, 'ev': "$4,208", "cv": "9%", "sd": "$385", "scenarios": {4490: 0.613-ROUND, 4110: 0.078, 3725: 0.285+ROUND, 3050: 0.024}},
        {'id': 4, 'ev': "$4,148", "cv": "6%", "sd": "$228", "scenarios": {4225: 0.898, 3470: 0.102}},
        {'id': 5, 'ev': "$3,938", "cv": "4%", "sd": "$151", "scenarios": {3990: 0.613-ROUND, 3975: 0.285+ROUND, 3610: 0.078, 3220: 0.024}},
        {'id': 6, 'ev': "$3,870", "cv": "0%", "sd": "$0", "scenarios": {3870: 1.0}},
    ]

    try:
        with open("llms_decision_support/data_files/scenarios_and_probabilities.json", 'r') as f:
            s_and_ps_dict = json.load(f)
    except:
        pass
    
    def round_shares(shares):
        # total = sum(shares.values())
        rounded_shares = {k: round(v, 2) for k, v in shares.items()}  # Initial rounding
        remainder = round(1.00 - sum(rounded_shares.values()), 2)  # Compute remainder

        # Compute decimal remainders for ranking
        remainders = sorted(shares.keys(), key=lambda k: shares[k] - rounded_shares[k], reverse=True)

        # Distribute the remainder (add or subtract 0.01 to highest remainders)
        for i in range(int(remainder * 100)):  # Convert to cent units
            rounded_shares[remainders[i]] += 0.01  # Adjust top remainders first

        return rounded_shares

    # Transform values into nested dictionaries
    SCENARIOS_PROBS_DICT = {}
    for key, value in s_and_ps_dict.items():
        # Split by semicolon to get multiple key-value pairs
        nested_items = value.split("; ")
        
        # Convert to dictionary (splitting each "key: value" pair)
        nested_dict = {int(k.strip()): float(v) for k, v in (item.split(": ") for item in nested_items)}
        
        nested_dict = round_shares(nested_dict)
        
        # Store in the transformed dictionary
        SCENARIOS_PROBS_DICT[key] = nested_dict