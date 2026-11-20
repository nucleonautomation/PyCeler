# Focused iterator selection cases workload; ordinary Python inputs include supported and retained cases.
def Cases():  # Test support/workload for iterator construction, target bindings and strict mismatch.
    import numpy as N
    for Size in (2048, 8192):
        for Storage in ('list', 'float32', 'float64'):
            Source = N.full(Size, 0.25, dtype='float64' if Storage == 'list' else Storage)
            Output = N.zeros_like(Source)
            if Storage == 'list':
                Source, Output = Source.tolist(), Output.tolist()
            yield dict(Args=(Output, Source), Label=Storage + str(Size), Holdout=Size == 8192)
