from .Runtime_Resources import _Resource
# Register original helper identities and generate guards for calls admitted into native regions.
def _Helper_Preamble(Source, Plans):
    Names, Pending = set(), list(Plans)
    while Pending:
        Plan = Pending.pop()
        if Plan is None:
            continue
        Names.update(Name for Name, Text in Plan.get('Helper_Sources', ()))
        Pending.extend(Plan[Key] for Key in ('Alternate', 'List_Alternative', 'Array_Alternative') if Key in Plan)
    if not Names:
        return ''
    Prefix = '_Pyceler_Helper_'
    return '\n'.join([f'def {Prefix}Reference(Value):', '    return Value', f'cdef object {Prefix}Function_Type = type({Prefix}Reference)', f'cdef object {Prefix}Code_Type = type({Prefix}Reference.__code__)', f'cdef tuple {Prefix}Names = {tuple(sorted(Names))!r}', f'cdef dict {Prefix}Originals = {{}}']) + '\n'

def _Helper_Kernel(Plan, Line):
    Sources = Plan.get('Helper_Sources', ())
    if not Sources:
        return ''
    Names = [Name for Name, Source in Sources]
    Roots = tuple((Root, Names.index(Name), Plan.get('Helper_Globals', {}).get(Root)) for Root, Name in Plan['Helper_Roots'].items())
    return _Resource('Helper_Runtime.pxi.in').replace('HELPER_NAMES', repr(tuple(Names))).replace('HELPER_ROOTS', repr(Roots)).replace('HELPER_MONITOR', f'_Pyceler_Fast_{Line}_Monitoring_Code').replace('HELPER_PREFIX', f'_Pyceler_Helper_{Line}_')

def _Helper_Guards(Plan, Line):
    return [f'if not _Pyceler_Helper_{Line}_Check(Namespace, Source_Globals):', '    return None'] if Plan.get('Helper_Sources') else []

def _Region_Roots(Plan):
    Roots = dict.fromkeys((*(Root for Root, Name, Module in Plan['Math']['Bindings']), *Plan.get('Random_Roots', ()), *Plan.get('Helper_Roots', ())))
    return tuple(Root for Root in Roots if Root not in Plan.get('Helper_Globals', {}))

def _Global_Bindings(Plan):
    return tuple((Root, Plan.get('Helper_Globals', {}).get(Root, Plan.get('Global_Names', {}).get(Root, Root))) for Root in _Region_Roots(Plan) if Root not in Plan['Local_Bindings'])
