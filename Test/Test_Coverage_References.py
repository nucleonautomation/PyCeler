import asyncio
import unittest
from Test import Coverage_Loops

class Coverage_References(unittest.TestCase):
    def test_Independent_And_Dependent_References(self):
        Source = [2, -4, 6]
        Output = [0, 0, 0]
        self.assertIs(Coverage_Loops.Independent_Map(Source, Output), Output)
        self.assertEqual(Output, [4, -8, 12])
        self.assertEqual(Source, [2, -4, 6])
        self.assertEqual(Coverage_Loops.Dependent_Map([2, -4, 6]), [2, -2, 4])
        Overlap = [1, 2, 3]
        self.assertIs(Coverage_Loops.Alias_Map(Overlap, Overlap), Overlap)
        self.assertEqual(Overlap, [2, 3, 4])

    def test_Scalar_Control_And_Dynamic_Iteration(self):
        self.assertEqual(Coverage_Loops.Scalar_Control(0), 1)
        self.assertEqual(Coverage_Loops.Scalar_Control(4), 7)
        self.assertEqual(Coverage_Loops.Scalar_Control(25), 294)
        self.assertEqual(Coverage_Loops.Dynamic_Stride(7, -2, -3), 12)
        self.assertEqual(Coverage_Loops.Dependent_While(5), 15)
        self.assertEqual(Coverage_Loops.Enumerated([4, 5, 6]), 17)
        self.assertEqual(Coverage_Loops.Zipped([2, 3, 100], [4, 5]), 23)
        with self.assertRaises(ValueError):
            Coverage_Loops.Dynamic_Stride(0, 1, 0)

    def test_Callback_And_Exception_Event_Order(self):
        Events = []
        Output = [0, 0]
        Coverage_Loops.Callback_Boundary([2, 3], Output, lambda Event: Events.append((Event, tuple(Output))))
        self.assertEqual(Events, [("before", (0, 0)), ("after", (4, 6))])
        Events = Coverage_Loops.Exception_Boundary([2, 0, -3], [])
        self.assertEqual(Events, [5, "visited", "zero", "visited", -4, "visited"])
        self.assertEqual(Coverage_Loops.Early_Return([0, 3, -2, -5]), -2)

    def test_Fragmented_Transport_Has_Exact_Request_And_Event_Traces(self):
        Transport = Coverage_Loops.Mutable_Receiver([b"ab", b"c", b"de"])
        Events = []
        self.assertEqual(Coverage_Loops.Ordered_Receive(Transport, 5, Events), b"abcde")
        self.assertEqual(Transport._Requests, [5, 3, 2])
        self.assertEqual(Events, [("receive", b"ab"), ("receive", b"c"), ("receive", b"de")])
        Transport = Coverage_Loops.Mutable_Receiver([b"a", b""])
        Events = []
        with self.assertRaisesRegex(EOFError, "incomplete buffer"):
            Coverage_Loops.Ordered_Receive(Transport, 2, Events)
        self.assertEqual(Transport._Requests, [2, 1])
        self.assertEqual(Events, [("receive", b"a"), ("receive", b"")])

    def test_Comprehension_And_Generator_References(self):
        List_Result, Set_Result, Dict_Result, Generator = Coverage_Loops.Comprehensions([-1, 0, 2])
        self.assertEqual(List_Result, [4])
        self.assertEqual(Set_Result, {-1, 0, 2})
        self.assertEqual(Dict_Result, {0: -1, 1: 0, 2: 2})
        self.assertEqual(list(Generator), [1, -2, 0, 0, -2, 4])
        Events = []
        def Input():
            for Value in (2, 3):
                Events.append(Value)
                yield Value
        Generator = Coverage_Loops.Generator_Suspension(Input())
        self.assertEqual(Events, [])
        self.assertEqual(next(Generator), 4)
        self.assertEqual(Events, [2])
        Generator.close()
        self.assertEqual(Events, [2])

    def test_Async_Reference_Preserves_Consumption_Order(self):
        Events = []
        async def Input():
            for Value in (2, 3):
                Events.append(Value)
                yield Value
        self.assertEqual(asyncio.run(Coverage_Loops.Async_Iteration(Input())), [2, 3])
        self.assertEqual(Events, [2, 3])
