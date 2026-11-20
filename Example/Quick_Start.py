# A small runnable example: no PyCeler decorators, type annotations or Cython declarations.
import math
import time
import numpy as np

def transform(values, output):
    # Rows write disjoint output cells; the converter can consider OpenMP workers.
    for row in range(len(values)):
        for column in range(len(values[0])):
            value = values[row, column]
            output[row, column] = math.sin(value) + math.sqrt(value + 1.0)
    return output

values = np.linspace(0.0, 10.0, 256 * 128).reshape(256, 128)
output = np.zeros_like(values)
started = time.perf_counter()
transform(values, output)
print("Checksum:", float(output.sum()))
print("Runtime:", time.perf_counter() - started)
