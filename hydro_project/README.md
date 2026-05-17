# Pumped-Storage Hydropower Simulation for Switzerland

This student research/coding project asks whether upgrading a large Swiss
storage hydropower complex, using Grande Dixence / Cleuson-Dixence as a
hypothetical case, with additional pumped-storage capability could be
economically profitable and useful for the Swiss electricity system.

The model simulates a simple operating rule: buy electricity when prices are
low, pump water uphill, and generate electricity when prices are high.

## Important Modelling Point

Pumped storage is not new electricity production. It is storage with losses.
In this project it is treated like a battery: pumping buys electricity from the
market, only part of that energy is stored because round-trip efficiency is
below 1, and later generation sells energy by drawing down the stored energy.

This means pumped storage can help a Netto Null electricity system indirectly:
it shifts electricity from surplus or low-price hours to scarce or high-price
hours. It does not create additional net energy.

## First-Version Assumptions

- The model runs hour by hour.
- It uses a simple threshold strategy, not advanced linear programming.
- It ignores detailed grid constraints and water inflows.
- Prices are assumed to be known for the simulated period.
- Pumping and generation are limited by plant power ratings.
- Storage is kept between zero and the maximum storage capacity.
- Round-trip efficiency is set to 80 percent in the sample case.
- The import reduction metric is simplified and is not a Swissgrid power-flow
  calculation.

## Repository Structure

```text
hydro_project/
    README.md
    requirements.txt
    main.py
    data/
        plant_parameters.csv
        hourly_market_data_sample.csv
    src/
        __init__.py
        plant.py
        data_loader.py
        strategy.py
        simulation.py
        metrics.py
        plots.py
    outputs/
    tests/
        test_simulation.py
```

## Data Needed Later

The included data is synthetic so the project runs immediately. A real research
version should replace it with data from sources such as:

- SFOE/BFE WASTA hydropower plant data
- Swiss day-ahead hourly electricity prices from ENTSO-E, the Swiss energy
  dashboard, or opendata.swiss
- Swissgrid production, consumption, import, and export data

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the simulation from inside the `hydro_project` folder:

```bash
python main.py
```

The script prints summary metrics, saves hourly results to
`outputs/simulation_results.csv`, and saves plots in `outputs/`.

Run tests:

```bash
pytest
```

## Replacing Synthetic Data

Replace `data/hourly_market_data_sample.csv` with a CSV using these columns:

```text
datetime, price_EUR_per_MWh, load_MW, production_MW, import_MW, export_MW
```

Replace `data/plant_parameters.csv` with one row using these columns:

```text
plant_name, storage_capacity_MWh, turbine_power_MW, pump_power_MW, roundtrip_efficiency, initial_storage_MWh
```

Keep units consistent. Prices are EUR/MWh, power is MW, hourly energy is MWh.

## Limitations

This first model is intentionally simple. It does not include reservoir inflows,
seasonal water constraints, balancing markets, taxes, grid tariffs, investment
costs, start-up limits, ramping limits, or detailed Swiss transmission
constraints. It is a clear base for later extensions, such as optimization,
real historical data, scenarios for Netto Null electricity demand, and
investment payback analysis.

## Detailed Project Description (for new readers)

This repository implements a transparent, rule-based hourly pumped-storage
simulation intended for teaching and exploratory research. The model is
intentionally simple and focuses on illustrating operational trade-offs and
scenario comparison rather than providing a production-ready hydrological
model.

Key behaviors implemented in the codebase:

- Hourly simulation of a single pumped-storage plant represented by
  `src/plant.py`.
- Several dispatch scenarios (rule-based strategies) that decide whether the
  plant should `pump`, `generate`, or remain `idle` each hour.
- Accounting of economic flows (cost/revenue/profit) and simple grid-use
  indicators (deficit/surplus, import reduction, surplus absorbed).
- Per-scenario CSV outputs and multiple diagnostic plots saved under
  `outputs/<scenario>/`.

## Repository structure and module responsibilities

- `main.py`: top-level runner. Loads data, defines scenario set, runs each
  scenario, collects per-scenario metrics, and writes comparison outputs.
- `data/plant_parameters.csv`: plant parameters (one row per run). See Inputs
  section below for required and optional columns.
- `data/hourly_market_data_sample.csv`: synthetic example market and grid
  time series (datetime, price, load, production, import, export).
- `src/data_loader.py`: helper functions to read and validate CSV inputs.
- `src/plant.py`: `HydroPlant` class modeling storage state, pumping and
  generation with configurable efficiencies and optional physical parameters.
- `src/strategy.py`: contains rule-based strategy functions and a mapping
  `SCENARIO_STRATEGIES` with the scenario names used by `main.py`.
- `src/simulation.py`: `run_simulation()` executes the hourly loop and
  records extended hourly outputs (net balance, deficit/surplus before and
  after storage actions, import/export interaction, thresholds used).
- `src/metrics.py`: `calculate_metrics()` aggregates scenario performance and
  grid indicators into a dictionary saved to the summary CSV.
- `src/plots.py`: plotting utilities that produce time series and comparison
  charts saved into `outputs/`.

## Scenarios (what each does)

All scenarios are implemented with clear, explainable rules (no optimization):

- `price_arbitrage_global` (global price arbitrage):
  - Uses global price quartiles computed over the entire dataset (25th/75th
    percentiles) as `low` and `high` thresholds.
  - If price <= low: `pump`. If price >= high: `generate`. Otherwise `idle`.
  - This scenario represents perfect knowledge of the price distribution for
    the whole simulated period (useful as an upper-bound benchmark).

- `rolling_24h_price_arbitrage` (limited foresight / day-ahead-like):
  - At each simulation hour `t`, the strategy looks at prices from hour `t`
    through `t+24` (or remaining hours near the dataset end) and computes
    local 25th/75th percentiles as `low`/`high` thresholds.
  - Decisions at time `t` use those local thresholds; thresholds are recorded
    for every hour and can be plotted.
  - This models limited day-ahead foresight and is more realistic than
    global quartiles.

- `import_reduction` (minimize import dependency):
  - **Pump** when exports > 2500 MW AND production > load.
  - **Generate** when imports > 5000 MW AND load > production.
  - **Rationale**: Targets high-import hours (indicating grid stress) and
    reduces reliance on foreign electricity during deficits. Uses a high
    import threshold (5000 MW) to focus on critical moments.

- `surplus_absorption` (capture and store excess production):
  - **Pump** when production surplus > 1500 MW AND exports > 0.
  - **Generate** when load > production AND imports > 4000 MW.
  - **Rationale**: Aggressively absorbs renewable or production surpluses
    before they are exported. Prevents curtailment and grid congestion by
    storing excess energy. Uses a moderate surplus threshold (1500 MW).

- `renewable_balancing` (smooth variability with hysteresis):
  - **Pump** when net_balance (production - load) > 500 MW.
  - **Generate** only when net_balance < -1000 MW AND imports > 0.
  - **Rationale**: Uses asymmetric thresholds (hysteresis) to reduce churn
    and smoothing oscillations. Acts as a buffer for hour-to-hour renewable
    variability, pumping at modest surplus but requiring significant deficit
    to generate. Mimics inertial/mechanical behavior.

The strategies are implemented as Python functions in `src/strategy.py` and
are intentionally simple so they are transparent and easy to describe in a
report or lecture.

## Hourly outputs recorded (columns in `simulation_results.csv`)

Each scenario writes hourly results with the following columns (not all
columns are mandatory in your input CSVs; missing optional inputs default to
zeros):

- `datetime`, `price_EUR_per_MWh`
- `load_MW`, `production_MW`, `import_MW`, `export_MW`
- `net_balance_MW`, `deficit_MW`, `surplus_MW`
- `action` (`pump`/`generate`/`idle`)
- `pump_MWh`, `generation_MWh`, `storage_MWh`
- `cost_EUR`, `revenue_EUR`, `profit_EUR`
- `deficit_after_storage_MW`, `surplus_after_storage_MW`
- `import_reduction_MWh`, `surplus_absorbed_MWh`
- `low_threshold`, `high_threshold` (thresholds used by price-based strategies)
- `scenario` (scenario name)

These outputs are stored for every hour and are suitable for plotting and
post-processing.

## Aggregated metrics (columns in `metrics_summary.csv`)

For each scenario the following aggregated metrics are computed and saved to
`outputs/metrics_summary.csv`:

- `total_revenue_EUR`, `total_cost_EUR`, `total_profit_EUR` (economic)
- `total_pumped_MWh`, `total_generated_MWh`, `roundtrip_losses_MWh`
- `pumping_hours`, `generation_hours`, `final_storage_MWh`
- `total_deficit_before_MWh`, `total_deficit_after_MWh`, `deficit_reduction_MWh`
- `total_surplus_before_MWh`, `total_surplus_after_MWh`, `surplus_absorbed_MWh`
- `import_reduction_MWh`
- `storage_cycles` (optional; computed when plant capacity provided)

`main.py` collects these per-scenario metrics into `metrics_summary.csv` and
also saves a comparison plot `outputs/scenario_comparison.png`.

## Input CSV formats and optional columns

Plant parameters (`data/plant_parameters.csv`) - required columns:

- `plant_name`, `storage_capacity_MWh`, `turbine_power_MW`, `pump_power_MW`,
  `roundtrip_efficiency`, `initial_storage_MWh`

Optional plant columns supported (keep backward compatibility):

- `pump_efficiency` (float 0-1)
- `turbine_efficiency` (float 0-1)
- `min_storage_fraction`, `max_storage_fraction` (fractions of capacity)
- `head_m`, `usable_volume_m3` — when both are provided the code computes a
  theoretical storage capacity using:  
  $$\text{storage\/MWh} = \frac{\rho g \cdot head_m \cdot usable_volume_m^3}{3.6\times10^9}$$
  where $\rho=1000\,\mathrm{kg/m^3}$ and $g=9.81\,\mathrm{m/s^2}$. This is
  used only when `storage_capacity_MWh` is missing or non-positive.

Market data (`data/hourly_market_data_sample.csv`) - required:

- `datetime`, `price_EUR_per_MWh`

Optional (recommended for grid-balancing scenarios):

- `load_MW`, `production_MW`, `import_MW`, `export_MW`

Missing optional market columns are defaulted to `0.0` by `src/data_loader.py`.

Datetime parsing: the loader uses pandas `to_datetime(..., errors='coerce')`
and will raise a `ValueError` if any datetimes cannot be parsed.

## Design assumptions and limitations

- The simulation is hourly and deterministic.
- Strategies are rule-based; there is no optimization or commitment model.
- Grid-balancing strategies (`import_reduction`, `surplus_absorption`,
  `renewable_balancing`) are calibrated on Swiss 2025 patterns: ~3500 MW
  median imports, ~3300 MW median exports, ~57% deficit hours, ~43% surplus
  hours. Thresholds may need adjustment for other datasets or seasons.
- Prices are assumed known for the forecast window in the rolling strategy
  (limited foresight). The global quartile strategy is an upper-bound
  benchmark because it uses full-period statistics.
- Reservoir inflows, ramping constraints, start-up costs, and detailed grid
  flows are not modeled. Import/export interaction is an approximate proxy.

## Outputs produced (files)

- `outputs/<scenario>/simulation_results.csv` — hourly results for scenario
- `outputs/<scenario>/*.png` — plots per scenario (prices, storage, actions,
  cumulative profit, monthly energy, etc.)
- `outputs/metrics_summary.csv` — table with one row per scenario
- `outputs/scenario_comparison.png` — bar chart comparing key metrics

## How to extend

- Add a new strategy function in `src/strategy.py` and add it to
  `SCENARIO_STRATEGIES` with a descriptive key.
- If you need optimization-based dispatch, implement a separate solver that
  reads the hourly `market_data` and plant model and returns an action series
  compatible with the simulation runner.

## Reproducibility and tests

Unit tests are in `tests/test_simulation.py`. Run them with:

```bash
pytest -q
```

## Contact / Notes

This project is structured for teaching and iterative development. If you
want, I can add a short `SCENARIOS.md` with diagrams or expand the plots to
include stacked contributions to imported energy.
