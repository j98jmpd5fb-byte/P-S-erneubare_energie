# Pumped-Storage Hydropower Simulation for Switzerland

This student research/coding project asks whether upgrading a large Swiss
storage hydropower complex, using Grande Dixence / Cleuson-Dixence as a
hypothetical case, with additional pumped-storage capability could be
economically profitable and useful for the Swiss electricity system.

The model simulates a simple day-ahead operating rule: for each day, pair
cheap pumping hours with expensive generation hours, and only operate when the
price spread is large enough to cover round-trip losses.

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
- It uses a simple day-ahead strategy, not advanced linear programming.
- It ignores detailed grid constraints and water inflows.
- The next day's hourly prices are assumed to be known when scheduling
  pumping and generation.
- Pumping/generation pairs are skipped if the day-ahead spread does not cover
  round-trip efficiency losses.
- Pumping and generation are limited by plant power ratings.
- Storage is kept between configured minimum and maximum operating levels.
- Round-trip efficiency is set in `data/plant_parameters.csv`.
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

The optional columns `min_storage_fraction` and `max_storage_fraction` define
operating storage limits as fractions of total storage capacity.

Keep units consistent. Prices are EUR/MWh, power is MW, hourly energy is MWh.

## Limitations

This first model is intentionally simple. It does not include reservoir inflows,
seasonal water constraints, balancing markets, taxes, grid tariffs, investment
costs, start-up limits, ramping limits, or detailed Swiss transmission
constraints. It is a clear base for later extensions, such as optimization,
real historical data, scenarios for Netto Null electricity demand, and
investment payback analysis.
