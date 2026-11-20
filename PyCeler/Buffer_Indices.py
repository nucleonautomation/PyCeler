def _Buffer_Coordinate(Slot, Axis, Coordinate, Lines, Indent='    '):
    Dimension = f'Shapes[{Slot}][{Axis}]'
    Lines.extend([f'{Indent}if {Coordinate} < -{Dimension} or {Coordinate} >= {Dimension}:', Indent + '    Valid[0] = False', Indent + '    return 0.0'])
    return f'(<Py_ssize_t>({Coordinate}) + ({Dimension} if {Coordinate} < 0.0 else 0))'
# Check every coordinate before flattening multidimensional indexing into a native buffer offset.
def _Buffer_Offset(Slot, Coordinates, Lines, Indent='    '):
    Offsets = []  # Each axis is bounds-checked independently before combining strides.
    for Axis, Coordinate in enumerate(Coordinates):
        Offset = _Buffer_Coordinate(Slot, Axis, Coordinate, Lines, Indent)
        Offsets.append(f'{Offset} * Strides[{Slot}][{Axis}]')
    return ' + '.join(Offsets)
