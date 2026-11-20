def Source():  # Test support/workload for generalization.
    Parts = ['import math\nimport numpy as np\n']
    for Name, Inner in (('Nested', 'for J in range(Depth):'), ('Nested_While', 'J = 0\nwhile J < Depth:')):
        Body = 'Value = 0.0\n' + Inner + '\n    Value += math.sqrt(abs(Source[I] - J * 0.125) + 0.25)\n'
        if Name == 'Nested_While':
            Body += '    J += 1\n'
        Body += 'Copy = Value\nOutput[I] = Value\nOther[I] = Copy'
        Parts.append(f'def {Name}(Source, Output, Other, N, Depth):\n    for I in range(N):\n' + '\n'.join('        ' + Line for Line in Body.splitlines()) + '\n    return Output, Other\n')
    Parts.append('def Repeated_Index(Source, Output, Other, N, Depth):\n    for Step in range(Depth):\n        for I in range(N):\n            Value = 0.0\n            for J in range(3):\n                Value += math.sin(Source[I] + J)\n            Output[I] = Value\n        for I in range(N):\n            Other[I] = Output[I] * 0.75\n    return Output, Other\n')
    Parts.append('def Conditional_Constant(Source, Output, Other, N, Depth):\n    for I in range(N):\n        Value = Source[I] * 2.0\n        if I < Depth:\n            Value = 1.25 + 2.5\n        Output[I] = Value\n        Other[I] = Value\n    return Output, Other\n')
    Parts.append('def Shared_Inner(Source, Output, Other, N, Depth):\n    for I in range(N):\n        Value = Source[I] * 2.0\n        for J in range(Depth):\n            Output[J] = Value\n            Other[J] = Value\n    return Output, Other\n')
    Parts.append('def Integer_Absolute(Source, Output, Other, N, Depth):\n    for I in range(N):\n        Value = abs(Source[I])\n        Output[I] = Value + 1\n        Other[I] = Value + 2\n    return Output, Other\n')
    Parts.append('def Interleaved(Source, Output, Other, N, Depth):\n    for I in range(N):\n        Value = math.sqrt(abs(Source[I]) + 1.0)\n        Output[2 * I] = Value\n        Output[2 * I + 1] = Value\n        Other[I] = Value\n    return Output, Other\n')
    Parts.append('def Columns(Source: "numpy.ndarray", Output: "numpy.ndarray", Other: "numpy.ndarray", N, Depth):\n    for I in range(N):\n        for J in range(Depth):\n            Output[J, I] = abs(Source[J, I]) * 0.5 + 0.125\n    return Output, Other\n')
    Parts.append('def Dependent(Source, Output, Other, N, Depth):\n    for I in range(1, N):\n        Output[I] = Output[I - 1] * 0.75 + Source[I]\n    return Output, Other\n')
    Parts.append('def Direct_Absolute(Source, Output, Other, N, Depth):\n    for I in range(N):\n        Output[I] = abs(Source[I])\n    return Output, Other\n')
    Parts.append('def Conditional_Expression(Source, Output, Other, N, Depth):\n    for I in range(N):\n        Value = Source[I] * 2.0\n        Value = 1.25 + 2.5 if I < Depth else 1.5 + 2.25\n        Output[I] = Value\n        Other[I] = Value\n    return Output, Other\n')
    for Array in (False, True):
        Annotation = ': "numpy.ndarray"' if Array else ''
        Header = f'def Many_Slots_{"Array" if Array else "List"}(Source{Annotation}, Output{Annotation}, Other{Annotation}, N, Depth):\n    for I in range(N):\n'
        Lines = ['Value_0 = Source[I] * 0.75'] + [f'Value_{Index} = Value_{Index - 1} + 0.001' for Index in range(1, 72)] + ['Output[I] = Value_71']
        Parts.append(Header + '\n'.join('        ' + Line for Line in Lines) + '\n    return Output, Other\n')
    Names = [f'Input_{Index}' for Index in range(11)]
    Parts.append('def Many_Buffers(' + ', '.join(Names) + ', Output, N):\n    for I in range(N):\n        Output[I] = ' + ' + '.join(Name + '[I]' for Name in Names) + '\n    return Output\n')
    return '\n'.join(Parts)
