import ast
import copy
from .Math_Maps import _Module_Constant_Anchor
from .Helper_Kernel import _Region_Roots
# Emit guarded iterator transactions while preserving constructor order and final iteration targets.
def _Iterator_Kernel(Plan, Line):
    if 'Iterator' not in Plan:
        return ''
    Numeric, Fast = f'_Pyceler_Numeric_{Line}_', f'_Pyceler_Fast_{Line}_'
    Contract = Plan['Iterator']
    Enum = Contract['Kind'] == 'enumerate'
    Lines = ['cdef extern from "Python.h":', f'    {Numeric}Object {Numeric}Enum_Type "PyEnum_Type"', f'    {Numeric}Object {Numeric}Zip_Type "PyZip_Type"', f'    {Numeric}Object {Numeric}Range_Type "PyRange_Type"', f'from cpython.list cimport PyList_CheckExact as {Numeric}Exact_List', f'from cpython.long cimport PyLong_CheckExact as {Numeric}Exact_Integer', f'cdef object {Numeric}Iterator_Span(object Binding, tuple Arguments, dict Keywords):', '    import builtins as B', f'    if Binding is not <object>&{Numeric}{"Enum" if Enum else "Zip"}_Type:', '        return None', '    Start = 0', '    Strict = False']
    if Enum:
        Lines.extend(['    Start = Arguments[1] if B.len(Arguments) == 2 else Keywords.get("start", 0)', f'    if not {Numeric}Exact_Integer(Start) or not -1125899906842624 <= Start <= 1125899906842624:', '        return None', '    Sources = Arguments[:1]'])
    else:
        Lines.extend(['    Strict = Keywords.get("strict", False)', '    if Strict is not True and Strict is not False:', '        return None', '    Sources = Arguments'])
    Lines.extend(['    Lengths = []', '    for Source in Sources:', f'        if {Numeric}Exact_List(Source):', '            Lengths.append(B.len(Source))', '            continue', f'        N = {Fast}System.modules.get("numpy")', f'        Core = {Fast}System.modules.get("numpy._core.multiarray") or {Fast}System.modules.get("numpy.core.multiarray")', '        if N is None or Core is None or N.ndarray is not Core.ndarray or B.type(Source) is not N.ndarray or Source.ndim != 1:', '            return None', '        Lengths.append(Source.shape[0])', '    Length = Lengths[0]', '    for Value in Lengths[1:]:', '        if Strict and Value != Length:', '            return None', '        if Value < Length:', '            Length = Value', '    if Length < 2 or Start + Length > 1125899906842624:', '        return None', f'    return (<object>&{Numeric}Range_Type)(Start, Start + Length)', ''])
    return '\n'.join(Lines)

def _Iterator_Source(Plan, Node, Line, Prefix, Table, Alternative=None):
    Contract = Plan['Iterator']
    Numeric = f'{Prefix}Numeric_{Line}_'
    Binding, Arguments, Keywords, Iterator, Span, Result, Namespace = (f'{Prefix}Iterator_{Name}_{Line}' for Name in ('Binding', 'Arguments', 'Keywords', 'Value', 'Span', 'Result', 'Namespace'))
    Call = Node.iter
    Arguments_Text = '(' + ', '.join(ast.unparse(Value) for Value in Call.args) + ',)'
    Keywords_Text = '{' + ', '.join(repr(Value.arg) + ': ' + ast.unparse(Value.value) for Value in Call.keywords) + '}'
    Globals = f'{Prefix}Module_Constants_{Line}.__globals__'
    Names = tuple(dict.fromkeys((*Plan['Names'], *Plan['Output_Guards'])))
    Pairs = [repr(Name) + ': ' + Name for Name in Names]
    Pairs.extend(repr(Root) + ': ' + (Root if Root in Plan['Local_Bindings'] else f"{Globals}.get({Plan.get('Global_Names', {}).get(Root, Root)!r})") for Root in _Region_Roots(Plan))
    Used = {Part.id for Statement in Node.body for Part in ast.walk(Statement) if isinstance(Part, ast.Name) and isinstance(Part.ctx, ast.Load)}
    Length = 'len' if 'len' in Used else f'{Prefix}Python_Builtins.len'
    Range = 'range' if 'range' in Used else f'{Prefix}Python_Builtins.range'
    if 'len' in Plan.get('Captured_Inputs', ()) and 'len' in Used and 'len' not in Names:
        Pairs.append("'len': len")
    Lines = [_Module_Constant_Anchor(Node, Line, Prefix), f'{Binding} = {ast.unparse(Call.func)}', f'{Arguments} = {Arguments_Text}', f'{Keywords} = {Keywords_Text}', f'{Iterator} = {Binding}(*{Arguments}, **{Keywords})', f'{Span} = {Numeric}Iterator_Span({Binding}, {Arguments}, {Keywords})', f'del {Binding}, {Arguments}, {Keywords}', f'{Result} = None', f'if {Span} is not None:', '    try:', f'        {Namespace} = {{' + ', '.join(Pairs) + '}', f'    except {Numeric}Name_Error:', '        pass', '    else:']
    def Attempt(Current, Label):
        Policy = f'{Prefix}Table_{Label}' if Table is not None else 'None'
        Extra = ', [0]' if Current['Kind'] == 'numeric_region' else ''
        return f"{Result} = {Prefix}Numeric_{Label}_Try({Namespace}, {Span}, {Span}, {Range}, {Length}, {Policy}, {Prefix}Module_Constants_{Label}.__code__, {Globals}{Extra})"
    if Alternative is None:
        Lines.append('        ' + Attempt(Plan, Line))
    else:
        Label = str(Line) + '_List'
        Objects = '(' + ', '.join(Alternative['Buffers']) + ',)'
        Lines.extend([f'        if {Prefix}Numeric_{Label}_Storage({Objects}):', '            ' + Attempt(Alternative, Label), '        else:', '            ' + Attempt(Plan, Line)])
        Lines.insert(1, _Module_Constant_Anchor(Node, Label, Prefix))
    Lines.extend([f'        del {Namespace}', f'del {Span}', 'try:', f'    if {Result} is None:'])
    Fallback = copy.deepcopy(Node)
    Fallback.iter = ast.Name(id=Iterator, ctx=ast.Load())
    Lines.extend('        ' + Value for Value in ast.unparse(Fallback).splitlines())
    Outputs = Plan.get('Live_Outputs', Plan['Written'])
    Assignment = ', '.join(Outputs) + (',' if len(Outputs) == 1 else '') + ' = ' + Result if Outputs else 'pass'
    Lines.extend(['    else:', '        ' + Assignment, 'finally:', f'    del {Iterator}, {Result}'])
    return '\n'.join(Lines)
