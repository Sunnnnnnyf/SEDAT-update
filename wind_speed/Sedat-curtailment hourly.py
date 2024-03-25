import pandas as pd
from pyomo.environ import ConcreteModel, Var, Objective, NonNegativeReals, minimize, Constraint, Param, RangeSet, SolverFactory, value, assert_optimal_termination


# Load data
df = pd.read_csv('/Users/fengxiaotong/Desktop/wind solar test 1.csv')
df['time'] = pd.to_datetime(df['time'], format='%H:%M')
df['time_index'] = ((df['day'] - 1) * 24) + df['time'].dt.hour

# Create model
model = ConcreteModel()

# Define sets
model.T = RangeSet(95)  # We could change the range based on our purpose

# Initialize parameters
def init_param(model, param_name):
    return {t: df.set_index('time_index').at[t, param_name] for t in model.T}

model.max_wind_output = Param(model.T, initialize=lambda model, t: init_param(model, 'wind capacity (kwh)')[t], within=NonNegativeReals)
model.max_solar_output = Param(model.T, initialize=lambda model, t: init_param(model, 'solar capacity (kwh)')[t], within=NonNegativeReals)
model.energy_demand = Param(model.T, initialize=lambda model, t: init_param(model, 'water desalination demand (kwh)')[t], within=NonNegativeReals)

# Variables
model.x_wind = Var(model.T, within=NonNegativeReals, bounds=(0, None))
model.x_solar = Var(model.T, within=NonNegativeReals, bounds=(0, None))
model.x_fossil = Var(model.T, within=NonNegativeReals, bounds=(0, None))


# Coefficients-cost $/Kwh
wind_coe = 37
solar_coe = 34
LCOF = 50

def objective_rule(model):
    return sum(
        ((wind_coe * ((model.max_wind_output[t]))+
        (solar_coe * (model.max_solar_output[t])) +
        (model.x_fossil[t] * LCOF))/model.energy_demand[t]) for t in model.T)


model.Objective = Objective(rule=objective_rule, sense=minimize)
# Objective

# Constraints
def wind_constraint_rule(model, t):
    return model.x_wind[t] <= model.max_wind_output[t]
model.WindConstraint = Constraint(model.T, rule=wind_constraint_rule)

def solar_constraint_rule(model, t):
    return model.x_solar[t] <= model.max_solar_output[t]
model.SolarConstraint = Constraint(model.T, rule=solar_constraint_rule)

def demand_satisfaction_rule(model, t):
    return model.x_wind[t] + model.x_solar[t] + model.x_fossil[t] >= model.energy_demand[t]

model.DemandSatisfactionConstraint = Constraint(model.T, rule=demand_satisfaction_rule)


# Solve the model
solver = SolverFactory('ipopt')
results = solver.solve(model, tee=False)
assert_optimal_termination(results)

# Print results
for t in model.T:
    print(f'Hour: {t}, Wind: {value(model.x_wind[t])} Kwh, Solar: {value(model.x_solar[t])} Kwh, Fossil: {value(model.x_fossil[t])} Kwh')

# print final cumulative sum







