import importlib.util
import json
import sys
from pathlib import Path

def _Run(File, Name, Fields):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[Name] = Module
    Error = None
    try:
        Spec.loader.exec_module(Module)
    except BaseException as Failure:
        Error = dict(Type=type(Failure).__name__, Arguments=Failure.args, Message=str(Failure))
    Values = {Field: getattr(Module, Field) for Field in Fields if hasattr(Module, Field)}
    Hooks = [Value for Key, Value in vars(Module).items() if Key.endswith("Module_Stats") and callable(Value)]
    Statistics = Hooks[0]() if Hooks else {}
    return dict(Values=Values, Error=Error, Native=Statistics)

def _Main():
    File = Path(sys.argv[1])
    Name = sys.argv[2]
    Fields = json.loads(sys.argv[3])
    Result = _Run(File, Name, Fields)
    print("PYCELER_MODULE_RESULT=" + json.dumps(Result, sort_keys=True))

if __name__ == "__main__":
    _Main()
