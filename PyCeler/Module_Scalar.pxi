cdef void _Find_Module_Scalars(object Tree, list Findings, dict Edits) except *:
    Tree.name = '_Pyceler_Module'
    Updates = {}
    Scopes = [(Tree, None)]
    for Function in Tree.body:
        if isinstance(Function, ast.FunctionDef) and not Function.decorator_list:
            Globals = {Name for Node in Function.body if isinstance(Node, ast.Global) for Name in Node.names}
            if Globals:
                Scopes.append((Function, Globals))
    for Scope, Globals in Scopes:
        Parts = []
        Pending = [Scope]
        while Pending:
            Part = Pending.pop()
            if Part is not Scope and isinstance(Part, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            Parts.append(Part)
            Pending.extend(ast.iter_child_nodes(Part))
        Available = {Part.id for Part in Parts if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Store)}
        if Globals is not None:
            Available.update(Globals)
        Counts = {}
        for Part in Parts:
            if isinstance(Part, ast.stmt):
                Counts[Part.lineno] = Counts.get(Part.lineno, 0) + 1
        Shared = {Line for Line, Count in Counts.items() if Count > 1}
        Protected = []
        for Edit in Edits.values():
            Existing = Edit[1] if Edit[3] is not None and Edit[3].get('Region', False) else Edit[2]
            if hasattr(Existing, 'lineno'):
                Protected.append((Existing.lineno, Existing.end_lineno))
        Locals = set()
        if Globals is not None:
            Arguments = Scope.args.posonlyargs + Scope.args.args + Scope.args.kwonlyargs
            Arguments += ([Scope.args.vararg] if Scope.args.vararg else []) + ([Scope.args.kwarg] if Scope.args.kwarg else [])
            Locals.update(Arg.arg for Arg in Arguments)
            Locals.update(Part.id for Part in Parts if isinstance(Part, ast.Name) and isinstance(Part.ctx, (ast.Store, ast.Del)) and Part.id not in Globals)
            Locals.update(Part.name for Part in Parts if isinstance(Part, ast.ExceptHandler) and Part.name and Part.name not in Globals)
            for Part in Parts:
                if isinstance(Part, (ast.Import, ast.ImportFrom)):
                    Locals.update(Alias.asname or Alias.name.split('.')[0] for Alias in Part.names if (Alias.asname or Alias.name.split('.')[0]) not in Globals)
        for Node in sorted((Part for Part in Parts if isinstance(Part, ast.For)), key=lambda Part: (Part.lineno, Part.col_offset)):
            if Node.lineno in Edits or any(Node.lineno <= Last and Node.end_lineno >= First for First, Last in Protected):
                continue
            if any(Node.lineno <= Line <= Node.end_lineno for Line in Shared):
                continue
            Plan = _Scalar_Region_Plan(Scope, Node, Available, '<module>' if Globals is None else Scope.name)
            if Plan is None:
                continue
            State = set(Plan['Inputs']) | set(Plan['Outputs'])
            if Globals is not None and not State <= Globals:
                continue
            Reporting = Plan['Reporting']
            if Reporting is not None and Globals is not None:
                if any(isinstance(Part, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)) or
                       isinstance(Part, ast.Name) and Part.id in Locals | {'locals', 'vars', 'eval', 'exec', '_getframe', 'currentframe'} for Part in ast.walk(Reporting)):
                    continue
            if Reporting is not None and any(isinstance(Part, (ast.Break, ast.Continue, ast.Return, ast.Yield, ast.YieldFrom, ast.Await, ast.Nonlocal)) for Part in _Rank_Parts(Reporting)):
                continue
            Plan['Kind'] = 'module_scalar'
            Plan['Module_Reduction'] = _Module_Reduction_Plan(Plan)
            Plan['Transformations'] = ('Native module arithmetic', 'Per-iteration observable-state continuation', 'Bounded ordered native spans')
            if Plan['Module_Reduction'] is not None:
                Plan['Transformations'] += ('Exact OpenMP reduction spans',)
            Parameters = tuple('_Pyceler_Argument_' + str(Position) for Position in range(len(Plan['Names'])))
            Definition = ast.parse('def _Pyceler_Probe(' + ', '.join(Parameters) + '):\n    pass').body[0]
            Prefix = [ast.Global(names=list(dict.fromkeys([*Plan['Inputs'], *Plan['Outputs']])))]
            Prefix.extend(ast.parse(Name + ' = ' + Parameters[Position + 2]).body[0] for Position, Name in enumerate(Plan['Inputs']))
            Prefix.append(ast.parse(Plan['Index'] + ' = ' + Parameters[1]).body[0])
            Candidate = copy.deepcopy(Node)
            Probe_Step = Parameters[Plan['Step_Argument']] if Plan['Step'] is None else str(Plan['Step'])
            Candidate.iter = ast.parse(f'range({Parameters[1]}, {Parameters[0]}, {Probe_Step})', mode='eval').body
            Candidate.body = copy.deepcopy(Plan['Statements'])
            Candidate.orelse = []
            Definition.body = Prefix + [Candidate, ast.parse('return (' + ', '.join(Plan['Outputs']) + ',)').body[0]]
            Plan['Probe'] = ast.fix_missing_locations(Definition)
            Edits[Node.lineno] = (Plan['Names'], Node, Scope, Plan)
            Updates[Node.lineno] = Plan
            Protected.append((Node.lineno, Node.end_lineno))
    for Position, Finding in enumerate(Findings):
        Plan = Updates.get(Finding.Line)
        if Plan is not None:
            Findings[Position] = replace(Finding, Classification='Module_Scalar_Region', Change='Guarded native module arithmetic with eligible OpenMP reduction spans',
                Reason='Checked native arithmetic publishes observable globals. Exact reductions use bounded serial/OpenMP spans only while no Python thread or custom signal observer is present; callbacks retain their original order.',
                Transformations=Plan['Transformations'], Constraints=('Checked integer or ordered floating arithmetic with Python continuation', 'Global state committed before signal checks', 'Parallel work requires an exact reduction proof'))

cdef str _Module_Scalar_Kernel(dict Plan, int Line, bint Parallel, str Filename, str Prefix, bint Measured=False, tuple Future_Features=()):
    Inputs = tuple(dict.fromkeys([*Plan['Inputs'], Plan['Index']]))
    Outputs = tuple(Name for Name in Plan['Outputs'] if Name != Plan['Index'])
    Slots = Plan['Slots']
    Floating = Plan.get('Floating', set())
    Step = f'_Pyceler_Module_Step_{Line}'
    Run = f'_Pyceler_Module_Run_{Line}'
    Pure = '\n'.join(ast.unparse(Node) for Node in Plan['Statements'])
    Reporting = Plan['Reporting']
    Fallback = copy.deepcopy(Plan['Loops'][0])
    Fallback.orelse = []
    Fallback.iter = ast.Name(id=Prefix + 'Module_Iterator', ctx=ast.Load())
    Fallback_Source = ast.unparse(ast.fix_missing_locations(Fallback))
    Template = f'_Pyceler_Module_Template_{Line}_'
    Lines = [_Module_Constant_Kernel(Line), f'import builtins as {Template}Builtins', f'import __future__ as {Template}Future', f'cdef int {Template}Flags = 0']
    Lines.extend(f'{Template}Flags |= {Template}Future.{Name}.compiler_flag' for Name in Future_Features)
    Fragments = [('Pure', Pure, 'exec'), ('Fallback', Fallback_Source, 'exec')]
    if Reporting is not None:
        Fragments.extend([('Test', ast.unparse(Reporting.test), 'eval'), ('Report', '\n'.join(ast.unparse(Node) for Node in Reporting.body), 'exec')])
    Lines.extend(f'cdef object {Template}{Name} = {Template}Builtins.compile({Source!r}, {Filename!r}, {Mode!r}, flags={Template}Flags, dont_inherit=True)' for Name, Source, Mode in Fragments)
    Lines.extend([f'cdef object {Step}(object Namespace):', '    import builtins as B', '    cdef object Value',
                  '    cdef _Pyceler_Int ' + ', '.join([*(Slot for Name, Slot in Slots.items() if Name not in Floating), *Plan.get('Temporaries', [])])])
    if Floating:
        Lines.extend(['    cdef double ' + ', '.join(Slots[Name] for Name in Floating),
                      '    if _Pyceler_Scalar_Rounding() != _Pyceler_Scalar_Nearest:', '        return None'])
    for Name in Inputs:
        Guard = 'B.type(Value) is B.int and -9223372036854775808 <= Value <= 9223372036854775807'
        if Name in Floating:
            Guard = 'B.type(Value) is B.float or (' + Guard + ')'
        Lines.extend([f'    if {Name!r} not in Namespace:', '        return None', f'    Value = Namespace[{Name!r}]',
                      f'    if not ({Guard}):', '        return None',
                      f'    {Slots[Name]} = Value'])
    Lines.append('    try:')
    Lines.extend('        ' + Text[16:] for Text in Plan['Lines'])
    Lines.extend(['    except (_Pyceler_Overflow, _Pyceler_Zero_Division):', '        return None',
                  '    return (' + ', '.join(Slots[Name] for Name in Outputs) + ',)'])
    if Reporting is not None:
        Predicate = dict(Slots={}, Lines=[], Temporaries=[])
        Test_Names = tuple(dict.fromkeys(Node.id for Node in ast.walk(Reporting.test) if isinstance(Node, ast.Name)))
        try:
            Test = _Scalar_Test(Reporting.test, set(Test_Names), Predicate)
        except _Unsupported_Scalar:
            Test = None
        Lines.extend(['', f'cdef bint _Pyceler_Module_Test_{Line}(object Namespace, object Code) except -1:', '    import builtins as B', '    cdef object Value'])
        if Test is not None:
            Lines.append('    cdef _Pyceler_Int ' + ', '.join(Predicate['Slots'].values()))
            for Name in Test_Names:
                Lines.extend([f'    if {Name!r} not in Namespace:', '        return B.eval(Code, Namespace)', f'    Value = Namespace[{Name!r}]',
                              '    if B.type(Value) is not B.int or not -9223372036854775808 <= Value <= 9223372036854775807:',
                              '        return B.eval(Code, Namespace)', f'    {Predicate["Slots"][Name]} = Value'])
            Lines.extend(['    try:', '        return ' + Test, '    except (_Pyceler_Overflow, _Pyceler_Zero_Division):', '        return B.eval(Code, Namespace)'])
        else:
            Lines.append('    return B.eval(Code, Namespace)')
    Reduction = Plan['Module_Reduction']
    if Reduction is not None:
        Lines.extend(['', _Module_Reduction_Kernel(Reduction, Line, Parallel)])
    else:
        Span_Source = _Scalar_Region_Kernel(Plan, Line).replace(f'_Pyceler_Scalar_Region_{Line}', f'_Pyceler_Module_Span_{Line}')
        Span_Source = '\n'.join(Text for Text in Span_Source.splitlines() if '_Pyceler_Poll(&Ticks)' not in Text and '_Pyceler_Region_Attempts' not in Text)
        Lines.extend(['', Span_Source])
    Lines.extend(['', f'cdef void {Run}(object Namespace, object Iterator, bint Allow_Threads, object Policy, object Source_Code) except *:', '    import builtins as B',
                  '    cdef object Result, Index, Span, Block, Arguments, Current', '    cdef unsigned long long Ticks = 0', '    cdef bint Completed', '    cdef int Mode',
                  '    global _Pyceler_Module_Native, _Pyceler_Module_Fallbacks, _Pyceler_Module_Team',
                  f'    Pool = _Pyceler_Module_Constants_{Line}_Pool(Source_Code)'])
    Lines.extend(f'    {Name} = _Pyceler_Module_Constants_{Line}_Code({Template}{Name}, Pool)' for Name, Source, Mode in Fragments)
    Lines.extend([f'    Ranged = _Pyceler_Region_Range(Iterator, {Plan["Step"]})',
                  f'    Spans = _Pyceler_Region_Spans(Iterator, {Plan["Period"]!r}) if Ranged else ((Iterator, None),)',
                  '    for Span, Size in Spans:',
                  '        Blocks = _Pyceler_Module_Blocks(Span, Size)',
                  '        for Block in Blocks:', '            Completed = False', '            Mode = 2 if Allow_Threads else 1'])
    if Measured:
        Lines.extend(['            if Policy is not None:', '                Mode = _Pyceler_Choose((B.len(Block),), True, Policy) if Ranged else 0',
                      '            if Mode == 0:', '                _Pyceler_Module_Fallbacks += 1',
                      "                _Pyceler_Dispatch_Event('Execution', 'python_fallback', 0)",
                      '                _Pyceler_Module_Python_Block(Namespace, Block, Fallback)', '                continue'])
    if Reduction is not None:
        Args = ', '.join(['Block.start', 'Block.stop', *(f'Namespace[{Name!r}]' for Name in Reduction['Inputs'])])
        Target = Reduction['Target']
        Guard = ' and '.join(f'{Name!r} in Namespace' for Name in (Target, *Reduction['Inputs']))
        Lines.extend([f'            if Ranged and {Guard} and B.type(Namespace[{Target!r}]) is B.int and _Pyceler_Module_Exclusive():',
                      f'                Arguments = ({Args},)', f'                Current = Namespace[{Target!r}]',
                      f'                Result = _Pyceler_Module_Reduction_{Line}(Arguments, Mode == 2 or 100 <= Mode < 10000, Mode - 100 if 100 <= Mode < 10000 else 0)', '                if Result is not None:',
                      f'                    Namespace[{Target!r}] = Current + Result[0]', f'                    Namespace[{Plan["Index"]!r}] = Result[1]',
                      '                    Completed = True', '                    _Pyceler_Module_Checkpoint()'])
    else:
        Guard = ' and '.join(f'{Name!r} in Namespace' for Name in Plan['Inputs']) or 'True'
        Args = ', '.join(['Block.stop', 'Block.start', *(f'Namespace[{Name!r}]' for Name in Plan['Inputs']), *(['Block.step'] if Plan['Step'] is None else [])])
        Lines.extend([f'            if Ranged and {Guard} and _Pyceler_Module_Exclusive():',
                      f'                Result = _Pyceler_Module_Span_{Line}({Args})', '                if Result is not None:',
                      '                    _Pyceler_Module_Native += 1', '                    _Pyceler_Module_Team = 1'])
        for Position, Name in enumerate(Plan['Outputs']):
            Lines.append(f'                    Namespace[{Name!r}] = Result[{Position}]')
        Lines.extend(["                    _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)",
                      '                    Completed = True', '                    _Pyceler_Module_Checkpoint()'])
    Lines.extend(['            if not Completed:', '                for Index in Block:', f'                    Namespace[{Plan["Index"]!r}] = Index',
                  f'                    Result = {Step}(Namespace)', '                    if Result is None:',
                  '                        _Pyceler_Module_Fallbacks += 1', "                        _Pyceler_Dispatch_Event('Execution', 'python_fallback', 0)", '                        B.exec(Pure, Namespace)', '                    else:',
                  '                        _Pyceler_Module_Native += 1', '                        _Pyceler_Module_Team = 1',
                  "                        _Pyceler_Dispatch_Event('Execution', 'native_serial', 1)"])
    for Position, Name in enumerate(Outputs):
        Lines.append(f'                        Namespace[{Name!r}] = Result[{Position}]')
    if Reporting is not None:
        Lines.extend([f'                    if _Pyceler_Module_Test_{Line}(Namespace, Test):', '                        B.exec(Report, Namespace)'])
    Lines.extend(['                    _Pyceler_Signals()', '                    Ticks += 1', '                    if (Ticks & 1023) == 0:', '                        _Pyceler_Module_Checkpoint(True)'])
    if Reporting is not None:
        Lines.extend([f'            elif _Pyceler_Module_Test_{Line}(Namespace, Test):', '                B.exec(Report, Namespace)'])
    return '\n'.join(Lines)
