def _Region_Guards(Source, Region):  # Translate region requirements into guard explanations used by analysis and dispatch reports.
    Lines, Conditions = [], []
    Number = 0
    for Line in Source.splitlines():
        Text = Line.lstrip()
        Depth = len(Line) - len(Text)
        while Conditions and Conditions[-1][0] >= Depth:
            Conditions.pop()
        if Text.startswith(('if ', 'elif ', 'except ')) and Text.endswith(':'):
            Conditions.append((Depth, Text[:-1]))
        if Text == 'return None':
            Number += 1
            Reason = f'guard_{Number}: ' + (Conditions[-1][1] if Conditions else 'native attempt declined')
            Lines.append(Line[:Depth] + f'_Pyceler_Guard_Event({str(Region)!r}, {Reason!r})')
        Lines.append(Line)
    return '\n'.join(Lines) + '\n'
