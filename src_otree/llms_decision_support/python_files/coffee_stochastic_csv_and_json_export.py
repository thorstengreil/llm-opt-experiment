from gurobipy import GRB, Model
import gurobipy as grb
import numpy as np
from gurobipy import GRB, Model
import gurobipy as grb
import numpy as np
import json

enforce_user_input_decisions = False
go_through_all_combinations = True

# Function to fix supplier and roastery activation to input values and re-optimize
def fix_activation_and_optimize(fixed_supplier_activation, fixed_roastery_activation):
    """
    This function accepts fixed supplier and roastery activation values, applies them to the model, 
    and performs a second optimization.
    
    :param fixed_supplier_activation: Dictionary of fixed values for supplier activation {'supplier1': 1, 'supplier2': 0, ...}
    :param fixed_roastery_activation: Dictionary of fixed values for roastery activation {'roastery1_low': 1, 'roastery2_high': 0, ...}
    """
    # Fix supplier activation to the provided input
    for s, activation in fixed_supplier_activation.items():
        supplier_activation[s].start = activation  # Set the value as the starting point
        supplier_activation[s].lb = supplier_activation[s].ub = activation  # Fix the variable

    # Fix roastery activation (low/high) to the provided input
    for r, level_activation in fixed_roastery_activation.items():
        roastery, level = r.split('_')  # Extract roastery and level ('low' or 'high')
        roastery_activation[roastery, level].start = level_activation  # Set the value as the starting point
        roastery_activation[roastery, level].lb = roastery_activation[roastery, level].ub = level_activation  # Fix the variable
    
    # Re-optimize the model with fixed activation values
    model.optimize()
    
def count_profit_occurences(input_dict):
    value_counts = {}
    for value in input_dict.values():
        if value in value_counts:
            value_counts[value] += 1
        else:
            value_counts[value] = 1
    result = {}
    for key in value_counts.keys():
        result[key] = value_counts[key] / num_scenarios
    return result

def format_dict(dict):
    return ', '.join(f'{k}: {v}' for k, v in dict.items())

def format_profit_dict(dict):
    return '; '.join(f'{np.round(k):.0f}: {v}' for k, v in dict.items()) 

# Supply chain data
supplier_capacity = {'supplier1': 250, 'supplier2': 100, 'supplier3': 200}

roastery_capacity = {'roastery1': 125, 'roastery2': 125}

fixed_supplier_cost = {'supplier1': 250, 'supplier2': 600, 'supplier3': 750}

fixed_roasting_cost = {
    'roastery1': {'low': 400, 'high': 600},
    'roastery2': {'low': 500, 'high': 700},
}

variable_roasting_cost_light = {'roastery1': 3, 'roastery2': 5}
variable_roasting_cost_dark = {'roastery1': 5, 'roastery2': 6}

shipping_cost_supplier_to_roastery = {
    ('supplier1', 'roastery1'): 5, ('supplier1', 'roastery2'): 4,
    ('supplier2', 'roastery1'): 6, ('supplier2', 'roastery2'): 3,
    ('supplier3', 'roastery1'): 2, ('supplier3', 'roastery2'): 7
}

shipping_cost_roastery_to_customers = {
    ('roastery1', 'customer1'): 5, ('roastery1', 'customer2'): 3,
    ('roastery1', 'customer3'): 6, ('roastery2', 'customer1'): 4,
    ('roastery2', 'customer2'): 5, ('roastery2', 'customer3'): 2
}

coffee_demand = {
    'light': {'customer1': 20, 'customer2': 30, 'customer3': 40},
    'dark': {'customer1': 20, 'customer2': 20, 'customer3': 100},
}

selling_price = 30

suppliers = ['supplier1', 'supplier2', 'supplier3']
roasteries = ['roastery1', 'roastery2']
customers = ['customer1', 'customer2', 'customer3']

# Scenario generation: Randomly generate 100 scenarios of supplier and roastery defaults
num_scenarios = 1000
np.random.seed(42)  # For reproducibility and consistence across participants

supplier_default_prob = {'supplier1': 0.3, 'supplier2': 0.0, 'supplier3': 0.0}
roastery_default_prob = {'roastery1': 0.1, 'roastery2': 0.0}

fixed_income_bonuspool = 2210

# String to be replaced with round-specific probabilities
disruption_risks_info = {}

for node, prob in disruption_risks_info.items():
    if node in suppliers:
        supplier_default_prob[node] = prob
    elif node in roasteries:
        roastery_default_prob[node] = prob

scenarios = []
for _ in range(num_scenarios):
    supplier_defaults = {s: np.random.rand() < supplier_default_prob[s] for s in suppliers}
    roastery_defaults = {r: np.random.rand() < roastery_default_prob[r] for r in roasteries}
    scenarios.append((supplier_defaults, roastery_defaults))

# Create new environment and model
env = grb.Env(params={"OutputFlag": 0})
model = grb.Model(env=env)

# Create scenario indices (integer-based)
scenario_indices = list(range(num_scenarios))

# First-Stage Decisions (scenario-independent)
roastery_activation = model.addVars(roasteries, ['low', 'high'], vtype=GRB.BINARY, name="roastery_activation")
supplier_activation = model.addVars(suppliers, vtype=GRB.BINARY, name="supplier_activation")

# Second-Stage Decisions (scenario-dependent)
coffee_flow_light = model.addVars(scenario_indices, roasteries, customers, vtype=GRB.INTEGER, name="coffee_flow_light")
coffee_flow_dark = model.addVars(scenario_indices, roasteries, customers, vtype=GRB.INTEGER, name="coffee_flow_dark")
coffee_flow_raw = model.addVars(scenario_indices, suppliers, roasteries, vtype=GRB.INTEGER, name="coffee_flow_raw")

# Objective: Maximize expected profit over all scenarios
expected_margin_contribution = 0

for scenario_idx, (supplier_defaults, roastery_defaults) in enumerate(scenarios):
    
    # Scenario-specific revenue and costs
    revenue = grb.quicksum(
        (coffee_flow_light[scenario_idx, r, c] + coffee_flow_dark[scenario_idx, r, c]) * selling_price
        for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
    )
    
    shipping_costs = grb.quicksum(
        (coffee_flow_light[scenario_idx, r, c] + coffee_flow_dark[scenario_idx, r, c]) * shipping_cost_roastery_to_customers[(r, c)]
        for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
    ) + grb.quicksum(
        coffee_flow_raw[scenario_idx, s, r] * shipping_cost_supplier_to_roastery[(s, r)]
        for s, r in shipping_cost_supplier_to_roastery.keys() if 'supplier' in s
    )
    
    variable_roasting_costs = grb.quicksum(
        coffee_flow_light[scenario_idx, r, c] * variable_roasting_cost_light[r] +
        coffee_flow_dark[scenario_idx, r, c] * variable_roasting_cost_dark[r]
        for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
    )
    
    # Total profit contribution for this scenario
    total_margin_contribution_scenario = revenue - shipping_costs - variable_roasting_costs
    
    expected_margin_contribution += (1 / num_scenarios) * total_margin_contribution_scenario

# Add fixed costs (first-stage decisions, scenario-independent)
fixed_roasting_costs = grb.quicksum(roastery_activation[r, level] * fixed_roasting_cost[r][level]
                                    for r in roasteries for level in ['low', 'high'])
fixed_supplier_costs = grb.quicksum(supplier_activation[s] * fixed_supplier_cost[s] for s in suppliers)

model.setObjective(fixed_income_bonuspool + expected_margin_contribution - fixed_roasting_costs - fixed_supplier_costs, GRB.MAXIMIZE)

# Constraints

# Constraint list to suppress console output
cl = []

# First-stage constraints (roastery activation mode, supplier capacity)
for r in roasteries:
    cl.append(model.addConstr(roastery_activation[r, 'low'] + roastery_activation[r, 'high'] <= 1, name=f"roastery_activation_consistency_{r}"))

# Second-stage constraints (dependent on scenario defaults)
for scenario_idx, (supplier_defaults, roastery_defaults) in enumerate(scenarios):
    
    for r in roasteries:
        if roastery_defaults[r]:  # If roastery defaults in this scenario, no roasting
            cl.append(model.addConstr(
                grb.quicksum(coffee_flow_light[scenario_idx, r, c] + coffee_flow_dark[scenario_idx, r, c]
                             for c in customers if (r, c) in shipping_cost_roastery_to_customers.keys()) == 0,
                name=f"roastery_default_{r}_scenario_{scenario_idx}"
            ))
        
        # Roasting capacity constraint (only applies if roastery is active)
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_light[scenario_idx, r, c] + coffee_flow_dark[scenario_idx, r, c]
                         for c in customers if (r, c) in shipping_cost_roastery_to_customers.keys())
            <= roastery_capacity[r] * (roastery_activation[r, 'low'] + 2 * roastery_activation[r, 'high']),
            name=f"roastery_capacity_{r}_scenario_{scenario_idx}"
        ))
    
    for s in suppliers:
        if supplier_defaults[s]:  # If supplier defaults in this scenario, no supply
            cl.append(model.addConstr(
                grb.quicksum(coffee_flow_raw[scenario_idx, s, r] for r in roasteries if (s, r) in shipping_cost_supplier_to_roastery.keys()) == 0,
                name=f"supplier_default_{s}_scenario_{scenario_idx}"
            ))
    
    # Demand constraints (for each scenario)
    for c in customers:
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_light[scenario_idx, r, c] for r in roasteries if (r, c) in shipping_cost_roastery_to_customers.keys())
            <= coffee_demand['light'][c], name=f"demand_light_{c}_scenario_{scenario_idx}"
        ))
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_dark[scenario_idx, r, c] for r in roasteries if (r, c) in shipping_cost_roastery_to_customers.keys())
            <= coffee_demand['dark'][c], name=f"demand_dark_{c}_scenario_{scenario_idx}"
        ))
    
    # Flow conservation constraints (for each scenario)
    for r in roasteries:
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_raw[scenario_idx, s, r] for s in suppliers if (s, r) in shipping_cost_supplier_to_roastery.keys())
            == grb.quicksum(coffee_flow_light[scenario_idx, r, c] + coffee_flow_dark[scenario_idx, r, c]
                            for c in customers if (r, c) in shipping_cost_roastery_to_customers.keys()),
            name=f"flow_conservation_{r}_scenario_{scenario_idx}"
        ))
    
    for s in suppliers:
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_raw[scenario_idx, s, r] for r in roasteries if (s, r) in shipping_cost_supplier_to_roastery.keys())
            <= supplier_activation[s] * supplier_capacity[s], name=f"supplier_capacity_{s}_scenario_{scenario_idx}"
        ))

# Solve the stochastic model
model.update()
model.optimize()

if model.status == GRB.OPTIMAL:
    if go_through_all_combinations == True:
        import itertools

        # Generate all combinations for suppliers (0 or 1 for each supplier)
        supplier_combinations = list(itertools.product([0, 1], repeat=3))

        # Generate all combinations for roasteries (0, 'L', 'H' for each roastery)
        roastery_states = [0, 'L', 'H']
        roastery_combinations = list(itertools.product(roastery_states, repeat=2))

        # Function to convert roastery states to the required dictionary format
        def convert_roastery_states(roastery_comb):
            return {
                'roastery1_low': 1 if roastery_comb[0] == 'L' else 0,
                'roastery1_high': 1 if roastery_comb[0] == 'H' else 0,
                'roastery2_low': 1 if roastery_comb[1] == 'L' else 0,
                'roastery2_high': 1 if roastery_comb[1] == 'H' else 0,
            }

        # Generate all combinations of suppliers and roasteries
        all_combinations = []
        for supplier_comb in supplier_combinations:
            for roastery_comb in roastery_combinations:
                supplier_activation_dict = {
                    'supplier1': supplier_comb[0],
                    'supplier2': supplier_comb[1],
                    'supplier3': supplier_comb[2],
                }
                roastery_activation_dict = convert_roastery_states(roastery_comb)
                all_combinations.append((supplier_activation_dict, roastery_activation_dict))
        
        data = []

        for comb in all_combinations:
            # Fix supplier and roastery value to a different value (external input)
            fixed_supplier_activation = comb[0]      # suppliers
            fixed_roastery_activation = comb[1]      # roasteries
            fix_activation_and_optimize(fixed_supplier_activation, fixed_roastery_activation)
            
            # Calculate the fixed costs once (they are scenario-independent)
            fixed_roasting_costs_total = sum(
                roastery_activation[r, level].x * fixed_roasting_cost[r][level]
                for r in roasteries for level in ['low', 'high']
            )

            fixed_supplier_costs_total = sum(
                supplier_activation[s].x * fixed_supplier_cost[s]
                for s in suppliers
            )

            profit_per_scenario = {}
            for scenario_idx, (supplier_defaults, roastery_defaults) in enumerate(scenarios):
                # Revenue for this scenario
                revenue = sum(
                    (coffee_flow_light[scenario_idx, r, c].x + coffee_flow_dark[scenario_idx, r, c].x) * selling_price
                    for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
                )

                # Shipping costs for this scenario
                shipping_costs = sum(
                    (coffee_flow_light[scenario_idx, r, c].x + coffee_flow_dark[scenario_idx, r, c].x) * shipping_cost_roastery_to_customers[(r, c)]
                    for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
                ) + sum(
                    coffee_flow_raw[scenario_idx, s, r].x * shipping_cost_supplier_to_roastery[(s, r)]
                    for s, r in shipping_cost_supplier_to_roastery.keys() if 'supplier' in s
                )

                # Variable roasting costs for this scenario
                variable_roasting_costs = sum(
                    coffee_flow_light[scenario_idx, r, c].x * variable_roasting_cost_light[r] +
                    coffee_flow_dark[scenario_idx, r, c].x * variable_roasting_cost_dark[r]
                    for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
                )

                # Profit per scenario: Revenue - all costs (variable + fixed)
                profit_per_scenario[scenario_idx] = (
                    fixed_income_bonuspool + revenue - shipping_costs - variable_roasting_costs
                    - fixed_roasting_costs_total - fixed_supplier_costs_total
                )
                
            # All scenarios and probabilities, min and max profit
            profit_scenarios_and_probabilities = count_profit_occurences(profit_per_scenario)
            min_profit = min(profit_scenarios_and_probabilities.keys())
            max_profit = max(profit_scenarios_and_probabilities.keys())
            print((f"Optimization problem solved. The expected profit is: ${model.objVal:,.0f}. "
                   f"Across all scenarios, the minimum profit is ${min_profit:,.0f} and the maximum is ${max_profit:,.0f}."))

            cv = np.std(list(profit_per_scenario.values())) / model.objVal
            r_helper_dict = {}
            for r in roasteries:
                if roastery_activation[r, 'high'].x == 1:
                    mode = 'high'
                elif roastery_activation[r, 'low'].x == 1:
                    mode = 'low'
                else:
                    mode = 0
                r_helper_dict[r] = mode
            data += [[format_dict(comb[0]), format_dict(r_helper_dict), model.objVal, cv, format_profit_dict(count_profit_occurences(profit_per_scenario))]]

        import pandas as pd
        df = pd.DataFrame(data, columns=["Suppliers", "Roasteries", "EV", "CV", "All Scenarios"])
        
        df.to_csv("data_files/all_combinations_scenarios_input.csv", index=False)
    else:
        if enforce_user_input_decisions == True:      
            # Fix supplier and roastery value to a different value (external input)
            fixed_supplier_activation = {        # 1: activate; 2: do not activate
                'supplier1':    1,
                'supplier2':    0,
                'supplier3':    1,
            }
            fixed_roastery_activation = {        # either 'low' or 'high' can be 1 (or both zero)
                'roastery1_low':    1,
                'roastery1_high':   0,
                'roastery2_low':    0,
                'roastery2_high':   1,
            }
            
            fix_activation_and_optimize(fixed_supplier_activation, fixed_roastery_activation)

        # Calculate the fixed costs once (they are scenario-independent)
        fixed_roasting_costs_total = sum(
            roastery_activation[r, level].x * fixed_roasting_cost[r][level]
            for r in roasteries for level in ['low', 'high']
        )

        fixed_supplier_costs_total = sum(
            supplier_activation[s].x * fixed_supplier_cost[s]
            for s in suppliers
        )

        profit_per_scenario = {}
        for scenario_idx, (supplier_defaults, roastery_defaults) in enumerate(scenarios):
            # Revenue for this scenario
            revenue = sum(
                (coffee_flow_light[scenario_idx, r, c].x + coffee_flow_dark[scenario_idx, r, c].x) * selling_price
                for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
            )

            # Shipping costs for this scenario
            shipping_costs = sum(
                (coffee_flow_light[scenario_idx, r, c].x + coffee_flow_dark[scenario_idx, r, c].x) * shipping_cost_roastery_to_customers[(r, c)]
                for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
            ) + sum(
                coffee_flow_raw[scenario_idx, s, r].x * shipping_cost_supplier_to_roastery[(s, r)]
                for s, r in shipping_cost_supplier_to_roastery.keys() if 'supplier' in s
            )

            # Variable roasting costs for this scenario
            variable_roasting_costs = sum(
                coffee_flow_light[scenario_idx, r, c].x * variable_roasting_cost_light[r] +
                coffee_flow_dark[scenario_idx, r, c].x * variable_roasting_cost_dark[r]
                for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
            )

            # Profit per scenario: Revenue - all costs (variable + fixed)
            profit_per_scenario[scenario_idx] = (
                fixed_income_bonuspool + revenue - shipping_costs - variable_roasting_costs
                - fixed_roasting_costs_total - fixed_supplier_costs_total
            )
        
        # All scenarios and probabilities
        profit_scenarios_and_probabilities = count_profit_occurences(profit_per_scenario)
        formatted_dict = '; '.join([f"${key:,.0f}: {value:.0%}" for key, value in profit_scenarios_and_probabilities.items()])
        print(f"Optimization problem solved. All profit scenarios and their probabilities: {formatted_dict}")
        print()

        # Decisions
        solution = {
            "Supplier activation": {i: bool(int(supplier_activation[i].X)) for i in supplier_activation.keys()},
            "Roastery activation": {i: bool(int(roastery_activation[i].X)) for i in roastery_activation.keys()},
        }
        print("Activation decisions:")
        for decision_type, values in solution.items():
            for index, value in values.items():
                if value == -0.0:
                    value += 0.0
                if value > 0:
                    print(f"- {index}: {value}")



# Convert created csv file to json
# Read the CSV file
df = pd.read_csv(r"llms_decision_support\data_files\all_combinations_scenarios_input.csv", dtype=str)
df = df[["decisions_str", "scenarios_probs"]]
# Convert to dictionary (first column as keys, second as values)
data_dict = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))

# Save as JSON
with open("data_files/scenarios_and_probabilities.json", "w") as f:
    json.dump(data_dict, f, indent=4)

print("JSON file created successfully!")