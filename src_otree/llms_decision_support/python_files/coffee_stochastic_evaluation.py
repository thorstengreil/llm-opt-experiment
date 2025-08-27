"""This module is usable via code created by the LLM.
(Information provided to LLM via helper functions documentation and in-context learning examples)
"""
import gurobipy as grb
import numpy as np

class StochasticModel():
    stoch_model = None
    
    def __init__(self):
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
        self.suppliers = s_capacity.keys()
        suppliers = self.suppliers
        self.roasteries = r_capacity.keys()
        roasteries = self.roasteries
        customers = coffee_demand['light'].keys()
        self.scen_num_range = range(num_scenarios)
        scen_num_range = self.scen_num_range

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
        self.model = grb.Model(env=env)
        model = self.model

        # 1st-stage vars
        self.r_activation = model.addVars(roasteries, ['low', 'high'], vtype=grb.GRB.BINARY, name="r_activation")
        r_activation = self.r_activation
        self.s_activation = model.addVars(suppliers, vtype=grb.GRB.BINARY, name="s_activation")
        s_activation = self.s_activation
        # 2nd-stage vars
        coffee_flow_raw = model.addVars(num_scenarios, suppliers, roasteries, vtype=grb.GRB.INTEGER, name="coffee_flow_raw")
        coffee_flow_light = model.addVars(num_scenarios, roasteries, customers, vtype=grb.GRB.INTEGER, name="coffee_flow_light")
        coffee_flow_dark = model.addVars(num_scenarios, roasteries, customers, vtype=grb.GRB.INTEGER, name="coffee_flow_dark")

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
        self.profit_per_scenario = {n: fixed_income_bonuspool + contribution_per_scenario[n] - fixed_r_cost - fixed_s_cost for n in scen_num_range}
        profit_per_scenario = self.profit_per_scenario
        model.setObjective((1 / num_scenarios) * sum(profit_per_scenario[n] for n in scen_num_range), grb.GRB.MAXIMIZE)

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

    @classmethod
    def evaluate_stochastic(cls, fixed_activation_decisions):
        """
        Use this function if the user asks to evaluate decisions under risk,
        i.e. across various disruption scenarios.
        
        Parameters:
            fixed_activation_decisions : dict
                Maps all(!) suppliers or roasteries to activation decisions:
                    - Suppliers: "activate" or "do not activate".
                    - Roasteries: "do not activate", "activate (low)", or "activate (high)".
                Example: {"supplier1": "activate", [...],  "roastery2": "activate (low)"}

        Return: dict
            - keys: all profit scenarios
            - values: their respective probabilities
        """
        if cls.stoch_model == None:
            cls.stoch_model = StochasticModel()

        model = cls.stoch_model.model
        suppliers = cls.stoch_model.suppliers
        roasteries = cls.stoch_model.roasteries
        scen_num_range = cls.stoch_model.scen_num_range
        s_activation = cls.stoch_model.s_activation
        r_activation = cls.stoch_model.r_activation
        profit_per_scenario = cls.stoch_model.profit_per_scenario

        # Solve initial model
        model.optimize()

        # The user has been provided with this activation setting; change if user asks to evaluate different decisions(!)
        fixed_s_activation = {}
        fixed_r_activation = {}

        # Loop through the original dictionary and populate the new ones
        for key, value in fixed_activation_decisions.items():
            if key in suppliers:
                # Map supplier activation status
                fixed_s_activation[key] = 1 if value == 'activate' else 0
            elif key in roasteries:
                # Initialize default values for roastery
                fixed_r_activation[f"{key}_low"] = 0
                fixed_r_activation[f"{key}_high"] = 0
                if 'high' in value:
                    fixed_r_activation[f"{key}_high"] = 1
                elif 'low' in value:
                    fixed_r_activation[f"{key}_low"] = 1

        # fix activation helper function
        def fix_activation_decisions(fixed_s_activation, fixed_r_activation):
            for s, act in fixed_s_activation.items():
                s_activation[s].lb = s_activation[s].ub = act
            for r, act in fixed_r_activation.items():
                roastery, level = r.split('_')
                r_activation[roastery, level].lb = r_activation[roastery, level].ub = act

        fix_activation_decisions(fixed_s_activation, fixed_r_activation)
        model.optimize()

        # Calculate share of unique profit occurrences
        def profit_occurrences(profit_dict):
            counts = {v: list(profit_dict.values()).count(v) / len(profit_dict) for v in set(profit_dict.values())}
            sorted_counts = sorted(counts.items(), key=lambda item: item[0], reverse=True)
            return {k: v for k, v in sorted_counts}

        profit_probs = profit_occurrences({n: profit_per_scenario[n].getValue() for n in scen_num_range})
        result = profit_probs
        
        return result

# Example
# fixed_activation_decisions = {'supplier1': 'activate', 'supplier2': 'do not activate', 'supplier3': 'activate', 'roastery1': 'activate (low)', 'roastery2': 'activate (high)'}
# profits_and_probs = StochasticModel.evaluate_stochastic(fixed_activation_decisions)
# print(profits_and_probs)