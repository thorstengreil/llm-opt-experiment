from otree.api import *
from llms_decision_support.python_files.constants import C

# To be imported via locals().update(...) in __init__.py
# (otree does not allow true external definition of Player class)
player_fields = dict(
    subject_id = models.StringField(
        label="Please provide the participant ID (=the number of your computer, e.g. '29') you received at check-in (keep paper slip for payment later):"
    ),
    informed_consent = models.IntegerField(
        choices=[
            [1, "I consent to participate"],
            [2, "I do not consent to participate"],
        ],
        widget=widgets.RadioSelect,
    ),

    termination_flag = models.BooleanField(initial=False),
    in_treatment_group_toggle = models.BooleanField(),

    # Payoffs
    payoff_currency = models.FloatField(initial=C.BASE_PAYOFF),
    payoff_currency_unrounded = models.FloatField(initial=C.BASE_PAYOFF),
    payoff_uq_bonus_currency = models.FloatField(initial=0.0),
    achieved_nr_of_uq_bonuses = models.IntegerField(initial=0),
    payoff_decisions_currency = models.FloatField(initial=0.0),
    payoff_experiment_currency = models.IntegerField(), 

    # # Counts how many times the answers to a set of questions were not fully correct
    uq1_tries_left = models.IntegerField(initial=C.MAX_UQ_TRIES),
    uq2_tries_left = models.IntegerField(initial=C.MAX_UQ_TRIES),
    uq3_tries_left = models.IntegerField(initial=C.MAX_UQ_TRIES),
    uq4_tries_left = models.IntegerField(initial=C.MAX_UQ_TRIES),
    uq5_tries_left = models.IntegerField(initial=C.MAX_UQ_TRIES),
    uq6_tries_left = models.IntegerField(initial=C.MAX_UQ_TRIES),

    # # Understanding questions (UQ) 1
    rules_bonus_for_understanding = models.IntegerField(
        label="""(Q1.1) [Fill in the blanks] You receive ______ per page if all
        understanding questions on it are answered correctly on the first try and a maximum of ______ across all pages.""",
        choices=[
            [1, f"{C.CURRENCY} {(C.UQ_BONUS_PER_PAGE/2):.2f}; {C.CURRENCY} {((C.UQ_BONUS_PER_PAGE * C.NR_OF_UQ_PAGES)/2):.2f}"],
            [2, f"{C.CURRENCY} {C.UQ_BONUS_PER_PAGE:.2f}; {C.CURRENCY} {(C.UQ_BONUS_PER_PAGE * C.NR_OF_UQ_PAGES):.2f}"],
            [3, f"{C.CURRENCY} {(C.UQ_BONUS_PER_PAGE*2):.2f}; {C.CURRENCY} {((C.UQ_BONUS_PER_PAGE * C.NR_OF_UQ_PAGES)*2):.2f}"],
            [4, f"{C.CURRENCY} {(C.UQ_BONUS_PER_PAGE*3):.2f}; {C.CURRENCY} {((C.UQ_BONUS_PER_PAGE * C.NR_OF_UQ_PAGES)*3):.2f}"],
        ],
    ),

    consequences_maximum_failures = models.IntegerField(
        label=f"""(Q1.2) What happens if you fail to answer all understanding questions correctly
        on any page {C.MAX_UQ_TRIES} times""",
        choices=[
            [1, "The experiment ends for you. You receive the fixed payoff plus any earned bonus payments."],
            [2, "You have one more try."],
            [3, "The experiment ends for you. You do not receive the fixed payoff, only any earned bonus payments."],
            [4, "Nothing, you can just continue."],
        ],
    ),

    decisions_influence_on_payoff = models.IntegerField(
        label="""(Q1.3) [Fill in the blanks] Your payoff ______""",
        choices=[
            [1, "does not relate to your decisions and is 100% random."],
            [2, "is a direct result of your decisions, without randomness."],
            [3, "depends on the performance of other participants."],
            [4, "is based on your decisions and may vary due to randomness."],
        ],
    ),

    # Understanding questions (UQ) 2
    parts_experiment = models.IntegerField(
        label="(Q2.1) [Fill in the blanks] The experiment consists of ______ part(s). The parts are ______",
        choices=[
            [1, "2; the same"],
            [2, "2; different"],
            [3, "3; the same"],
            [4, "4; no repetitions of each other"],
        ],
    ),

    network_structure = models.IntegerField(
        label="(Q2.2) What is the structure of the supply chain you will be managing in part 1?",
        choices=[
            [1, "3 suppliers, 1 roastery, and 2 customers"],
            [2, "3 suppliers, 2 roasteries, and 3 customers"],
            [3, "2 suppliers, 3 roasteries, and 2 customers"],
            [4, "1 supplier, 1 roastery, and 1 customer"],
        ],
    ),

    task = models.IntegerField(
        label="(Q2.3) What do you have to do in part 1?",
        choices=[
            [1, "Decide to which customers you deliver roasted coffee."],
            [2, "Decide at which roasting intensity to operate (light or dark coffee)"],
            [3, "Decide how much coffee to ship from suppliers to roasteries and customers."],
            [4, "Decide which suppliers and roasteries to activate."],
        ],
    ),

    compensation_influence = models.IntegerField(
        label="(Q2.4) What influences your outcome for part 1?",
        choices=[
            [1, "The stock price performance of the suppliers in the network."],
            [2, "The profit achieved through your activation decisions."],
            [3, "The economic viability of the customers in the network."],
            [4, "Using different transportations modes for a given route between a supplier and a roastery."],
        ],
    ),

    both_parts_payoff = models.IntegerField(
        label="""(Q2.5) Which statement is TRUE?""",
        choices=[
            [1, "Neither part 1 or 2 will influence your payoff, you always receive the same amount."],
            [2, "Only part 1 influences your payoff"],
            [3, "Only part 2 influences your payoff."],
            [4, "Your final payoff will be determined randomly (50:50 chance) from your outcomes in part 1 and 2."],
        ],
    ),

    fictional_currency = models.IntegerField(
        label="(Q2.6) What is the fictional currency used in the experiment?",
        choices=[
            [1, "Disruption Dollars (DIS$)."],
            [2, "Supply Chain Dollars (SC$)."],
            [3, "Coffee Dollars (COF$)."],
            [4, "Roastery Activation Dollars (RA$)."],
        ],
    ),

    # Understanding questions (UQ) 3
    activation_requirement = models.IntegerField(
        label="(Q3.1) What is required to deliver coffee to customers?",
        choices=[
            [1, "At least one supplier or one roastery must be activated."],
            [2, "At least one supplier and one roastery must be activated."],
            [3, "Only one roastery must be activated."],
            [4, "All suppliers and roasteries must be activated."],
        ],
    ),

    profit_definition = models.IntegerField(
        label="(Q3.2) How is profit defined?",
        choices=[
            [1, "Revenue - fixed cost - shipping cost - roasting cost"],
            [2, "Revenue multiplied by the number of suppliers activated"],
            [3, "Total coffee sold"],
            [4, "Shipping costs minus revenue"],
        ],
    ),

    supplier_fixed_cost = models.IntegerField(
        label="""(Q3.3) [Fill in the blanks] If I activate supplier 2, I must pay ____
        in fixed cost to receive a maximum of ____ units of raw coffee (additional shipping cost per unit occur)?""",
        choices=[
            [1, "$250; 250 units"],
            [2, "$600; 100 units"],
            [3, "$750; 200 units"],
            [4, "$400; 125 units"],
            [4, "$600; 250 units"],
            [4, "$500; 125 units"],
            [4, "$700; 250 units"],
        ],
    ),

    roastery_fixed_cost = models.IntegerField(
        label="""(Q3.4) [Fill in the blanks] If I activate roastery 1 in the activation mode 'high',
        I must pay ____ in fixed cost to roast a maximum of ____ units of coffee?""",
        choices=[
            [1, "$250; 250 units"],
            [2, "$600; 100 units"],
            [3, "$750; 200 units"],
            [4, "$400; 125 units"],
            [5, "$600; 250 units"],
            [6, "$500; 125 units"],
            [7, "$700; 250 units"],
        ],
    ),

    suppliers_total_capacity = models.IntegerField(
        label="""(Q3.5) [This is not a trick question] All else aside, how much total capacity across all suppliers would you have to activate to fulfill the total demand for roasted coffee of 230 units?""",
        choices=[
            [1, "≥100 units"],
            [2, "≥125 units"],
            [3, "≥200 units"],
            [4, "≥230 units"],
        ],
    ),

    roasteries_total_capacity = models.IntegerField(
        label="""(Q3.6) [This is not a trick question] All else aside, how much total capacity across all roasteries would you have to activate to fulfill the total demand for roasted coffee of 230 units?""",
        choices=[
            [1, "≥100 units"],
            [2, "≥125 units"],
            [3, "≥200 units"],
            [4, "≥230 units"],
        ],
    ),

    bonus_pool = models.IntegerField(
        label="(Q3.7) Which statement is correct?",
        choices=[
            [1, "Your decisions may lead to an increase or decrease of the bonus pool's final size."],
            [2, "The bonus pool is filled with COF$ 0 in the beginning."],
            [3, "The bonus pool's final size is independent of your decisions in part 1."],
            [4, "Your decisions in part 1 will never influence the bonus pool's final size."],
        ],
    ),

    # Understanding questions (UQ) 4
    fixed_cost_impact = models.IntegerField(
        label="(Q4.1) What happens if you activate a supplier or roastery but it ends up not being used (i.e. no coffee flows through it)?",
        choices=[
            [1, "You will still have to pay the fixed cost for the supplier or roastery."],
            [2, "You will only pay costs if the supplier or roastery is used for coffee flow."],
            [3, "The fixed cost is waived if the coffee flow is zero."],
            [4, "You will not have to pay any costs."],
        ],
    ),

    shipping_influence = models.IntegerField(
        label="(Q4.2) <strong>[Read carefully!]</strong> Which statement is <strong>NOT</strong> correct?",
        choices=[
            [1, "Shipping from suppliers to roasteries to customers is optimized automatically."],
            [2, "Shipping costs per unit differ for the routes in the network."],
            [3, "Based on your roastery and supplier activation decisions, the best shipping routes will be chosen for you."],
            [4, "Shipping costs are always the same, no matter how coffee flows through the network."],
        ],
    ),

    decisions_selection_test = models.StringField(),

    # Understanding questions (UQ) 5
    disruption_timing = models.IntegerField(
        label="(Q5.1) When do disruptions potentially occur in the supply chain?",
        choices=[
            [1, "Before you make your supplier and roastery activation decisions."],
            [2, "After you commit your supplier and roastery activation decisions but before any coffee is shipped or roasted."],
            [3, "After coffee has been delivered to customers."],
            [4, "Never."],
        ],
    ),

    disruption_impact = models.IntegerField(
        label="(Q5.2) What happens to the fixed costs already paid if a disruption occurs?",
        choices=[
            [1, "Fixed costs are refunded."],
            [2, "You only lose the fixed costs for disrupted customers."],
            [3, "Fixed costs are partially refunded, but shipping costs are lost."],
            [4, "All fixed costs are non-refundable (no matter if a disruption occured or not)."],
        ],
    ),

    disruption_definition = models.IntegerField(
        label="(Q5.3) What happens if a supplier or roastery defaults?",
        choices=[
            [1, "You have to wait longer for raw or roasted beans to be delivered."],
            [2, "The affected supplier/roastery can only deliver half the usual amount."],
            [3, "Nothing."],
            [4, "The affected supplier or roastery cannot deliver anything."],
        ],
    ),

    disruption_examples_1 = models.IntegerField(
        label="Which of these 3 entities can be disrupted given this information?",
        choices=[
            [1, "One, two, all or none could be disrupted."],
            [2, "Only Roastery 2 since its risk is the highest."],
            [3, "Only one of them can be disrupted at a time."],
            [4, "None because their probabilities do not sum to 100%"],
        ],
    ),

    disruption_examples_2 = models.IntegerField(
        label="(Q5.5) <strong>[Read carefully!]</strong> For the disruption risk setting in Q5.4, which individual scenario is <strong>NOT</strong> possible?",
        choices=[
            [1, "No disruption anywhere."],
            [2, "Only Roastery 2 defaults."],
            [3, "Supplier 3 and Roastery 2 default."],
            [4, "Supplier 2 and Roastery 1 default."],
            [5, "Only Supplier 3 defaults."],
        ],
    ),

    performance_evaluation = models.IntegerField(
        label="(Q5.6) Which of the following statements is TRUE?",
        choices=[
            [1, "The more risk you take, the more profit you will make with 100% certainty."],
            [2, "Your profit is determined based on your decisions before any disruptions have occured."],
            [3, f"You will always be paid {C.CURRENCY} {C.MAX_DECISIONS_PAYOFF:,.2f} for your decisions."],
            [4, "Your outcome depends on your achieved profit, i.e. it is determined after disruptions may or may not have occured."],
        ],
    ),

    # Understanding questions (UQ) 6
    provided_setting_basis = models.IntegerField(
        label="(Q6.1) What is the provided activation setting based on?",
        choices=[
            [1, "Maximizing profit with no risk."],
            [2, "Maximizing average profit over many runs, considering disruption probabilities."],
            [3, "Minimizing cost across all suppliers and roasteries."],
            [4, "Maximizing revenue only in customers with zero disruptions."],
        ],
    ),

    provided_setting_risk = models.IntegerField(
        label="(Q6.2) What is a characteristic of the provided activation setting?",
        choices=[
            [1, "There is risk involved in achieving the maximum average profit."],
            [2, "The activation setting might ignore disruption probabilities."],
            [3, "The activation setting is always accurate and there is no risk."],
            [4, "The activation setting increases the fixed costs dramatically."],
        ],
    ),

    risk_judgement = models.IntegerField(
        label="For this setting, which of the following sets of decisions with their potential profit scenarios can be seen as most risky?",
        choices=[
            [1, "Decisions: Activate Supplier 2 and Roastery 2; profit scenarios [in COF$]: 1,000 (100%)."],
            [2, "Decisions: Activate Supplier 1 and 3 as well as Roastery 2; profit scenarios [in COF$]: 800 (50%) or 1,200 (50%)."],
            [3, "Decisions: Activate Supplier 3 and Roastery 1; profit scenarios [in COF$]: 1 (25%), 500 (25%), 1,500 (25%) or 2,000 (25%)."],
            [4, "Decisions: Activate Supplier 1 and 2 as well as Roastery 1; profit scenarios [in COF$]: 700 (50%) or 1,300 (50%)."],
        ],
    ),

    decision_support_system_role = models.IntegerField(
        label="(Q6.4) How does the interactive decision support system help?",
        choices=[
            [1, "It guarantees minimum cost."],
            [2, "It does know which disruptions will occur."],
            [3, "It knows the problem setting, provided activation setting, decision task, and helps answer questions but cannot foresee the future."],
            [4, "It reduces fixed and raw coffee shipping cost by renegotiating with suppliers."],
        ],
    ),

    test_question = models.StringField(),

    # Part 1 decision-making context and data
    disruption_risks_info = models.LongStringField(),
    p1_provided_decisions = models.LongStringField(),
    p1_provided_scenarios = models.LongStringField(),
    current_question_to_llm = models.StringField(initial=""),
    questions_counter = models.IntegerField(initial=0),
    all_questions_to_llm = models.LongStringField(initial=""),
    all_answers_from_llm = models.LongStringField(initial=""),
    number_of_debug_iterations = models.IntegerField(),
    p1_decisions = models.LongStringField(),
    p1_scenarios = models.LongStringField(),
    p1_realized_disruptions = models.LongStringField(),
    p1_outcome = models.IntegerField(),

    # Part 2: Problem-specific risk test where 'choices' refers to 6 subdicts in C.CUSTOM_TEST_CHOICES
    p2_decisions = models.IntegerField(
        choices=[1, 2, 3, 4, 5, 6],
        widget=widgets.RadioSelect,
        blank=True,
    ),
    p2_outcome = models.IntegerField(),

    # Part 1 and 2: Post-decision question(s)
    change_p1_decision = models.BooleanField(
        label="""Based on what you learned, would you <strong>change your decisions for part 1</strong> to the ones you made in <strong>part 2</strong>?""",
    ),

    # Post-experiment questions (demographics)
    ev_knowledge = models.IntegerField(
        label="""(1) I am familiar with the statistical concept of the expected value
    (i.e. the weighted sum over all possible values, where a value's weight refers to the value's probability).""",
        choices=[
            [1, "Strongly disagree"],
            [2, "Somewhat disagree"],
            [3, "Neither agree nor disagree"],
            [4, "Somewhat agree"],
            [5, "Strongly agree"],
        ],
        widget=widgets.RadioSelect,
    ),

    variability_knowledge = models.IntegerField(
        label="""(2) I am familiar with the statistical concept of variability
    (i.e. the extent to which values diverge from the overall dataset's mean value).""",
        choices=[
            [1, "Strongly disagree"],
            [2, "Somewhat disagree"],
            [3, "Neither agree nor disagree"],
            [4, "Somewhat agree"],
            [5, "Strongly agree"],
        ],
        widget=widgets.RadioSelect,
    ),

    general_risk_question = models.IntegerField(
        #label="(1) How willing are you to take risks, in general (0: no willingness, 10: very high willingness)?",
        label="""How do you see yourself: are you generally a person who is fully prepared 
    to take risks or do you try to avoid taking risks?<br>(0: not at all willing to take risks, 10: very willing to take risks)""",
        choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    ),

    # demographics questions
    age = models.IntegerField(
        label="What is your age in full (completed) years?",
        min=18, max=130
    ),
    sex = models.StringField(
        label="What is your sex?",
        choices=["Male", "Female", "Diverse", "Prefer not to tell"]
    ),
    nationality = models.StringField(
        label="Which country best describes your nationality?",
        choices=[
            'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Argentina', 
            'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 
            'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin', 
            'Bhutan', 'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil', 
            'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cabo Verde', 'Cambodia', 
            'Cameroon', 'Canada', 'Central African Republic', 'Chad', 'Chile', 'China', 
            'Colombia', 'Comoros', 'Congo', 'Costa Rica', 'Croatia', 'Cuba', 'Cyprus', 
            'Czech Republic', 'Denmark', 'Djibouti', 'Dominica', 'Dominican Republic', 
            'Ecuador', 'Egypt', 'El Salvador', 'Equatorial Guinea', 'Eritrea', 'Estonia', 
            'Eswatini', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia', 
            'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada', 'Guatemala', 'Guinea', 
            'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hungary', 'Iceland', 'India', 
            'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy', 'Jamaica', 'Japan', 
            'Jordan', 'Kazakhstan', 'Kenya', 'Kiribati', 'Kuwait', 'Kyrgyzstan', 'Laos', 
            'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Liechtenstein', 'Lithuania', 
            'Luxembourg', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali', 'Malta', 
            'Marshall Islands', 'Mauritania', 'Mauritius', 'Mexico', 'Micronesia', 'Moldova', 
            'Monaco', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia', 
            'Nauru', 'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 
            'North Korea', 'North Macedonia', 'Norway', 'Oman', 'Pakistan', 'Palau', 'Panama', 
            'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Qatar', 
            'Romania', 'Russia', 'Rwanda', 'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines', 
            'Samoa', 'San Marino', 'Sao Tome and Principe', 'Saudi Arabia', 'Senegal', 'Serbia', 
            'Seychelles', 'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia', 'Solomon Islands', 
            'Somalia', 'South Africa', 'South Korea', 'South Sudan', 'Spain', 'Sri Lanka', 'Sudan', 
            'Suriname', 'Sweden', 'Switzerland', 'Syria', 'Taiwan', 'Tajikistan', 'Tanzania', 'Thailand', 
            'Timor-Leste', 'Togo', 'Tonga', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan', 
            'Tuvalu', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States', 
            'Uruguay', 'Uzbekistan', 'Vanuatu', 'Vatican City', 'Venezuela', 'Vietnam', 'Yemen', 'Zambia', 
            'Zimbabwe'
        ],
    ),
    education = models.StringField(
        label="Which best describes your highest level of completed education?",
        choices=[
            "High school",
            "Undergraduate",
            "Master's degree",
            "PhD",
            "Other"
        ]
    ),
    position = models.StringField(
        label="What best describes your current position or role?",
        choices=[
            "Undergraduate student",
            "Graduate student (Master's)",
            "Graduate student (PhD)",
            "Employee (<5 years of experience)",
            "Employee (>= 5 years of experience)",
            "Self-employed",
            "Other"
        ]
    ),
    # In the experiment, this demographics field is placed on the first page
    # (due to participant hiring policies; to safeguard correct affiliation before the start of the experiment)
    degree_program = models.StringField(
        label=("If you are a student, please select your degree program. Otherwise, select 'not applicable'."),
        choices=[
            "Management & Technology (B.Sc.)",
            "Management & Technology (M.Sc.)",
            "Master in Management (M.Sc.)",
            "Master in Finance & Information Management (M.Sc.)",
            "Master in Consumer Science (M.Sc.)",
            "Other/Not applicable",
        ],
    ),
    degree_specialization_tech_bsc = models.StringField(
        label=("If applicable, please select the technical specialization of your degree program Management & Technology (B.Sc.). Otherwise, select 'not applicable'."),
        choices=[
            "Chemistry",
            "Computer Engineering",
            "Electrical & Information Technology",
            "Informatics",
            "Mechanical Engineering",
            "Medicine",
            "Other/Not applicable (please specifiy below)",
        ],
    ),
    degree_specialization_tech_msc = models.StringField(
        label=("If applicable, please select the technical specialization of your degree program Management & Technology (M.Sc.). Otherwise, select 'not applicable'."),
        choices=[
            "Chemistry",
            "Computer Engineering",
            "Electrical & Information Technology",
            "Industrial Engineering",
            "Informatics",
            "Mechanical Engineering",
            "Sustainable Energies",
            "Other/Not applicable (please specifiy below)",
        ],
    ),
    degree_specialization_mgmt_msc = models.StringField(
        label=("If applicable, please select the management specialization of your degree program Management & Technology (M.Sc.). Otherwise, select 'not applicable'."),
        choices=[
            "Economics & Econometrics",
            "Energy Markets",
            "Finance and Accounting",
            "Innovation & Entrepreneurship",
            "Life Sciences Management & Policy",
            "Management & Marketing",
            "Operations & Supply Chain Management",
            "Other/Not applicable (please specifiy below)",
        ],
    ),
    chatgpt_experience = models.IntegerField(
        label="""(3) I have experience in interacting with Chatbots 
                    based on Large Language Models (e.g. OpenAI's ChatGPT).""",
        choices=[
            [1, "Strongly disagree"],
            [2, "Somewhat disagree"],
            [3, "Neither agree nor disagree"],
            [4, "Somewhat agree"],
            [5, "Strongly agree"],
        ],
        widget=widgets.RadioSelect
    ),
    optimization_experience = models.IntegerField(
        label="""(4) I have worked with mathematical optimization models
                    (either conceptually or practically (i.e. implementation)).""",
        choices=[
            [1, "Strongly disagree"],
            [2, "Somewhat disagree"],
            [3, "Neither agree nor disagree"],
            [4, "Somewhat agree"],
            [5, "Strongly agree"],
        ],
        widget=widgets.RadioSelect
    ),
    english_native_speaker = models.IntegerField(
        label="""Which of the following describes best how you learned English?""",
        choices=[
            [1, "Native English speaker (i.e. English is your mother tongue)"],
            [2, "Non-native English speaker (i.e. you learned English as a second language (e.g. at school))"],
        ]
    ),

    english_proficiency = models.IntegerField(
        label="""In addition, how would you rate your proficiency in English?""",
        choices=[
            [1, """Proficient/Advanced: I can understand complex texts and conversations with ease,
                and I can express myself fluently and accurately in various contexts."""],
            [2, """Upper Intermediate/Intermediate: I can understand the main points of clear standard input
                on familiar topics and can produce connected text on topics that are familiar or of personal interest."""],
            [3, """Elementary/Beginner: I can understand and use basic sentences and expressions needed for simple,
                everyday communication and can handle very short social exchanges."""],
        ],
        widget=widgets.RadioSelect
    ),

    open_feedback = models.LongStringField(
        label="Would you like to give any additional feedback (field can be left blank)?", blank=True),

    objective = models.IntegerField(
        label="What will determine your payoff and should therefore guide your decision-making?",
        choices=[
            [1, "Cost"],
            [2, "Revenue"],
            [3, "Supply capacity"], 
            [4, "Roasting capacity"],
            [5, "Share of served demand for roasted coffee"],
            [6, "Profit (after potential disruptions occured)"]
        ]
    ),
    decision_types = models.IntegerField(
        label="Which decisions do you have to take yourself in the experiment?",
        choices=[
            [1, "1. Raw coffee amounts, 2. Roasting amounts (light and dark), 3. Shipping amounts (light and dark)"],
            [2, "1. Supplier activation (yes/no), 2. Roastery activation (yes/no)"],
            [3, "1. Supplier activation (yes/no), 2. Roastery capacity activation (zero/low/high)"],
            [4, "1. Raw coffee amounts, 2. Packaging sizes, 3. Wholesale prices"]
        ]
    ),
    questions_yes_no = models.IntegerField(
        label="(For LLM treatment only) Can you ask multiple questions about the decision setting or not?",
        choices=[
            [1, "No, you cannot ask qeustions at all"],
            [2, "No, you can only ask one question"],
            [3, "Yes, you can ask multiple questions"]
        ]
    ),
)