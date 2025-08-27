import gurobipy as grb
import numpy as np

def evaluate_deterministic(fixed_activation_decisions, specific_disruption_outcome):
    """
    This function evaluates exactly one deterministic scenario,
    i.e. one specific set of (committed) activation decisions under a fixed realization of disruptions.
    
    Args:
        fixed_activation_decisions : dict
            Maps all suppliers or roasteries to activation decisions:
                - Suppliers: "activate" or "do not activate".
                - Roasteries: "do not activate", "activate (low)", or "activate (high)".
            Example: {"supplier1": "activate", [...],  "roastery2": "activate (low)"}

        specific_disruption_outcome: dict
            Indicates for all suppliers/roasteries whether a disruption occurs (`True` for disruption, `False` otherwise).
            Example: {"supplier1": True, [...], "roastery2": False}

    Returns:
        Profit as Float number for this specific decisions and disruptions setting as per the input parameters.
    """

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

    # Fixed income from existing bonus pool
    fixed_income_bonuspool = 2210

    suppliers = list(set(i[0] for i in shipping_cost_supplier_to_roastery.keys()))
    roasteries = list(set(i[0] for i in shipping_cost_roastery_to_customers.keys()))
    customers = list(set(i[1] for i in shipping_cost_roastery_to_customers.keys()))
    suppliers.sort()
    roasteries.sort()
    customers.sort()

    # Create new environment and model
    env = grb.Env(params={"OutputFlag": 0})
    model = grb.Model(env=env)

    # Create Gurobi variables
    coffee_flow_light = model.addVars(roasteries, customers, vtype=grb.GRB.INTEGER, name="coffee_flow_light")
    coffee_flow_dark = model.addVars(roasteries, customers, vtype=grb.GRB.INTEGER, name="coffee_flow_dark")
    coffee_flow_raw = model.addVars(suppliers, roasteries, vtype=grb.GRB.INTEGER, name="coffee_flow_raw")
    roastery_activation = model.addVars(roasteries, ['low', 'high'], vtype=grb.GRB.BINARY, name="roastery_activation")
    supplier_activation = model.addVars(suppliers, vtype=grb.GRB.BINARY, name="supplier_activation")

    # IF NEEDED, ADD NEW DATA CODE HERE

    # Profit objective
    revenue = grb.quicksum(
        (coffee_flow_light[r, c] + coffee_flow_dark[r, c]) * selling_price
        for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
    )

    shipping_costs = grb.quicksum(
        coffee_flow_raw[s, r] * shipping_cost_supplier_to_roastery[(s, r)]
        for s, r in shipping_cost_supplier_to_roastery.keys() if 'supplier' in s
    ) + grb.quicksum(
        (coffee_flow_light[r, c] + coffee_flow_dark[r, c]) * shipping_cost_roastery_to_customers[(r, c)]
        for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
    )

    variable_roasting_costs = grb.quicksum(
        coffee_flow_light[r, c] * variable_roasting_cost_light[r] +
        coffee_flow_dark[r, c] * variable_roasting_cost_dark[r]
        for r, c in shipping_cost_roastery_to_customers.keys() if 'customer' in c
    )

    fixed_roasting_costs = grb.quicksum(roastery_activation[r, level] * fixed_roasting_cost[r][level]
                            for r in roasteries for level in ['low', 'high'])

    fixed_supplier_costs = grb.quicksum(supplier_activation[s] * fixed_supplier_cost[s] for s in suppliers)

    # Set objective to maximize profit
    model.setObjective(fixed_income_bonuspool + revenue - shipping_costs - variable_roasting_costs - fixed_roasting_costs - fixed_supplier_costs, grb.GRB.MAXIMIZE)

    # Constraint list to suppress console output
    cl = []

    # Adding constraints
    # Only one roastery activation mode is chosen
    for r in roasteries:
        cl.append(model.addConstr(roastery_activation[r, 'low'] + roastery_activation[r, 'high'] <= 1, name=f"roastery_activation_consistency_{r}"))

    # Limit roasted flows by roasting capacity
    for r in roasteries:
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_light[r, c] + coffee_flow_dark[r, c] for c in customers if (r, c) in shipping_cost_roastery_to_customers.keys())
            <= roastery_capacity[r] * (roastery_activation[r, 'low'] + 2 * roastery_activation[r, 'high']),
            name=f"max_capacity_{r}"
        ))

    # Serve demand (not all demand must be fulfilled)
    for c in customers:
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_light[r, c] for r in roasteries if (r, c) in shipping_cost_roastery_to_customers.keys())
            <= coffee_demand['light'][c], f"demand_light_{c}"
        ))
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_dark[r, c] for r in roasteries if (r, c) in shipping_cost_roastery_to_customers.keys())
            <= coffee_demand['dark'][c], f"demand_dark_{c}"
        ))

    # Conserve all flows
    for r in roasteries:
        cl.append(model.addConstr(
            grb.quicksum(coffee_flow_raw[s, r] for s in suppliers if (s, r) in shipping_cost_supplier_to_roastery.keys())
            == grb.quicksum(coffee_flow_light[r, c] + coffee_flow_dark[r, c] for c in customers if (r, c) in shipping_cost_roastery_to_customers.keys()),
            name=f"conservation_of_flow_{r}"
        ))

    # Limit supplier capacity
    for s in suppliers:
        cl.append(model.addConstr(grb.quicksum(coffee_flow_raw[s, r] for r in roasteries if (s,r) in shipping_cost_supplier_to_roastery.keys())
                        <= supplier_activation[s] * supplier_capacity[s], name=f"supplier_activation_{s}"))

    # Incorporate fixed user decisions and realized disruptions
    for entity, decision in fixed_activation_decisions.items():
        if entity in suppliers:
            if decision == "activate":
                model.addConstr(supplier_activation[entity] == 1, name=f"enforce_{entity}_choice")
                if specific_disruption_outcome.get(entity, False):
                    model.addConstr(
                        grb.quicksum(coffee_flow_raw[entity, r] for r in roasteries if (entity, r) in shipping_cost_supplier_to_roastery) == 0,
                        name=f"zero_flow_{entity}")
            else:
                model.addConstr(supplier_activation[entity] == 0, name=f"enforce_{entity}_choice")
        
        elif entity in roasteries:
            if decision == "do not activate":
                model.addConstr(roastery_activation[entity, 'low'] + roastery_activation[entity, 'high'] == 0, name=f"enforce_{entity}_choice")
            else:
                if decision == "activate (low)":
                    model.addConstr(roastery_activation[entity, 'low'] == 1, name=f"enforce_{entity}_choice")
                elif decision == "activate (high)":
                    model.addConstr(roastery_activation[entity, 'high'] == 1, name=f"enforce_{entity}_choice")
                if specific_disruption_outcome.get(entity, False):
                    model.addConstr(
                        grb.quicksum(coffee_flow_light[entity, c] + coffee_flow_dark[entity, c] for c in customers if (entity, c) in shipping_cost_roastery_to_customers) == 0,
                        name=f"zero_flow_{entity}")

    # IF NEEDED, ADD NEW CONSTRAINT CODE HERE

    # Solve model
    model.update()
    model.optimize()

    status = model.Status
    if status == grb.GRB.OPTIMAL:
        #return f"{np.round(model.objVal, 0):,.0f}"
        return np.round(model.objVal,0)
    else:
        result = ""
        if status == grb.GRB.UNBOUNDED:
            result = "unbounded"
        elif status == grb.GRB.INF_OR_UNBD:
            result = "inf_or_unbound"
        elif status == grb.GRB.INFEASIBLE:
            result = "infeasible"
            model.computeIIS()
            constrs = [c.ConstrName for c in model.getConstrs() if c.IISConstr]
            result += "\nConflicting Constraints:\n" + str(constrs)
            result += """\nDo not print all infeasible constraints. Simply mention
            the reason why they are infeasible (e.g. demand cannot be satisfied).
            """
        else:
            result = "Model Status:" + str(status)
        return result