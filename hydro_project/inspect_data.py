import pandas as pd
import numpy as np

df = pd.read_csv("data/simulation_input_2025.csv")

rename_map = {
    "total_import_MW_avg": "import_MW",
    "total_export_MW_avg": "export_MW",
    "total_production_MW_avg": "production_MW",
    "total_consumption_MW_avg": "load_MW",
}

df = df.rename(columns=rename_map)

print(f"Data shape: {df.shape}")

print(f'\nImport range: {df["import_MW"].min():.1f} - {df["import_MW"].max():.1f} MW')
print(f'Export range: {df["export_MW"].min():.1f} - {df["export_MW"].max():.1f} MW')
print(f'Production range: {df["production_MW"].min():.1f} - {df["production_MW"].max():.1f} MW')
print(f'Load range: {df["load_MW"].min():.1f} - {df["load_MW"].max():.1f} MW')
print(f'Price range: {df["price_EUR_per_MWh"].min():.1f} - {df["price_EUR_per_MWh"].max():.1f} EUR/MWh')

net_balance = df["production_MW"] - df["load_MW"]
surplus = np.maximum(net_balance, 0)
deficit = np.maximum(-net_balance, 0)

print(f"\nNet balance range: {net_balance.min():.1f} - {net_balance.max():.1f} MW")

print(f'\nImport median: {df["import_MW"].median():.1f} MW')
print(f'Export median: {df["export_MW"].median():.1f} MW')

print(f'Deficit hours: {(df["load_MW"] > df["production_MW"]).sum()}')
print(f'Surplus hours: {(df["production_MW"] > df["load_MW"]).sum()}')

print("\nUseful 75% thresholds:")
print(f'Import 75% threshold: {df["import_MW"].quantile(0.75):.1f} MW')
print(f'Export 75% threshold: {df["export_MW"].quantile(0.75):.1f} MW')
print(f'Surplus 75% threshold: {pd.Series(surplus[surplus > 0]).quantile(0.75):.1f} MW')
print(f'Deficit 75% threshold: {pd.Series(deficit[deficit > 0]).quantile(0.75):.1f} MW')

# import_th = df["import_MW"].quantile(0.75)
# export_th = df["export_MW"].quantile(0.75)

# net_balance = df["production_MW"] - df["load_MW"]
# surplus = np.maximum(net_balance, 0)
# deficit = np.maximum(-net_balance, 0)

# surplus_th = pd.Series(surplus[surplus > 0]).quantile(0.75)
# deficit_th = pd.Series(deficit[deficit > 0]).quantile(0.75)

# print("\nCondition counts:")
# print("High import hours:", (df["import_MW"] >= import_th).sum())
# print("High export hours:", (df["export_MW"] >= export_th).sum())
# print("High surplus hours:", (surplus >= surplus_th).sum())
# print("High deficit hours:", (deficit >= deficit_th).sum())

# print("\nCombined conditions:")
# print(
#     "High import AND deficit:",
#     ((df["import_MW"] >= import_th) & (net_balance < 0)).sum()
# )
# print(
#     "High export AND surplus:",
#     ((df["export_MW"] >= export_th) & (net_balance > 0)).sum()
# )
# print(
#     "High deficit:",
#     (deficit >= deficit_th).sum()
# )
