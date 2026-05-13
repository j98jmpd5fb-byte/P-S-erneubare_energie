import math


class HydroPlant:
    """A simple pumped-storage plant represented as a lossy energy store.

    The storage value is measured as electric energy that can later be sold
    through the turbines. Pumping buys electricity from the market and stores
    only part of it because the full pump-turbine cycle has losses.
    """

    def __init__(
        self,
        name,
        storage_capacity_MWh,
        turbine_power_MW,
        pump_power_MW,
        roundtrip_efficiency,
        initial_storage_MWh,
        pump_efficiency=None,
        turbine_efficiency=1.0,
        min_storage_fraction=0.0,
        max_storage_fraction=1.0,
    ):
        if not 0 < roundtrip_efficiency <= 1:
            raise ValueError("roundtrip_efficiency must be between 0 and 1.")
        if storage_capacity_MWh <= 0:
            raise ValueError("storage_capacity_MWh must be positive.")
        if turbine_power_MW < 0 or pump_power_MW < 0:
            raise ValueError("Power values cannot be negative.")
        if not 0 <= initial_storage_MWh <= storage_capacity_MWh:
            raise ValueError("Initial storage must be within plant capacity.")
        if not 0 <= min_storage_fraction < max_storage_fraction <= 1:
            raise ValueError("Storage fractions must satisfy 0 <= min < max <= 1.")

        self.name = name
        self.storage_capacity_MWh = float(storage_capacity_MWh)
        self.turbine_power_MW = float(turbine_power_MW)
        self.pump_power_MW = float(pump_power_MW)
        self.roundtrip_efficiency = float(roundtrip_efficiency)
        self.min_storage_MWh = self.storage_capacity_MWh * float(min_storage_fraction)
        self.max_storage_MWh = self.storage_capacity_MWh * float(max_storage_fraction)
        self.initial_storage_MWh = float(initial_storage_MWh)
        self.storage_MWh = float(initial_storage_MWh)

        # For a beginner model, keep turbine discharge simple and put losses
        # mostly on pumping. This still preserves round-trip efficiency.
        self.turbine_efficiency = float(turbine_efficiency)
        self.pump_efficiency = (
            float(pump_efficiency)
            if pump_efficiency is not None
            else self.roundtrip_efficiency / self.turbine_efficiency
        )

    def can_pump(self):
        return self.pump_power_MW > 0 and self.storage_MWh < self.max_storage_MWh

    def can_generate(self):
        return self.turbine_power_MW > 0 and self.storage_MWh > self.min_storage_MWh

    def pump(self, power_MW, duration_h):
        """Buy electricity and store the useful part after pumping losses.

        Returns the electricity bought from the market in MWh.
        """
        if duration_h <= 0 or not self.can_pump():
            return 0.0

        requested_power = min(float(power_MW), self.pump_power_MW)
        requested_input_MWh = max(requested_power, 0.0) * duration_h
        available_storage_MWh = self.max_storage_MWh - self.storage_MWh

        # If the reservoir is almost full, buy only enough electricity to fill it.
        input_limited_by_space = available_storage_MWh / self.pump_efficiency
        electricity_bought_MWh = min(requested_input_MWh, input_limited_by_space)
        stored_energy_MWh = electricity_bought_MWh * self.pump_efficiency

        self.storage_MWh = min(
            self.max_storage_MWh,
            self.storage_MWh + stored_energy_MWh,
        )
        return electricity_bought_MWh

    def generate(self, power_MW, duration_h):
        """Release stored water and sell electric energy through the turbines.

        Returns the electricity generated and sold in MWh.
        """
        if duration_h <= 0 or not self.can_generate():
            return 0.0

        requested_power = min(float(power_MW), self.turbine_power_MW)
        requested_generation_MWh = max(requested_power, 0.0) * duration_h
        usable_storage_MWh = self.storage_MWh - self.min_storage_MWh
        possible_generation_MWh = usable_storage_MWh * self.turbine_efficiency
        generation_MWh = min(requested_generation_MWh, possible_generation_MWh)

        storage_used_MWh = generation_MWh / self.turbine_efficiency
        self.storage_MWh = max(self.min_storage_MWh, self.storage_MWh - storage_used_MWh)

        if math.isclose(self.storage_MWh, self.min_storage_MWh, abs_tol=1e-9):
            self.storage_MWh = self.min_storage_MWh
        return generation_MWh
