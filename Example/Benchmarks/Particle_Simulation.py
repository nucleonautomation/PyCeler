# Preserved particle simulation used for generalization checks.

import math
import random
import time


def particle_simulation(n, steps):

    random.seed(123)

    x = [random.uniform(-100, 100) for _ in range(n)]
    y = [random.uniform(-100, 100) for _ in range(n)]
    vx = [random.uniform(-1, 1) for _ in range(n)]
    vy = [random.uniform(-1, 1) for _ in range(n)]

    ax = [0.0] * n
    ay = [0.0] * n

    for step in range(steps):

        # Calculate particle interactions
        for i in range(n):

            fx = 0.0
            fy = 0.0

            for j in range(n):

                if i == j:
                    continue

                dx = x[j] - x[i]
                dy = y[j] - y[i]

                distance_sq = dx * dx + dy * dy + 0.01

                inv_dist = 1.0 / math.sqrt(distance_sq)
                force = inv_dist * inv_dist * inv_dist

                fx += dx * force
                fy += dy * force

            ax[i] = fx
            ay[i] = fy

        # Update particle velocities and positions
        for i in range(n):

            vx[i] += ax[i] * 0.001
            vy[i] += ay[i] * 0.001

            x[i] += vx[i] * 0.01
            y[i] += vy[i] * 0.01

    return sum(x) + sum(y)


if __name__ == "__main__":

    N = 1000
    STEPS = 10

    start = time.perf_counter()

    result = particle_simulation(N, STEPS)

    print("Result:", result)
    print("Time:", time.perf_counter() - start)
