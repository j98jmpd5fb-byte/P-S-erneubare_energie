import pandas as pd

df = pd.read_csv("outputs/price_arbitrage_global/simulation_results.csv")

print(df[["natural_inflow_MWh", "stored_inflow_MWh", "spilled_inflow_MWh"]].describe())
print(df[["natural_inflow_MWh", "stored_inflow_MWh", "spilled_inflow_MWh"]].head())