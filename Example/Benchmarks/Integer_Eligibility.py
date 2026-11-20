# Preserved integer eligibility reproduction with the original workload size.

import time
import math

start = time.perf_counter()

SIZE = 3000
LIMIT = 1000

total = 0
checksum = 0

for i in range(SIZE):
    row_total = 0

    for j in range(SIZE):
        # Integer-heavy computation
        x = (i * 7919 + j * 104729) % 1000003
        y = (i * j + x * 31) % 999983

        # Mixed arithmetic operations
        value = (x * x + y * y + i * j) % 10000019

        if value % 11 == 0:
            row_total += value * 7
        elif value % 13 == 0:
            row_total -= value * 3
        elif value % 17 == 0:
            row_total += value // 5
        else:
            row_total += (value % 997) * 2

        # Bitwise operations
        if (x ^ y) % 23 == 0:
            row_total ^= (x & y)

        # Additional conditional computation
        if row_total % 100003 == 0:
            row_total += (i << 2) ^ (j >> 1)

    checksum += row_total

    if checksum % 99991 == 0:
        total += i * 17

    total += row_total

elapsed = time.perf_counter() - start

print("Benchmark completed!")
print(f"Result: {total}")
print(f"Checksum: {checksum}")
print(f"Time: {elapsed:.2f}s")
print(f"Operations: {SIZE * SIZE:,}")
print(f"Ops/sec: {SIZE * SIZE / elapsed:,.0f}")
