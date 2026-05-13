def calculate_metrics(results):
    """Calculate economic and simplified grid usefulness indicators.

    Approximate import reduction is intentionally simple:
    for each generation hour, count min(generation_MWh, import_MW). Because the
    model is hourly, import_MW is treated as MWh over that hour. This is not a
    grid-flow calculation, only a first indicator of possible avoided imports.
    """
    generation_import_reduction = results.apply(
        lambda row: min(row["generation_MWh"], row["import_MW"]),
        axis=1,
    )

    return {
        "total_revenue_EUR": results["revenue_EUR"].sum(),
        "total_cost_EUR": results["cost_EUR"].sum(),
        "total_profit_EUR": results["profit_EUR"].sum(),
        "total_pumped_energy_MWh": results["pump_MWh"].sum(),
        "total_generated_energy_MWh": results["generation_MWh"].sum(),
        "pumping_hours": int((results["pump_MWh"] > 0).sum()),
        "generation_hours": int((results["generation_MWh"] > 0).sum()),
        "final_storage_MWh": results["storage_MWh"].iloc[-1],
        "approximate_import_reduction_MWh": generation_import_reduction.sum(),
    }
