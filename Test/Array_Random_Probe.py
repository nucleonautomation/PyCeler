import copy
import json
import random
import sys
from pathlib import Path
import numpy as np
# Isolated verification for random draw order and state preservation.
sys.path.insert(0, str(Path(__file__).parent))
from Array_Region_Probe import Load, Observe, Counters

def Main():
    Reference, Native = Load(sys.argv[1], 'Reference'), Load(sys.argv[2], 'Array_Random_Loops')
    Cases = []
    for Size in (0, 1, 8, 64, 128):
        Cases.append(('Random_Image', (np.zeros((Size, 13, 2), dtype=np.uint8), np.zeros((Size, 13), dtype=np.float32), Size, 13, 2), Size >= 8))
        Cases.append(('Random_Pairs', (np.zeros((Size, 13), dtype=np.float64), Size, 13), Size >= 8))
    Cases.extend([('Random_Image', (np.zeros((8, 13, 2), dtype=np.uint8), np.zeros((8, 13), dtype=np.float32), 10, 13, 2), False), ('Random_Domain', (np.zeros((64, 13), dtype=np.float64), 64, 13, 20.5), False), ('Random_Domain', (np.zeros((64, 13), dtype=np.float64), 64, 13, 100.5), True)])
    Positive = 0
    Parallel = len(sys.argv) < 5 or sys.argv[4] == 'parallel'
    Conditional = ('Random_Variable', 'Random_Balanced', 'Random_Condition', 'Random_Branch', 'Random_Nested')
    for Size in (0, 1, 8, 257, 4096):
        for Dtype in ('float32', 'float64'):
            Data = np.where(np.arange(Size) % 3 == 0, -0.25, 0.25).astype(Dtype)
            Cases.extend((Name, (Data, np.zeros_like(Data)), Size > 1) for Name in Conditional)
    Data = np.resize(np.array([-0.25, 0.25]), (64, 13))
    Cases.extend([('Random_Rows', (Data, np.zeros_like(Data), 64, 13), True), ('Random_Branch_Error', (Data.reshape(-1), np.zeros(Data.size)), False)])
    for Value in (-0.25, 0.25):
        Data = np.full(4096, Value)
        Cases.extend((Name, (Data, np.zeros_like(Data)), True) for Name in ('Random_Variable', 'Random_Balanced'))
    Data = np.resize(np.array([-0.25, 0.25]), 65540)
    Cases.extend((Name, (Data, np.zeros_like(Data)), True) for Name in ('Random_Variable', 'Random_Balanced'))
    Teams = 0
    for Name, Args, Required in Cases:
        Results = []
        Before = Counters(Native)
        Native._Pyceler_Dispatch_Stats(True, True)
        for Module in (Reference, Native):
            random.seed(1931)
            random.gauss(0.0, 1.0)
            Results.append((Observe(getattr(Module, Name), copy.deepcopy(Args)), random.getstate()))
        assert Results[0] == Results[1], (Name, 'result, error, mutations or RNG state differ')
        if Required:
            assert Counters(Native)['Native_Elements'] > Before['Native_Elements'], (Name, 'no native execution')
            Positive += 1
        if Name in Conditional or Name == 'Random_Rows':
            Parallel_Delta = Counters(Native)['Parallel_Elements'] - Before['Parallel_Elements']
            Totals = Native._Pyceler_Dispatch_Stats().get('Totals', {})
            if Parallel and Name in ('Random_Balanced', 'Random_Branch') and Args[0].size >= 4096:
                assert Parallel_Delta > 0 and Totals.get('Maximum_Team', 0) > 1, (Name, 'no parallel team', Totals)
                Teams += 1
            if not Parallel or Name in ('Random_Variable', 'Random_Condition', 'Random_Nested', 'Random_Rows'):
                assert Parallel_Delta == 0, (Name, 'variable draw sequence must remain ordered')
    Original = random.random
    Calls = []
    try:
        for Module in (Reference, Native):
            State = [0]
            def Custom():
                State[0] += 1
                if State[0] == 17:
                    raise RuntimeError('custom random boundary')
                return 0.25
            random.random = Custom
            Args = (np.zeros((8, 13), dtype=np.float64), 8, 13)
            Calls.append((Observe(Module.Random_Pairs, Args), State[0]))
        assert Calls[0] == Calls[1]
    finally:
        random.random = Original
    Report = dict(Comparisons=len(Cases) + 1, Positive=Positive, Parallel=Teams, Counters=Counters(Native))
    Path(sys.argv[3]).write_text(json.dumps(Report, indent=2))
    print(json.dumps(Report))

if __name__ == '__main__':
    Main()
