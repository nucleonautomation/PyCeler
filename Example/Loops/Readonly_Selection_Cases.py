# Focused readonly selection cases workload; ordinary Python inputs include supported and retained cases.
def Source():
    Steps = ['Value = math.sin(First[Index]) + math.cos(Second[Index])'] + ['Value = math.sin(Value + 0.125)' for Index in range(16)] + ['Output[Index] = Value']
    return 'import math\ndef Transform(First, Second, Output):\n    for Index in range(len(First)):\n' + '\n'.join('        ' + Step for Step in Steps) + '\n    return Output\n'
# Test support/workload for shared read-only storage and selection holdouts.
def Cases():
    import numpy as Numpy
    for Size in (1024, 4096, 16384):
        for Storage in ('list', 'float32', 'float64'):
            First = [0.25] * Size if Storage == 'list' else Numpy.full(Size, 0.25, dtype=Storage)
            Output = [0.0] * Size if Storage == 'list' else Numpy.zeros_like(First)
            yield dict(Args=(First, First, Output), Label=Storage + '_' + str(Size), Holdout=Size == 16384)
