# Focused random bound cases workload; ordinary Python inputs include supported and retained cases.
import numpy as Numpy
# Test support/workload for random bound.
def Cases():
    for Width, Holdout in ((1024, False), (4096, False), (8192, False), (16384, True)):
        yield dict(Args=(Numpy.zeros((8, Width)), 0, Width), Label='random-width-' + str(Width), Holdout=Holdout)
