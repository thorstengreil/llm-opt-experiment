# import behavioral experiment software
from otree.api import *

# import externalized otree modules
from llms_decision_support.python_files.constants import C
from llms_decision_support.python_files.player_fields import player_fields

# Player class and players_agent_dict needed before utils and pages imports
# (due to oTree; otherwise circular import error)
class Player(BasePlayer):
    # otree does not allow true external definition of Player class
    # Thus: import only externally defined fields
    locals().update(player_fields)
# Ensure each player has its own agent environment
players_agent_dict = {}

from llms_decision_support.python_files.pages import *
from llms_decision_support.python_files.utils import *

doc = """
This is an application to deploy our behavioral experiment setting for our
research topic large language models for supply chain decision support
"""

class Subsession(BaseSubsession):
    # Not needed
    pass

class Group(BaseGroup):
    # Not needed
    pass

start = [
    A0_Idle_before_start,
    A1_Introduction,
    A2_Experiment_overview,
]
uq_pages = [
    B_UQ1_Non_performance_payoff,
    B_UQ2_Setting_and_task,
    B_UQ3_Decisions_profit_etc,
    B_UQ4_Decision_selection,
    B_UQ5_Disruptions,
    B_UQ6_Decision_support,
    B_UQX_Summary,
]
experiment = [
    C_P1_Decision_making,
    D_P2_Decision_making,
    E_Post_decision_questions, 
    F_P1_Outcome,
    G_P2_Outcome,
    H_Add_experiment_questions,
]
end = [
    I_Demographics,
    J_Final_page,
    K_No_consent,
]
page_sequence = start + uq_pages + experiment + end

# auto-define form fields to capture page start and end time
# (only possible after page sequence is set)
for page_class in page_sequence:
    page_name_str = page_class.__name__
    # use setattrb() outside of Player class to batch-define form fields
    # (no loops allowed in Player class)
    setattr(Player, f"{page_name_str}_start_time", models.StringField())
    setattr(Player, f"{page_name_str}_end_time", models.StringField())