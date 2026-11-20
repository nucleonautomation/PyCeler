# Monte Carlo option-payoff workload with ordered random draws.

import time
import math
import random

start = time.perf_counter()

random.seed(42)

SIMULATIONS = 2_000_000
STEPS = 100

S0 = 100.0
STRIKE = 105.0
RATE = 0.05
VOLATILITY = 0.2
DT = 1.0 / STEPS

discount = math.exp(-RATE)

total_payoff = 0.0
total_squared = 0.0

for simulation in range(SIMULATIONS):

    price = S0

    for step in range(STEPS):

        z = random.gauss(0.0, 1.0)

        price *= math.exp(
            (RATE - 0.5*VOLATILITY*VOLATILITY)*DT
            + VOLATILITY*math.sqrt(DT)*z
        )

    payoff = max(price-STRIKE, 0.0)

    total_payoff += payoff
    total_squared += payoff*payoff

mean = total_payoff / SIMULATIONS
variance = (
    total_squared / SIMULATIONS - mean*mean
)

option_price = discount * mean

print("Option price:", option_price)
print("Variance:", variance)
print("Checksum:", total_payoff)
print("Time:", time.perf_counter()-start)
