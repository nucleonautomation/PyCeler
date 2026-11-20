import ast
import copy
from .Numeric_Regions import _Numeric_Region_Plan
from .Common_Analysis import _Independent_Outer_Storage, _Parts, _Contained_Scalar_Edits, _Binding_Targets
from .Common_Values import _Real_Inputs
from .Common_Scopes import _Function_Scopes, _Bind_Region_Scope
from .Fast_Math import _Fast_Imports
from .Common_Calls import _Call_Facts
from .Array_Random import _Random_Draw_Bounds
from .Iterator_Regions import _Iterator_Plan
from .Array_Index_Facts import _Array_Index_Facts
# Normalize ndarray syntax and attach guarded array plans to the shared numeric-region representation.
class _Array_Normalize(ast.NodeTransformer):
    def __init__(self):
        self._Rows = {}
        self._Explicit = False

    def visit_Subscript(self, Node):
        if isinstance(Node.value, ast.Attribute) and Node.value.attr == 'shape' and isinstance(Node.value.value, ast.Name) and isinstance(Node.slice, ast.Constant) and type(Node.slice.value) is int and Node.slice.value >= 0:
            Value = copy.deepcopy(Node.value.value)
            for Axis in range(Node.slice.value):
                Value = ast.Subscript(value=Value, slice=ast.Constant(0), ctx=ast.Load())
            self._Explicit = True
            return ast.copy_location(ast.Call(func=ast.Name(id='len', ctx=ast.Load()), args=[Value], keywords=[]), Node)
        Node = self.generic_visit(Node)
        if isinstance(Node.slice, ast.Tuple):
            self._Explicit = True
            Result = Node.value
            for Position, Index in enumerate(Node.slice.elts):
                Result = ast.Subscript(value=Result, slice=Index, ctx=Node.ctx if Position + 1 == len(Node.slice.elts) else ast.Load())
            return ast.copy_location(Result, Node)
        return Node

    def visit_Assign(self, Node):
        if len(Node.targets) == 1 and isinstance(Node.targets[0], (ast.Tuple, ast.List)) and isinstance(Node.value, ast.Subscript):
            Target = Node.targets[0]
            if all(isinstance(Value, ast.Name) for Value in Target.elts):
                self._Explicit = True
                Root = Node.value.value
                if isinstance(Root, ast.Name):
                    self._Rows[Root.id] = len(Target.elts)
                return [ast.copy_location(ast.Assign(targets=[copy.deepcopy(Value)], value=ast.Subscript(value=self.visit(copy.deepcopy(Node.value)), slice=ast.Constant(Index), ctx=ast.Load())), Node) for Index, Value in enumerate(Target.elts)]
        return self.generic_visit(Node)

def _Array_Independent(Plan):
    return _Independent_Outer_Storage(Plan)

def _Compatible_Ordered_Map(Plan, Node, Edit):
    Previous = Edit[1]
    if Node.end_lineno < Previous.lineno or Node.lineno > Previous.end_lineno:
        return True
    if Node.lineno > Previous.lineno or Node.end_lineno < Previous.end_lineno:
        return False
    Bindings = _Fast_Imports(Edit[3])
    return all(Root in Bindings and Bindings[Root] == (None if Module else Name) for Root, Name, Module in Plan['Math']['Bindings'])
# Reuse numeric control-flow analysis, then specialize storage and scalar operations for ndarrays.
def _Array_Plan(Function, Outer, Available, Module, Hints, Helpers=None, Call_Bindings=None, Internal=(), Normalized=False):
    Normalize = _Array_Normalize()
    Normal = ast.fix_missing_locations(Normalize.visit(copy.deepcopy(Outer)))
    Explicit = Normalized or Normalize._Explicit or any(isinstance(Node, ast.Name) and Node.id in Hints for Node in ast.walk(Outer))
    Plan = _Numeric_Region_Plan(Function, Normal, Available, Module, Array=True, Helpers=Helpers, Call_Bindings=Call_Bindings, Internal=Internal, Normalized=Normalized)
    if Plan is None:
        return None
    if any(isinstance(Node, ast.While) for Node in ast.walk(Normal)):
        return None
    if any(Name in Available for Name in Plan['Builtins']):  # A shadowed builtin may execute user code and cannot use the builtin fast path.
        return None
    Body_Calls = {(Node.lineno, Node.col_offset) for Statement in Normal.body for Node in ast.walk(Statement) if isinstance(Node, ast.Call)}
    Random_Roots = tuple(sorted({Root for Position, Root in Plan['Random'].items() if Position in Body_Calls}))
    Random_Ranges = []
    Random_Bounds = (0, 0)
    if Random_Roots:
        if len(Random_Roots) != 1 or any(isinstance(Node, (ast.Continue, ast.Break)) for Node in ast.walk(Normal)):
            return None
        Body = Normal.body
        while len(Body) == 1 and isinstance(Body[0], ast.For):
            Loop = Body[0]
            if any(isinstance(Node, ast.Call) and (Node.lineno, Node.col_offset) in Plan['Random'] for Node in ast.walk(Loop.iter)):
                return None
            if any(isinstance(Node, ast.Name) and Node.id in Plan['Written'] for Node in ast.walk(Loop.iter)):
                return None
            Random_Ranges.append(ast.unparse(Loop.iter))
            Body = Loop.body
        if any(isinstance(Node, ast.For) for Statement in Body for Node in ast.walk(Statement)):
            return None
        Random_Bounds = _Random_Draw_Bounds(Body, Plan['Random'])
    Real_Inputs = _Real_Inputs(Normal, Plan['Inputs'], Plan['Read_Buffers'], Plan['Carry'], tuple(Root + '.' + Name if Module else Root for Root, Name, Module in Plan['Math']['Bindings']))
    Pure_Scalars = not Plan['Read_Buffers'] and not Plan['Carry']
    def Rewrite(Value):
        if not isinstance(Value, tuple):
            return Value
        if Value and Value[0] == 'python_power':
            return ('array_power', Rewrite(Value[1]), Value[2])
        if Value and Value[0] == 'checked_integer' and not Pure_Scalars:
            return ('array_arithmetic', *(Rewrite(Part) for Part in Value[1:]))
        Operations = ('buffer', 'dimension', 'helper', 'conditional', 'compare') if Pure_Scalars else ('buffer', 'dimension', 'arithmetic', 'negative', 'absolute', 'helper', 'conditional', 'compare')
        if Value and isinstance(Value[0], str) and Value[0] in Operations:
            return ('array_' + Value[0], *(Rewrite(Part) for Part in Value[1:]))
        return tuple(Rewrite(Part) for Part in Value)
    Plan['Program'] = Rewrite(Plan['Program'])  # Preserve control-flow IR while replacing only ndarray-specific value operations.
    _Array_Index_Facts(Plan, Normal)
    Axes = {Name: [set() for Axis in range(Value[1])] for Name, Value in Plan['Buffers'].items()}
    Parents = {Child: Parent for Parent in ast.walk(Normal) for Child in ast.iter_child_nodes(Parent)}
    for Node in ast.walk(Normal):
        if not isinstance(Node, ast.Subscript) or isinstance(Parents.get(Node), ast.Subscript) and Parents[Node].value is Node:
            continue
        Coordinates = []
        while isinstance(Node, ast.Subscript):
            Coordinates.insert(0, Node.slice)
            Node = Node.value
        if isinstance(Node, ast.Name) and Node.id in Axes and len(Coordinates) == len(Axes[Node.id]):
            for Axis, Value in enumerate(Coordinates):
                Axes[Node.id][Axis].add(Value.value if isinstance(Value, ast.Constant) and type(Value.value) is int and Value.value >= 0 else None)
    Plan['Array_Axes'] = {Name: tuple(max(Values) + 1 if Values and None not in Values else None for Values in Dimensions) for Name, Dimensions in Axes.items()}
    if not Module:
        Locals = {Argument.arg for Argument in Function.args.posonlyargs + Function.args.args + Function.args.kwonlyargs}
        Locals.update(Node.id for Node in ast.walk(Function) if isinstance(Node, ast.Name) and isinstance(Node.ctx, ast.Store))
        Locals.update(Alias.asname or Alias.name.split('.')[0] for Node in ast.walk(Function) if isinstance(Node, (ast.Import, ast.ImportFrom)) for Alias in Node.names)
        Plan['Local_Bindings'] = tuple(Name for Name in Plan['Local_Bindings'] if Name in Locals)
    Plan.update(Kind='array_region', Original=Outer, Array_Rows=Normalize._Rows, Random_Roots=Random_Roots, Random_Ranges=tuple(Random_Ranges), Real_Inputs=tuple(Real_Inputs), Pure_Scalars=Pure_Scalars, Parallel=_Array_Independent(Plan), Transformations=('Native ndarray regions', 'Rank-specific stride indexing', 'Ordered reductions and independent OpenMP rows'))
    Plan.update(Random_Count=Random_Bounds[1], Random_Dynamic=Random_Bounds[0] != Random_Bounds[1])
    Plan['Parallel'] = Plan['Parallel'] and not Plan['Random_Dynamic']  # Variable random consumption prevents independent partitioning of the RNG stream.
    Plan['Math_Imports'] += tuple('import random as ' + Root for Root in sorted(set(Plan['Random'].values())))
    Plan['Probe'].body[0] = copy.deepcopy(Outer)
    return Plan

def _Iteration_Hints(Node):
    if not isinstance(Node, ast.For):
        return ()
    Value, Target = Node.iter, Node.target
    if isinstance(Value, ast.Name) and isinstance(Target, ast.Name):
        return ((Target.id, Value.id),)
    if not isinstance(Value, ast.Call) or not isinstance(Value.func, ast.Name) or not isinstance(Target, (ast.Tuple, ast.List)):
        return ()
    if Value.func.id == 'enumerate' and Value.args and len(Target.elts) == 2:
        Pairs = ((Target.elts[1], Value.args[0]),)
    elif Value.func.id == 'zip' and len(Target.elts) == len(Value.args):
        Pairs = zip(Target.elts, Value.args)
    else:
        return ()
    return tuple((Target.id, Value.id) for Target, Value in Pairs if isinstance(Target, ast.Name) and isinstance(Value, ast.Name))

def _Array_Hints(Scope, Aliases):
    Hints = set()
    Parts = tuple(_Parts(Scope))
    for Node in Parts:
        if isinstance(Node, ast.arg) and (isinstance(Node.annotation, ast.Constant) and Node.annotation.value == 'numpy.ndarray' or isinstance(Node.annotation, ast.Attribute) and Node.annotation.attr == 'ndarray' and isinstance(Node.annotation.value, ast.Name) and Node.annotation.value.id in Aliases):
            Hints.add(Node.arg)
        if isinstance(Node, ast.Assign) and isinstance(Node.value, ast.Call):
            Target = Node.value.func
            while isinstance(Target, ast.Attribute):
                Target = Target.value
            if isinstance(Target, ast.Name) and Target.id in Aliases or isinstance(Node.value.func, ast.Attribute) and Node.value.func.attr == 'query':
                Hints.update(Part.id for Target in Node.targets for Part in ast.walk(Target) if isinstance(Part, ast.Name))
    Pairs = tuple(Pair for Node in Parts for Pair in _Iteration_Hints(Node))
    while True:
        Added = {Target for Target, Source in Pairs if Source in Hints} - Hints
        if not Added:
            return Hints
        Hints.update(Added)
# Keep competing backends attached to the same region instead of duplicating overlapping rewrites.
def _Array_Region_Plans(Tree, Edits, Scopes=None, Calls=None):
    Plans = {}
    Calls = _Call_Facts(Tree) if Calls is None else Calls
    Helpers = Calls['Helpers']
    Scope, Captures, Locals, Scope_Globals = '<module>', frozenset(), frozenset(), {}
    Occupied = [(Edit[1].lineno, Edit[1].end_lineno) for Edit in Edits.values() if Edit[3] is None or Edit[3].get('Kind') != 'math_map' or Edit[3].get('Fast_Math')]
    Maps = {Edit[1].lineno: Edit[3] for Edit in Edits.values() if Edit[3] is not None and (Edit[3].get('Kind') is None and Edit[3].get('Arithmetic') or Edit[3].get('Kind') == 'math_map')}
    Ordered = tuple(Edit for Edit in Edits.values() if Edit[3] is not None and Edit[3].get('Kind') == 'math_map')
    Aliases = {Alias.asname or Alias.name for Node in Tree.body if isinstance(Node, ast.Import) for Alias in Node.names if Alias.name == 'numpy'}
    Hints = _Array_Hints(Tree, Aliases)
    def Visit(Function, Statements, Available, Module):
        Bound = Available.copy()
        for Node in Statements:
            Existing = Maps.get(getattr(Node, 'lineno', None))
            Contained = _Contained_Scalar_Edits(Node, Edits)
            if isinstance(Node, ast.For) and (Existing is not None or not any(Node.lineno <= End and Node.end_lineno >= Start and (Start, End) not in Contained.values() for Start, End in Occupied)):
                Plan = _Iterator_Plan(_Array_Plan, Function, Node, Bound, Module, Hints | (set(Existing['Arrays']) if Existing is not None else set()), Helpers, Calls['Math'])
                if Plan is not None and not all(_Compatible_Ordered_Map(Plan, Node, Edit) for Edit in Ordered):
                    Plan = None
                if Plan is not None:
                    if not _Bind_Region_Scope(Plan, Scope, Captures, Locals, Scope_Globals, Bound):
                        continue
                    if Existing is not None:
                        if set(Plan['Names']) == set(Existing['Names']):
                            Plan['Selection_Output'] = Existing['Output']
                            Plan['Single_Only'] = bool(Existing.get('Fast_Math')) or len(Existing.get('Arithmetic', ())) == 1 and not Existing.get('Comparison')
                            Existing['Array_Alternative'] = Plan
                        continue
                    Plans[Node.lineno] = (Plan['Names'], Node, Function, Plan)
                    for Previous in Contained:
                        Edits.pop(Previous)
                    Occupied.append((Node.lineno, Node.end_lineno))
                    continue
            if isinstance(Node, ast.Assign):
                Bound.update(Part.id for Target in Node.targets for Part in ast.walk(Target) if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Store))
            elif isinstance(Node, (ast.Import, ast.ImportFrom)):
                Bound.update(Alias.asname or Alias.name.split('.')[0] for Alias in Node.names if Alias.name != '*')
            elif isinstance(Node, ast.If):
                Left = Visit(Function, Node.body, Bound, Module)
                Right = Visit(Function, Node.orelse, Bound, Module)
                Bound.update(Left & Right)
            elif isinstance(Node, (ast.For, ast.While)):
                Visit(Function, Node.body, Bound | (_Binding_Targets(Node.target) if isinstance(Node, ast.For) else set()), Module)
                Visit(Function, Node.orelse, Bound, Module)
        return Bound
    Globals = Visit(Tree, Tree.body, set(), True)
    Global_Hints = Hints.copy()
    for Function, Scope, Captures, Locals, Scope_Globals in _Function_Scopes(Tree) if Scopes is None else Scopes:
        if not isinstance(Function, ast.FunctionDef) or Function.decorator_list or getattr(Function, 'type_params', ()):
            continue
        Parts = list(ast.walk(Function))
        if any(isinstance(Node, (ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom, ast.Try, ast.Delete, ast.Lambda, ast.ClassDef)) or isinstance(Node, ast.FunctionDef) and Node is not Function or isinstance(Node, ast.Name) and Node.id in {'locals', 'globals', 'vars', 'eval', 'exec', '_getframe', 'currentframe'} for Node in Parts):
            continue
        Names = {Argument.arg for Argument in Function.args.posonlyargs + Function.args.args + Function.args.kwonlyargs}
        Hints = {Name for Name, Symbol in Scope_Globals.items() if Symbol in Global_Hints} | _Array_Hints(Function, Aliases)
        Visible = {Name for Name, Symbol in Scope_Globals.items() if Symbol in Globals}
        Visit(Function, Function.body, Names | Visible | set(Captures), False)
    return Plans
