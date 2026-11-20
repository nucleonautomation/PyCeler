# Three-dimensional list-grid diffusion at the original benchmark size.

import time
import math

start = time.perf_counter()

NX = 120
NY = 120
NZ = 100
STEPS = 120

ALPHA = 0.12

grid = [[[0.0 for _ in range(NZ)]
         for _ in range(NY)]
        for _ in range(NX)]

# Initial heat source
for x in range(NX):
    for y in range(NY):
        for z in range(NZ):
            dx = x - NX / 2
            dy = y - NY / 2
            dz = z - NZ / 2

            grid[x][y][z] = math.exp(
                -(dx*dx + dy*dy + dz*dz) / 500
            )

for step in range(STEPS):

    new_grid = [[[0.0 for _ in range(NZ)]
                 for _ in range(NY)]
                for _ in range(NX)]

    for x in range(1, NX-1):
        for y in range(1, NY-1):
            for z in range(1, NZ-1):

                center = grid[x][y][z]

                laplacian = (
                    grid[x+1][y][z] +
                    grid[x-1][y][z] +
                    grid[x][y+1][z] +
                    grid[x][y-1][z] +
                    grid[x][y][z+1] +
                    grid[x][y][z-1] -
                    6.0 * center
                )

                new_grid[x][y][z] = (
                    center + ALPHA * laplacian
                )

    grid = new_grid

checksum = sum(
    grid[x][y][z]
    for x in range(NX)
    for y in range(NY)
    for z in range(NZ)
)

print("Checksum:", checksum)
print("Time:", time.perf_counter() - start)
