import json
import sys
from pathlib import Path
import numpy

Directory = Path(sys.argv[1])
sys.path.insert(0, str(Directory))
import Mixed
Report = json.loads((Directory / "Mixed.selection.json").read_text(encoding="utf-8"))
Calls = []

def _Record(Frame, Event, Value):
    if Event == "call" and Frame.f_code.co_filename == "Mixed.py":
        Calls.append(Frame.f_code.co_name)

def _Verify(Function, Args, Winner):
    Calls.clear()
    sys.setprofile(_Record)
    try:
        Result = Function(*Args)
    finally:
        sys.setprofile(None)
    Expected = [Function.__name__] if Winner == "Python" or sys.argv[2] != "2" else []
    assert Calls == Expected, (Function.__name__, Winner, Calls, Expected)
    return Result

for Item in Report["Items"]:
    for Case in Item["Cases"]:
        if Item["Function"] == "Clear_Elements":
            Values = numpy.full(Case["Shape"], 7, dtype=Case["Key"])
            assert _Verify(Mixed.Clear_Elements, (Values,), Case["Winner"]) is Values
            assert not Values.any()
        else:
            Rows, Columns = Case["Arguments"]
            assert _Verify(Mixed.Count, (Rows, Columns), Case["Winner"]) == sum(Row + Column for Row in range(Rows) for Column in range(Columns))
Values = [7, 3]
assert _Verify(Mixed.Clear_Elements, (Values,), "Python") is Values and Values == [0, 0]
assert Mixed.Count() == 16
