# Repeated list-grid updates with separate current and next state.

import time
import math

start = time.perf_counter()

SIZE = 200
ITERATIONS = 300

# Initialize simulation grid
grid = [
    [math.sin(i * 0.01) * math.cos(j * 0.01)
     for j in range(SIZE)]
    for i in range(SIZE)
]

next_grid = [
    [0.0 for j in range(SIZE)]
    for i in range(SIZE)
]

for iteration in range(ITERATIONS):

    # Update interior grid cells
    for i in range(1, SIZE - 1):
        for j in range(1, SIZE - 1):

            center = grid[i][j]
            top = grid[i - 1][j]
            bottom = grid[i + 1][j]
            left = grid[i][j - 1]
            right = grid[i][j + 1]

            # Heat diffusion calculation
            next_grid[i][j] = (
                center * 0.5
                + top * 0.125
                + bottom * 0.125
                + left * 0.125
                + right * 0.125
            )

    grid, next_grid = next_grid, grid

# Calculate final energy and checksum
total_energy = 0.0
checksum = 0

for i in range(SIZE):
    for j in range(SIZE):
        value = grid[i][j]

        total_energy += value * value

        checksum += int(abs(value) * 1000000) % 100003

elapsed = time.perf_counter() - start

print("Heat diffusion completed!")
print(f"Iterations: {ITERATIONS}")
print(f"Grid size: {SIZE} x {SIZE}")
print(f"Total energy: {total_energy:.12f}")
print(f"Checksum: {checksum}")
print(f"Time: {elapsed:.3f}s")
print(f"Cell updates: {(SIZE - 2) * (SIZE - 2) * ITERATIONS:,}")
print(
    f"Updates/sec: "
    f"{(SIZE - 2) * (SIZE - 2) * ITERATIONS / elapsed:,.0f}"
)
