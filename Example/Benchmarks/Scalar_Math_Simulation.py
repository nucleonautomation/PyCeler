# Nested scalar math simulation with ordered energy and checksum updates.

import time
import math

start = time.perf_counter()

SIZE = 2500
ITERATIONS = 80

total_energy = 0.0
global_checksum = 0

for i in range(SIZE):
    row_energy = 0.0
    row_checksum = 0

    for j in range(SIZE):
        # Initial numerical values
        x = (i * 0.001) + (j * 0.002)
        y = (j * 0.003) - (i * 0.001)

        value = 0.0

        # Iterative numerical simulation
        for k in range(ITERATIONS):
            a = math.sin(x + k * 0.0001)
            b = math.cos(y - k * 0.0002)

            x = a * 0.7 + b * 0.3
            y = b * 0.6 - a * 0.4

            value += x * x + y * y

        # Conditional floating-point operations
        if value > 20.0:
            row_energy += value * 1.5
        elif value > 10.0:
            row_energy -= value * 0.75
        elif value > 5.0:
            row_energy += value / 3.0
        else:
            row_energy += value * 0.25

        # Integer checksum calculations
        ix = int(abs(x) * 1000000)
        iy = int(abs(y) * 1000000)

        checksum = (ix * 7919 + iy * 104729) % 1000003

        if checksum % 7 == 0:
            row_checksum += checksum * 3
        elif checksum % 11 == 0:
            row_checksum -= checksum * 2
        else:
            row_checksum += checksum % 997

    total_energy += row_energy
    global_checksum += row_checksum

elapsed = time.perf_counter() - start

print("Numerical simulation completed!")
print(f"Total energy: {total_energy:.10f}")
print(f"Global checksum: {global_checksum}")
print(f"Time: {elapsed:.2f}s")
print(f"Operations: {SIZE * SIZE * ITERATIONS:,}")
print(f"Ops/sec: {SIZE * SIZE * ITERATIONS / elapsed:,.0f}")
