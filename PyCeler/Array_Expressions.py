from .Buffer_Indices import _Buffer_Offset
from .Common_Calls import _Helper_Substitute, _Helper_Emit
# Emit ndarray scalar operations while tracking the dtype of every intermediate and selected operand.
def _Array_Tag(Node):
    Kind = Node[0]
    if Kind == 'native_value':
        return Node[2]
    if Kind == 'literal':
        return '5' if type(Node[1]) is bool else '4' if type(Node[1]) is int else '0'
    if Kind in ('checked_integer', 'integer_negative', 'array_cast_int', 'array_floor_divide', 'array_index', 'dimension', 'dimension_path', 'array_dimension'):
        return '4'
    if Kind == 'helper':
        return _Array_Tag(_Helper_Substitute(Node[3], Node[1], Node[2]))
    if Kind == 'local':
        return f'Scalar_Kinds[{Node[1]}]'
    if Kind == 'array_buffer':
        return f'Buffer_Kinds[{Node[1]}]'
    if Kind == 'array_arithmetic':
        Left, Right = _Array_Tag(Node[2]), _Array_Tag(Node[3])
        return f'(2 if {Left} == 2 or {Right} == 2 else 1 if {Left} == 1 or {Right} == 1 else 0)'
    if Kind in ('array_negative', 'absolute', 'array_power'):
        return _Array_Tag(Node[1])
    return '0'

def _Array_Emitted_Tag(Node, Value):
    if Node[0] in ('array_helper', 'array_conditional', 'array_arithmetic', 'array_negative', 'array_absolute', 'array_power', 'array_compare', 'array_min', 'array_max'):
        return 'K' + Value[1:]
    return _Array_Tag(Node)
# Evaluate operands in Python order and carry the selected value tag through conditional expressions.
def _Array_Emit(Node, Lines, Variables, Functions, Prefix, Emit):
    Kind = Node[0]
    if Kind == 'array_dimension':
        return f'Shapes[{Node[1]}][{Node[2]}]'
    Target = 'T' + str(len(Variables))
    Variables.append(Target)
    if Kind in ('array_helper', 'array_conditional', 'array_arithmetic', 'array_negative', 'array_absolute', 'array_power', 'array_compare', 'array_min', 'array_max'):
        Tag_Target = 'K' + Target[1:]
        Variables.append(Tag_Target)
    if Kind == 'array_helper':
        Value, Tag = _Helper_Emit(Node, Lines, Variables, Functions, Prefix, Emit, _Array_Emitted_Tag, True)
        Lines.extend([f'    {Target} = {Value}', f'    {Tag_Target} = {Tag}'])
    elif Kind == 'array_conditional':
        Test = Emit(Node[1], Lines, Variables, Functions, Prefix)
        Lines.append(f'    if {Test}:')
        for Keyword, Branch in ((None, Node[2]), ('else:', Node[3])):
            if Keyword:
                Lines.append('    ' + Keyword)
            Work = []
            Value = Emit(Branch, Work, Variables, Functions, Prefix)
            Lines.extend('    ' + Line for Line in Work)
            Lines.extend([f'        {Target} = {Value}', f'        {Tag_Target} = {_Array_Emitted_Tag(Branch, Value)}'])
    elif Kind == 'array_index':
        Value = Emit(Node[1], Lines, Variables, Functions, Prefix)
        Tag = _Array_Emitted_Tag(Node[1], Value)
        Lines.extend([f'    if not ({Tag} == 4 or 10 <= {Tag} < 30):', '        Valid[0] = False', '        return 0.0', f'    {Target} = {Value}'])
    elif Kind == 'array_power':
        Value = Emit(Node[1], Lines, Variables, Functions, Prefix)
        Exponent = 'T' + str(len(Variables))
        Variables.append(Exponent)
        Lines.extend([f'    {Tag_Target} = {_Array_Emitted_Tag(Node[1], Value)}', f'    if {Tag_Target} > 2:', '        Valid[0] = False', '        return 0.0', f'    {Exponent} = {Node[2]}', f'    if {Tag_Target} == 1:', f'        {Target} = {Prefix}Array_Power_Float(<float>{Value}, <float>{Exponent})', '    else:', f'        {Target} = {Prefix}Array_Power_Double({Value}, {Exponent})', f'    if not {Prefix}Finite({Target}):', '        Valid[0] = False', '        return 0.0'])
    elif Kind == 'array_random':
        Lines.extend(['    if Random_Values == NULL or Random_Position < 0 or Random_Position >= Random_Limit:', '        Valid[0] = False', '        return 0.0', f'    {Target} = Random_Values[Random_Position]', '    Random_Position += 1', '    Random_Consumed[0] = Random_Position'])
    elif Kind in ('array_cast_float', 'array_cast_int'):
        Value = Emit(Node[1], Lines, Variables, Functions, Prefix)
        if Kind == 'array_cast_int':
            Lines.extend([f'    if not {Prefix}Finite({Value}) or {Value} < -1125899906842624.0 or {Value} > 1125899906842624.0:', '        Valid[0] = False', '        return 0.0'])
        Lines.append(f'    {Target} = ' + (f'<long long>{Value}' if Kind == 'array_cast_int' else Value))
    elif Kind in ('array_min', 'array_max'):
        Values = [(Emit(Value, Lines, Variables, Functions, Prefix), Value) for Value in Node[1:]]  # Evaluate every argument before selecting a winner, as a Python function call does.
        First, First_Node = Values[0]
        Lines.extend([f'    {Target} = {First}', f'    {Tag_Target} = {_Array_Emitted_Tag(First_Node, First)}'])
        Operator = '<' if Kind == 'array_min' else '>'  # Strict comparison keeps the first operand on ties, including signed zero.
        for Value, Value_Node in Values[1:]:
            Tag = _Array_Emitted_Tag(Value_Node, Value)
            Promotion = f'{Prefix}Scalar_Promote({Tag_Target}, {Tag}, False)'  # Comparison promotion may differ from the dtype of the operand returned by min/max.
            Test = f'(<float>{Value} {Operator} <float>{Target}) if {Promotion} == 1 else ({Value} {Operator} {Target})'
            Lines.extend([f'    if {Test}:', f'        {Target} = {Value}', f'        {Tag_Target} = {Tag}'])
    elif Kind == 'array_floor_divide':
        Left, Right = Emit(Node[1], Lines, Variables, Functions, Prefix), Emit(Node[2], Lines, Variables, Functions, Prefix)
        Left_Tag, Right_Tag = _Array_Emitted_Tag(Node[1], Left), _Array_Emitted_Tag(Node[2], Right)
        Lines.extend([f'    if {Left_Tag} not in (4, 5) or {Right_Tag} not in (4, 5) or {Right} == 0.0:', '        Valid[0] = False', '        return 0.0', f'    {Target} = (<long long>{Left}) / (<long long>{Right})', f'    if (({Left} < 0.0) != ({Right} < 0.0)) and (<long long>{Left}) % (<long long>{Right}) != 0:', f'        {Target} -= 1.0'])
    elif Kind == 'array_buffer':
        Coordinates = [Emit(Value, Lines, Variables, Functions, Prefix) for Value in Node[2]]
        Offset = _Buffer_Offset(Node[1], Coordinates, Lines)
        Lines.append(f'    {Target} = Buffers[{Node[1]}][{Offset}]')
    elif Kind in ('array_negative', 'array_absolute'):
        Value = Emit(Node[1], Lines, Variables, Functions, Prefix)
        Expression = f'-{Value}' if Kind == 'array_negative' else f'{Prefix}fabs({Value})'
        Lines.extend([f'    {Target} = {Expression}', f'    {Tag_Target} = {_Array_Emitted_Tag(Node[1], Value)}'])
        Lines.extend([f'    if {Tag_Target} >= 10 or {Tag_Target} == 4:', f'        if not {Prefix}Scalar_Integer_Valid({Target}, {Tag_Target}):', '            Valid[0] = False', '            return 0.0', f'        if {Target} == 0.0:', f'            {Target} = 0.0'])
        if Kind == 'array_negative':
            Lines.extend([f'    if {Tag_Target} == 3:', '        Valid[0] = False', '        return 0.0'])
    else:
        Left = Emit(Node[2], Lines, Variables, Functions, Prefix)
        Right = Emit(Node[3], Lines, Variables, Functions, Prefix)
        Left_Tag, Right_Tag = _Array_Emitted_Tag(Node[2], Left), _Array_Emitted_Tag(Node[3], Right)
        Tag = f'{Prefix}Scalar_Promote({Left_Tag}, {Right_Tag}, {Node[1] == "/"!r})'
        Left_Saved, Right_Saved = 'T' + str(len(Variables)), 'T' + str(len(Variables) + 1)
        Variables.extend((Left_Saved, Right_Saved))
        Lines.extend([f'    {Left_Saved} = {Left}', f'    {Right_Saved} = {Right}'])
        Left, Right = Left_Saved, Right_Saved
        if Kind == 'array_compare':
            Lines.extend([f'    if {Tag} == 1:', f'        {Target} = 1.0 if <float>{Left} {Node[1]} <float>{Right} else 0.0', '    else:', f'        {Target} = 1.0 if {Left} {Node[1]} {Right} else 0.0', f'    {Tag_Target} = 3 if ({Left_Tag} not in (0, 4, 5) or {Right_Tag} not in (0, 4, 5)) else 5'])
            return Target
        Lines.append(f'    {Tag_Target} = {Tag}')
        Lines.extend([f'    if {Tag_Target} == 255:', '        Valid[0] = False', '        return 0.0'])
        if Node[1] != '/':
            Lines.extend([f'    if ({Left_Tag} >= 10 and {Right_Tag} == 4 and not {Prefix}Scalar_Integer_Valid({Right}, {Left_Tag})) or ({Right_Tag} >= 10 and {Left_Tag} == 4 and not {Prefix}Scalar_Integer_Valid({Left}, {Right_Tag})):', '        Valid[0] = False', '        return 0.0'])
        if Node[1] == '/':
            Lines.extend([f'    if {Right} == 0.0 or ({Tag} == 1 and <float>{Right} == 0.0):', '        Valid[0] = False', '        return 0.0'])
        Lines.extend([f'    if {Tag_Target} == 1:', f'        {Target} = <float>(<float>{Left} {Node[1]} <float>{Right})', '    else:', f'        {Target} = {Left} {Node[1]} {Right}', f'    if not {Prefix}Finite({Target}):', '        Valid[0] = False', '        return 0.0'])
        Lines.extend([f'    if {Tag_Target} >= 10 or {Tag_Target} == 4:', f'        if not {Prefix}Scalar_Integer_Valid({Target}, {Tag_Target}):', '            Valid[0] = False', '            return 0.0', f'        if {Target} == 0.0:', f'            {Target} = 0.0'])
    return Target
