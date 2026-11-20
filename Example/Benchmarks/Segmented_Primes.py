# Segmented prime sieve with dependent marking and checksum accumulation.

import time
import math

start = time.perf_counter()

LIMIT = 20_000_000
SEGMENT_SIZE = 100_000

root = int(math.sqrt(LIMIT))

base = [True] * (root + 1)
base_primes = []

for i in range(2, root + 1):
    if base[i]:
        base_primes.append(i)

        for j in range(i*i, root + 1, i):
            base[j] = False

total_primes = 0
prime_sum = 0

for low in range(2, LIMIT + 1, SEGMENT_SIZE):

    high = min(low + SEGMENT_SIZE, LIMIT + 1)

    segment = [True] * (high - low)

    for p in base_primes:

        start_value = max(
            p*p,
            ((low + p - 1) // p) * p
        )

        for j in range(start_value, high, p):
            segment[j - low] = False

    for i in range(len(segment)):

        if segment[i] and low + i >= 2:
            total_primes += 1
            prime_sum += low + i

print("Prime count:", total_primes)
print("Prime sum:", prime_sum)
print("Time:", time.perf_counter() - start)
