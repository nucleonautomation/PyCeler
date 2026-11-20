# Focused storage composition cases workload; ordinary Python inputs include supported and retained cases.
def Source():
    Body = ['Value = Source[Index] * 0.75'] + [f'Value = Value + {Number}.125' for Number in range(12)] + ['Output[Index] = Value']
    Loop = '    for Index in range(N):\n' + '\n'.join('        ' + Line for Line in Body) + '\n'
    return 'def Transform(Source, Output, N):\n' + Loop + '    return Output\n\ndef Extracted(Source, Output, N):\n    Marker = N + 2\n' + Loop + '    return Output, Marker\n\ndef Whole(Source, Output):\n    for Index in range(len(Source)):\n        Output[Index] = Source[Index] * 2\n    return Output\n'
# Test support/workload for competing list/array backends and runtime storage kinds.
def Cases():
    import numpy as Numpy
    for Kind in (float, int):
        Size = 4096
        yield dict(Args=(Size, [0.0] * Size, [Kind(Index % 9 + 1) for Index in range(Size)]), Label='list_' + Kind.__name__, Holdout=True)
    for Kind in (Numpy.float32, Numpy.float64, Numpy.int32, Numpy.int64):
        Source = (Numpy.arange(4096) % 9 + 1).astype(Kind)
        yield dict(Args=(len(Source), Numpy.zeros_like(Source), Source), Label=Numpy.dtype(Kind).str, Holdout=True)
