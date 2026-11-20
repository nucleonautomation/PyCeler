def Cases():
    import numpy as N
    for Size in (2048, 8192):
        for Kind in ('list', 'float32', 'float64'):
            Source = N.full(Size, 0.25, dtype='float64' if Kind == 'list' else Kind)
            Output = N.zeros_like(Source)
            if Kind == 'list':
                Source, Output = Source.tolist(), Output.tolist()
            yield dict(Args=(Source, Output, -7), Holdout=Size == 8192)
# Test support/workload for iterator construction, target bindings and strict mismatch.
def Helpers():
    for Case in Cases():
        yield dict(Args=Case['Args'][:2], Holdout=Case['Holdout'])
