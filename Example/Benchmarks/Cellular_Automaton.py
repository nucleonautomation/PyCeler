# Repeated cellular automaton generations on a nested list grid.

import time
import random

start = time.perf_counter()

WIDTH = 800
HEIGHT = 800
GENERATIONS = 250

random.seed(42)

grid = [
    [random.randint(0, 1) for _ in range(WIDTH)]
    for _ in range(HEIGHT)
]

for generation in range(GENERATIONS):

    new_grid = [
        [0] * WIDTH
        for _ in range(HEIGHT)
    ]

    for y in range(1, HEIGHT-1):
        for x in range(1, WIDTH-1):

            neighbors = (
                grid[y-1][x-1] +
                grid[y-1][x] +
                grid[y-1][x+1] +
                grid[y][x-1] +
                grid[y][x+1] +
                grid[y+1][x-1] +
                grid[y+1][x] +
                grid[y+1][x+1]
            )

            alive = grid[y][x]

            if alive:
                if neighbors == 2 or neighbors == 3:
                    new_grid[y][x] = 1
            else:
                if neighbors == 3:
                    new_grid[y][x] = 1

    grid = new_grid

checksum = sum(sum(row) for row in grid)

print("Checksum:", checksum)
print("Time:", time.perf_counter()-start)
