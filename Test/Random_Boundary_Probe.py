import importlib.util
import json
import random
import sys
# Isolated verification for random boundary.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Error = None
    random.seed(817)
    try:
        Spec.loader.exec_module(Module)
    except Exception as Failure:
        Error = (type(Failure).__name__, str(Failure))
    State = (Error, Module.Row, getattr(Module, 'Column', None), getattr(Module, 'Middle', None), Module.Output.tobytes(), random.getstate())
    Native = sum(Value()['Native_Elements'] for Name, Value in vars(Module).items() if Name.startswith('_Pyceler_Fast_') and Name.endswith('Stats'))
    return State, Native

def Main():
    Reference, Unused = Load(sys.argv[1], 'Reference')
    Actual, Native = Load(sys.argv[2], sys.argv[3])
    assert Reference == Actual, (Reference[:4], Actual[:4])
    if sys.argv[3] not in ('Zero_Step', 'Empty_Outer', 'Empty_Middle'):
        assert Native > 0, (sys.argv[3], 'no native execution')
    print(json.dumps(dict(Case=sys.argv[3], Exact=True, Native=Native)))

if __name__ == '__main__':
    Main()
