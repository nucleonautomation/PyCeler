def Source():  # Test support/workload for affine offsets and overlapping storage.
    Cases = {
        'Direct': 'Output[2 * I + 1] = Source[I] * 0.75',
        'Alias': 'J = 2 * I + 1\nOutput[J] = Source[I] * 0.75',
        'Chained': 'J = 2 * I\nK = J + 1\nOutput[K] = Source[I] * 0.75',
        'Dependent': 'J = 2 * I + 1\nOutput[J] = Output[J - 2] * 0.5 + Source[I]',
        'Reassigned': 'J = 2 * I + 1\nJ = N - J\nOutput[J] = Source[I] * 0.75',
        'Branched': 'J = 2 * I + 1\nif I > 4:\n    J = N - J\nOutput[J] = Source[I] * 0.75',
        'Rebound_Outer': 'J = 2 * I + 1\nI = I - 1\nOutput[J] = Source[I] * 0.75',
    }
    Parts = []
    for Kind in ('List', 'Array'):
        for Name, Body in Cases.items():
            Annotation = ': "numpy.ndarray"' if Kind == 'Array' else ''
            Parts.append(f'def {Name}_{Kind}(Source{Annotation}, Output{Annotation}, N):\n    for I in range(1, N):\n' + '\n'.join('        ' + Line for Line in Body.splitlines()) + '\n    return Output\n')
    return '\n'.join(Parts)
