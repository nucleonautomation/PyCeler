import math as M

from math import sin as Wave

def Map_acos(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.acos(Source[Index])
    return Output

def Map_acosh(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.acosh(Source[Index])
    return Output

def Map_asin(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.asin(Source[Index])
    return Output

def Map_asinh(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.asinh(Source[Index])
    return Output

def Map_atan(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.atan(Source[Index])
    return Output

def Map_atanh(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.atanh(Source[Index])
    return Output

def Map_cbrt(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.cbrt(Source[Index])
    return Output

def Map_cos(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.cos(Source[Index])
    return Output

def Map_cosh(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.cosh(Source[Index])
    return Output

def Map_exp(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.exp(Source[Index])
    return Output

def Map_exp2(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.exp2(Source[Index])
    return Output

def Map_expm1(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.expm1(Source[Index])
    return Output

def Map_fabs(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.fabs(Source[Index])
    return Output

def Map_isfinite(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.isfinite(Source[Index])
    return Output

def Map_isinf(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.isinf(Source[Index])
    return Output

def Map_isnan(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.isnan(Source[Index])
    return Output

def Map_log(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.log(Source[Index])
    return Output

def Map_log10(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.log10(Source[Index])
    return Output

def Map_log1p(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.log1p(Source[Index])
    return Output

def Map_sin(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.sin(Source[Index])
    return Output

def Map_sinh(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.sinh(Source[Index])
    return Output

def Map_sqrt(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.sqrt(Source[Index])
    return Output

def Map_tan(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.tan(Source[Index])
    return Output

def Map_tanh(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.tanh(Source[Index])
    return Output

def Composed(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = M.sin(M.sqrt(Source[Index])) + M.cos(Source[Index]) * M.exp(M.log(Source[Index]) * 0.1)
    return Output

def Aliased(Source, Output):
    for Index in range(len(Source)):
        Output[Index] = Wave(Source[Index])
    return Output
