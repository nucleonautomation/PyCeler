# Preserved numerical simulation used for generalization checks.

import math
import random
import time


def numerical_simulation(n, iterations):
    random.seed(42)

    # Generate input data
    data = [
        random.random() * 100.0
        for _ in range(n)
    ]

    results = [0.0] * n

    for step in range(iterations):

        for i in range(1, n - 1):

            x = data[i]
            left = data[i - 1]
            right = data[i + 1]

            value = 0.0

            for j in range(100):

                a = math.sin(x * 0.001 + j)
                b = math.cos(left * 0.002 - j)
                c = math.sqrt(abs(right - x) + 1.0)

                value += (a * b + c) / (j + 1.0)

                if value > 100.0:
                    value *= 0.5

                elif value < -100.0:
                    value *= -0.25

            results[i] = value

        # Update simulation state
        for i in range(1, n - 1):
            data[i] = (
                results[i] * 0.5
                + data[i - 1] * 0.25
                + data[i + 1] * 0.25
            )

    return sum(results)


if __name__ == "__main__":

    N = 20000
    ITERATIONS = 20

    start = time.perf_counter()

    result = numerical_simulation(N, ITERATIONS)

    elapsed = time.perf_counter() - start

    print("Result:", result)
    print("Execution time:", elapsed)
