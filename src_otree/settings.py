from os import environ


SESSION_CONFIGS = [
    # dict(
    #     name='operational_uncertainty',
    #     display_name="Operational Uncertainty",
    #     app_sequence=['operational_uncertainty'],
    #     num_demo_participants=10,
    # ),
    dict(
        name='llms_decision_support',
        display_name="LLMs for Supply Chain Decision Support",
        app_sequence=['llms_decision_support'],
        num_demo_participants=10,
    )
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ROOMS = [
    dict(name='sloan_brl_lab', display_name='Room for conducting experiments at Sloan Behavioral Research Lab (no participant labels)'),
    dict(name='testing', display_name='Room for testing'),
]

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
Here are some oTree games.
"""


SECRET_KEY = '2205063303433'

INSTALLED_APPS = ['otree']

STATIC_URL = '/static/'