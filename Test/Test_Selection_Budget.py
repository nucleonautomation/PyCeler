import random
import sys
import types
import unittest
from unittest.mock import patch
from PyCeler.Selection_Worker import _Check, _Preflight
from PyCeler.Selection_Policy import _Selection_Table, _Explain_Selection
# Regression checks for validation, timing budgets and conservative dispatch.
class Selection_Budget(unittest.TestCase):
    def test_Unmeasured_Synthetic_Size_Does_Not_Revoke_Completed_Band(self):
        Complete = dict(Key='int', Size=128, Validation={'Python': 'valid', 'Serial': 'valid'}, Timings={Name: dict(Samples_Ns=[Time] * 5, Median_Ns=Time) for Name, Time in (('Python', 100), ('Serial', 10))})
        Limited = dict(Key='int', Size=2048, Validation={'Python': 'inconclusive: preflight budget'}, Timings={}, Probe_Constraint='worker_budget')
        self.assertEqual(_Selection_Table([Complete, Limited], 1.1), {'int': [(128, 1)]})
        Bounded = _Selection_Table([Complete, Limited], 1.1, True)['int']
        self.assertEqual(Bounded[:2], [(2049, 0), (2048, 0)])
        Item = dict(Function='Calculate', Cases=[dict(Limited, Dispatch_Winner='Serial')])
        _Explain_Selection(Item)
        self.assertIn('Unmeasured synthetic', Item['Summary']['Decisions'][0]['Reason'])
        self.assertIsNone(Item['Summary']['Decisions'][0]['Speedup'])

    def test_Inconclusive_Holdout_Still_Rejects_The_Band(self):
        Complete = dict(Key='int', Size=128, Validation={'Python': 'valid', 'Serial': 'valid'}, Timings={Name: dict(Samples_Ns=[Time] * 5, Median_Ns=Time) for Name, Time in (('Python', 100), ('Serial', 10))})
        Holdout = dict(Key='int', Size=1024, Holdout=True, Representative=True, Validation={'Python': 'inconclusive: budget'}, Timings={}, Probe_Constraint='worker_budget')
        self.assertTrue(all(Mode == 0 for Bound, Mode in _Selection_Table([Complete, Holdout], 1.1)['int']))

    def test_Preflight_Isolates_Mutations_Random_State_And_Trace(self):
        def Calculate(Values, Size):
            for Index in range(Size):
                Values[Index] += random.random()
            return Values
        def Trace(Frame, Event, Argument):
            return Trace
        Values = [0.0] * 64
        State = random.getstate()
        Previous = sys.gettrace()
        try:
            sys.settrace(Trace)
            self.assertTrue(_Preflight(Calculate, (Values, 64), Random_State=True))
            self.assertIs(sys.gettrace(), Trace)
        finally:
            sys.settrace(Previous)
        self.assertEqual(Values, [0.0] * 64)
        self.assertEqual(random.getstate(), State)

    def test_Large_Nested_Probe_Preserves_Earlier_And_Later_Cases(self):
        def Calculate(Values, Size):
            for Index in range(Size):
                Total = 0.0
                for Inner in range(Size):
                    Total += Inner * 0.125
                Values[Index % len(Values)] = Total
            return Values
        Item = dict(Probe='Calculate', Kind='numeric_region', Eligible=['Python', 'Serial'], Tuning=dict(Budget_Seconds=8))
        Modules = {Name: types.SimpleNamespace(Calculate=Calculate) for Name in ('Python', 'Serial')}
        Inputs = [('int', Size, (8,), ([0.0] * 8, Size)) for Size in (8, 1000000000, 16)]
        with patch('PyCeler.Selection_Worker._Cases', return_value=Inputs):
            Cases = _Check(Item, Modules, 0, 1.1)
        self.assertTrue(Cases[0]['Timings']['Python'])
        self.assertIn('preflight', Cases[1]['Validation']['Python'])
        self.assertEqual(Cases[1]['Timings'], {})
        self.assertTrue(Cases[2]['Timings']['Python'])
        self.assertTrue(all(Args[0] == [0.0] * 8 for Key, Size, Shape, Args in Inputs))

    def test_Preflight_Stops_Unbounded_Big_Integer_Growth(self):
        def Calculate(Size):
            Value = 2
            for Index in range(Size):
                Value = Value * Value
            return Value
        self.assertFalse(_Preflight(Calculate, (1000000,)))
