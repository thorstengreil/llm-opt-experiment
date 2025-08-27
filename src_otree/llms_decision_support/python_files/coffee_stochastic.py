"""This module is intentionally kept minimal to improve the efficiency of LLM input and output.
"""
from gurobipy import GRB
import gurobipy as grb
import numpy as np

# supply chain data
s_capacity = {'supplier1': 250, 'supplier2': 100, 'supplier3': 200}
r_capacity = {'roastery1': {'low': 125, 'high': 250}, 'roastery2': {'low': 125, 'high': 250}}
fixed_supplier_cost = {'supplier1': 250, 'supplier2': 600, 'supplier3': 750}
fixed_roasting_cost = {'roastery1': {'low': 400, 'high': 600}, 'roastery2': {'low': 500, 'high': 700}}
variable_roasting_cost_light = {'roastery1': 3, 'roastery2': 5}
variable_roasting_cost_dark = {'roastery1': 5, 'roastery2': 6}
shipping_cost_s_to_r = {('supplier1', 'roastery1'): 5, ('supplier1', 'roastery2'): 4, 
                        ('supplier2', 'roastery1'): 6, ('supplier2', 'roastery2'): 3, 
                        ('supplier3', 'roastery1'): 2, ('supplier3', 'roastery2'): 7}
shipping_cost_r_to_c = {('roastery1', 'customer1'): 5, ('roastery1', 'customer2'): 3, 
                        ('roastery1', 'customer3'): 6, ('roastery2', 'customer1'): 4, 
                        ('roastery2', 'customer2'): 5, ('roastery2', 'customer3'): 2}
coffee_demand = {'light': {'customer1': 20, 'customer2': 30, 'customer3': 40}, 
                 'dark': {'customer1': 20, 'customer2': 20, 'customer3': 100}}
selling_price, fixed_income_bonuspool, num_scenarios = 30, 2210, 1000
suppliers = s_capacity.keys()
roasteries = r_capacity.keys()
customers = coffee_demand['light'].keys()
scen_num_range = range(num_scenarios)

# disruption scenarios
np.random.seed(42)
s_default_prob = {'supplier1': 0.3, 'supplier2': 0.0, 'supplier3': 0.0}
r_default_prob = {'roastery1': 0.1, 'roastery2': 0.0}
scenarios = [
    ({s: np.random.rand() < s_default_prob[s] for s in suppliers},
     {r: np.random.rand() < r_default_prob[r] for r in roasteries})
    for _ in scen_num_range
]

# model setup
env = grb.Env(params={"OutputFlag": 0})
model = grb.Model(env=env)

# 1st-stage vars
r_activation = model.addVars(roasteries, ['low', 'high'], vtype=GRB.BINARY, name="r_activation")
s_activation = model.addVars(suppliers, vtype=GRB.BINARY, name="s_activation")
# 2nd-stage vars
coffee_flow_raw = model.addVars(num_scenarios, suppliers, roasteries, vtype=GRB.INTEGER, name="coffee_flow_raw")
coffee_flow_light = model.addVars(num_scenarios, roasteries, customers, vtype=GRB.INTEGER, name="coffee_flow_light")
coffee_flow_dark = model.addVars(num_scenarios, roasteries, customers, vtype=GRB.INTEGER, name="coffee_flow_dark")

# fix activation helper function
def fix_activation_decisions(fixed_s_activation, fixed_r_activation):
    for s, act in fixed_s_activation.items():
        s_activation[s].lb = s_activation[s].ub = act
    for r, act in fixed_r_activation.items():
        roastery, level = r.split('_')
        r_activation[roastery, level].lb = r_activation[roastery, level].ub = act

# Objective function
contribution_per_scenario = {
    n: (
        grb.quicksum((coffee_flow_light[n, r, c] + coffee_flow_dark[n, r, c]) * selling_price for r, c in shipping_cost_r_to_c)
        - sum((coffee_flow_light[n, r, c] + coffee_flow_dark[n, r, c]) * shipping_cost_r_to_c[r, c] for r, c in shipping_cost_r_to_c)
        - sum(coffee_flow_raw[n, s, r] * shipping_cost_s_to_r[s, r] for s, r in shipping_cost_s_to_r)
        - sum(
            coffee_flow_light[n, r, c] * variable_roasting_cost_light[r] +
            coffee_flow_dark[n, r, c] * variable_roasting_cost_dark[r]
            for r, c in shipping_cost_r_to_c
        )
    )
    for n in scen_num_range
}

fixed_r_cost = sum(r_activation[r, lvl] * fixed_roasting_cost[r][lvl] for r in roasteries for lvl in ['low', 'high'])
fixed_s_cost = sum(s_activation[s] * fixed_supplier_cost[s] for s in suppliers)
profit_per_scenario = {n: fixed_income_bonuspool + contribution_per_scenario[n] - fixed_r_cost - fixed_s_cost for n in scen_num_range}
model.setObjective((1 / num_scenarios) * sum(profit_per_scenario[n] for n in scen_num_range), GRB.MAXIMIZE)

# Constraints
for r in roasteries:
    _=model.addConstr(r_activation[r, 'low'] + r_activation[r, 'high'] <= 1)
for n, (s_defs, r_defs) in enumerate(scenarios):
    for r in roasteries:
        if r_defs[r]:
            _=model.addConstr(sum(coffee_flow_light[n, r, c] + coffee_flow_dark[n, r, c] for c in customers) == 0)
        _=model.addConstr(sum(coffee_flow_light[n, r, c] + coffee_flow_dark[n, r, c] for c in customers) <= sum(r_capacity[r][lvl] * r_activation[r, lvl] for lvl in r_capacity[r].keys()))
        _=model.addConstr(sum(coffee_flow_raw[n, s, r] for s in suppliers) == sum(coffee_flow_light[n, r, c] + coffee_flow_dark[n, r, c] for c in customers))
    for s in suppliers:
        if s_defs[s]:
            _=model.addConstr(sum(coffee_flow_raw[n, s, r] for r in roasteries) == 0)
        _=model.addConstr(sum(coffee_flow_raw[n, s, r] for r in roasteries) <= s_activation[s] * s_capacity[s])
    for c in customers:
        _=model.addConstr(sum(coffee_flow_light[n, r, c] for r in roasteries) <= coffee_demand['light'][c])
        _=model.addConstr(sum(coffee_flow_dark[n, r, c] for r in roasteries) <= coffee_demand['dark'][c])
        
# Solve initial model
model.optimize()

# The user has been provided with this activation setting below; change if user asks to evaluate different decisions(!)
# If the user asks to check additional activation settings, activate enough supplier and
# roastery capacity to meet the total demand for light and dark coffee (without disruptions).
fixed_s_activation = {'supplier1': 1, 'supplier2': 0, 'supplier3': 1}
fixed_r_activation = {'roastery1_low': 0, 'roastery1_high': 1, 'roastery2_low': 0, 'roastery2_high': 0}
fix_activation_decisions(fixed_s_activation, fixed_r_activation)
model.optimize()

# Calculate share of unique profit occurrences
def profit_occurrences(profit_dict):
    counts = {v: list(profit_dict.values()).count(v) / len(profit_dict) for v in set(profit_dict.values())}
    sorted_counts = sorted(counts.items(), key=lambda item: item[0], reverse=True)
    return sorted_counts

profit_probs = profit_occurrences({n: profit_per_scenario[n].getValue() for n in scen_num_range})
formatted_scenarios = '; '.join([f"${key:,.0f}: {value:.0%}" for key, value in profit_probs])
activations = [f"{s}: {True}" for s in s_activation.keys() if s_activation[s].X > 0] + \
              [f"{r}: {lvl}" for r, lvl in r_activation.keys() if r_activation[r, lvl].X > 0]
print(f"Optimization problem solved. Profit scenarios and probabilities: {formatted_scenarios}. Activations: {', '.join(activations)}")