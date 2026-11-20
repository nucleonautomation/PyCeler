# Ordinary triple-loop list matrix multiplication.

import time
import random

start = time.perf_counter()

N = 350

random.seed(42)

A = [
    [random.random() for _ in range(N)]
    for _ in range(N)
]

B = [
    [random.random() for _ in range(N)]
    for _ in range(N)
]

C = [
    [0.0 for _ in range(N)]
    for _ in range(N)
]

for i in range(N):
    for k in range(N):

        aik = A[i][k]

        for j in range(N):
            C[i][j] += aik * B[k][j]

checksum = sum(
    C[i][j]
    for i in range(N)
    for j in range(N)
)

print("Checksum:", checksum)
print("Time:", time.perf_counter()-start)
