import unittest
from Numeric_Loops import Clear_Elements, Prefix_Sum

class Numeric_Loop_Baselines(unittest.TestCase):
    def test_Clear_Elements(self):
        for Input, Expected in (([], []), ([4], [0]), ([3, -2, 5], [0, 0, 0])):
            with self.subTest(Input=Input.copy()):
                self.assertIs(Clear_Elements(Input), Input)
                self.assertEqual(Input, Expected)

    def test_Prefix_Sum(self):
        for Input, Expected in (([], []), ([4], [4]), ([3, -2, 5], [3, 1, 6])):
            with self.subTest(Input=Input.copy()):
                self.assertIs(Prefix_Sum(Input), Input)
                self.assertEqual(Input, Expected)
