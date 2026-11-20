def _Monitoring_Kernel(Prefix):  # Generate runtime checks for tracing, profiling and other observers that constrain native execution.
    Lines = [f'from cpython.module cimport PyModule_CheckExact as {Prefix}Monitoring_Module',
             'cdef extern from "Python.h":', f'    int {Prefix}Monitoring_Function "PyCFunction_Check"(object Value)', f'    const char* {Prefix}Monitoring_Version "Py_GetVersion"()',
             f'cdef str {Prefix}Monitoring_Runtime = (<bytes>{Prefix}Monitoring_Version()).decode("ascii")',
             f'cdef int {Prefix}Monitoring_Mode = 0 if {Prefix}Monitoring_Runtime.startswith("3.11.") else 1 if {Prefix}Monitoring_Runtime.startswith(("3.12.", "3.13.", "3.14.")) else 2',
             f'cdef object {Prefix}Monitoring = {Prefix}System.__dict__.get("monitoring")',
             f'cdef bint {Prefix}Monitoring_Code(object Code=None):', '    cdef object Monitor, Events, Local, Frame',
             f'    if {Prefix}Monitoring_Mode == 0:', '        return True',
             f'    Monitor = {Prefix}Monitoring',
             f'    if {Prefix}Monitoring_Mode != 1 or not {Prefix}Monitoring_Module(Monitor) or {Prefix}System.__dict__.get("monitoring") is not Monitor:', '        return False',
             '    Events, Local = Monitor.__dict__.get("get_events"), Monitor.__dict__.get("get_local_events")',
             '    for Name, Function in (("get_events", Events), ("get_local_events", Local)):',
             f'        if not {Prefix}Monitoring_Function(Function) or Function.__self__ is not Monitor or Function.__name__ != Name:', '            return False',
             '    if Code is None:', f'        Frame = {Prefix}System.__dict__.get("_getframe")',
             f'        if not {Prefix}Monitoring_Function(Frame) or Frame.__self__ is not {Prefix}System or Frame.__name__ != "_getframe":', '            return False',
             '        Code = Frame().f_code',
             '    for Tool in range(6):', '        if Events(Tool) or Local(Tool, Code):', '            return False', '    return True']
    return '\n'.join(Lines)
