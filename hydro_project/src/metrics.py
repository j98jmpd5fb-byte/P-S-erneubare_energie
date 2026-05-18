def calculate_metrics(results, plant=None):
    """Calculate economic, storage, and grid-balancing metrics."""
    total_pumped = float(results.get("pump_MWh", 0.0).sum())
    total_generated = float(results.get("generation_MWh", 0.0).sum())
    total_profit = float(results.get("profit_EUR", 0.0).sum())
    total_cost = float(results.get("cost_EUR", 0.0).sum())
    total_revenue = float(results.get("revenue_EUR", 0.0).sum())

    start_storage = float(results["storage_MWh"].iloc[0]) if len(results) else 0.0
    final_storage = float(results["storage_MWh"].iloc[-1]) if len(results) else 0.0
    storage_change = final_storage - start_storage
    roundtrip_losses = max(0.0, total_pumped - total_generated - storage_change)

    total_deficit_before = float(results.get("deficit_MW", 0.0).sum())
    total_deficit_after = float(results.get("deficit_after_storage_MW", 0.0).sum())
    total_surplus_before = float(results.get("surplus_MW", 0.0).sum())
    total_surplus_after = float(results.get("surplus_after_storage_MW", 0.0).sum())
    import_reduction = float(results.get("import_reduction_MWh", 0.0).sum())

    # ============================================================
    # Grid support metrics
    # ============================================================

    # Pumping during Swiss grid surplus hours
    surplus_pump_mask = (
        (results["action"] == "pump")
        & (results["surplus_MW"] > 0)
    )

    deficit_generate_mask = (
        (results["action"] == "generate")
        & (results["import_MW"] > 0)
    )

    # Surplus absorbed is limited by pump energy and available export capacity
    surplus_absorbed_MWh = (
        results.loc[surplus_pump_mask, ["pump_MWh", "export_MW"]]
        .min(axis=1)
        .sum()
    )

    deficit_reduction_MWh = (
        results.loc[deficit_generate_mask, ["generation_MWh", "import_MW"]]
        .min(axis=1)
        .sum()
    )

    renewable_surplus_pump_mask = (
        surplus_pump_mask
        & (results["renewable_fraction"] >= 0.5)
    )

    renewable_surplus_absorbed_MWh = (
        results.loc[renewable_surplus_pump_mask, ["pump_MWh", "export_MW"]]
        .min(axis=1)
        .sum()
    )

    metrics = {
        "total_revenue_EUR": total_revenue,
        "total_cost_EUR": total_cost,
        "total_profit_EUR": total_profit,
        "total_pumped_MWh": total_pumped,
        "total_generated_MWh": total_generated,
        "roundtrip_losses_MWh": roundtrip_losses,
        "pumping_hours": int((results.get("pump_MWh", 0.0) > 0).sum()),
        "generation_hours": int((results.get("generation_MWh", 0.0) > 0).sum()),
        "final_storage_MWh": final_storage,
        "total_deficit_before_MWh": total_deficit_before,
        "total_deficit_after_MWh": total_deficit_after,
        "deficit_reduction_MWh": deficit_reduction_MWh,
        "total_surplus_before_MWh": total_surplus_before,
        "total_surplus_after_MWh": total_surplus_after,
        "surplus_absorbed_MWh": surplus_absorbed_MWh,
        "import_reduction_MWh": import_reduction,
        "renewable_surplus_absorbed_MWh": renewable_surplus_absorbed_MWh,
    }

    if plant is not None and getattr(plant, "storage_capacity_MWh", None) and plant.storage_capacity_MWh > 0:
        metrics["storage_cycles"] = total_pumped / plant.storage_capacity_MWh

    return metrics
