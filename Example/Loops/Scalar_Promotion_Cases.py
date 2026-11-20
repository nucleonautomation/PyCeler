# Focused scalar promotion cases workload; ordinary Python inputs include supported and retained cases.
def Source():  # Test support/workload for mixed scalar types and NumPy promotion.
    Cases = {
        'Direct': 'Output[I] = Source[I] * Factor + 0.125',
        'Aliased': 'Value = Source[I] * 0.5\nOutput[I] = Value * Factor + 0.125',
        'Literal': 'Output[I] = Source[I] + Factor * 0.5',
        'Integer_First': 'Output[I] = Source[I] + Factor * Factor',
        'Math_Sibling': 'Output[I] = math.sin(Source[I]) * Factor + 0.125',
        'Math_Argument': 'Output[I] = Source[I] + math.sin(Factor)',
    }
    Parts = ['import math\n']
    for Kind in ('List', 'Array'):
        for Name, Body in Cases.items():
            Annotation = ': "numpy.ndarray"' if Kind == 'Array' else ''
            Parts.append(f'def {Name}_{Kind}(Source{Annotation}, Output{Annotation}, Factor, N):\n    for I in range(N):\n' + '\n'.join('        ' + Line for Line in Body.splitlines()) + '\n    return Output\n')
    return '\n'.join(Parts)
