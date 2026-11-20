# Renamed, independent cases for direct-source lexical bindings and shared closure deletion.
def Factory(Seed):
    Value = Seed
    def Read():
        return Value
    def Set(New):
        nonlocal Value
        Value = New
        return Value
    def Delete():
        nonlocal Value
        del Value
    def Increase(Amount):
        nonlocal Value
        Value += Amount
        return Value
    del Value
    return Read, Set, Delete, Increase

def Local_Delete():
    Value = 1
    def Read():
        return Value
    del Value
    return Value

def Before_Binding():
    def Read():
        return Missing
    del Missing
    return Read

def Dead_Binding(Flag):
    if Flag:
        Target: object
    else:
        Ignored = False and (Target := 5)
    return Target

def Partial_Delete(Events):
    First, Second = 1, 2
    def Read():
        return First, Second
    del Second
    try:
        del First, Second
    except UnboundLocalError:
        Events.append('second was already empty')
    return Read

def Outer_Shadow():
    Label = 'outer'
    def Inner():
        Label = 'inner'
        return Label
    def Read():
        return Label
    del Label
    return Inner, Read

def Defaults():
    Label = 9
    def Inner(Value=Label):
        return Value, Label
    del Label
    return Inner

class Box:
    def Factory(self):
        __Value = 4
        def Read():
            return __Value
        del __Value
        return Read

def Late_Global():
    return Published_Later

globals()['Published_Later'] = 31
Published_Result = Published_Later

min = 7

def Global_Builtin():
    global min
    min += 2
    return min

def Read_Builtins(Values):
    return sum(Values), tuple(enumerate(Values)), sorted(Values), max(Values)
