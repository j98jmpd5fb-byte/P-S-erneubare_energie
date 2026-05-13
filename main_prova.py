
def liter_per_min_to_cubic_m3_per_sec(lpm): 
    return lpm / 1000 / 60

def potential_energy(volume_m3,head_m,gravity=9.81):
    density_water = 1000  # kg/m^3
    mass = density_water * volume_m3  # mass in kg
    potential_energy_joules = mass * gravity * head_m  # potential energy in joules
    return potential_energy_joules

def joule_to_kwh(joules):
    return joules / 3.6e6


def main():
    pass