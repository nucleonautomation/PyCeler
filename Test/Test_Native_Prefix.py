import unittest
from PyCeler.Math_Maps import _Native_Prefix
# Regression checks for collision-safe source prefix assembly.
class Native_Prefix(unittest.TestCase):
    def test_Renames_Native_Names_Without_Changing_User_Literals(self):
        Source = 'cdef double _Pyceler_Value = _Pyceler_Input\nLabel = "user _Pyceler_literal"\n# user _Pyceler_comment\ncdef extern from "_Pyceler_header.h":\n    int _Pyceler_External\ncdef extern from *:\n    """\n    static int _Pyceler_Embedded = 1;\n    """\n'
        Expected = 'cdef double _Pyceler_XValue = _Pyceler_XInput\nLabel = "user _Pyceler_literal"\n# user _Pyceler_comment\ncdef extern from "_Pyceler_header.h":\n    int _Pyceler_XExternal\ncdef extern from *:\n    """\n    static int _Pyceler_XEmbedded = 1;\n    """\n'
        self.assertEqual(_Native_Prefix(Source, '_Pyceler_X'), Expected)
        self.assertIs(_Native_Prefix(Source, '_Pyceler_'), Source)

    def test_Large_Unicode_And_Multiline_Source_Preserves_Offsets(self):
        for Newline in ('\n', '\r\n'):
            Lines = ['Label = "λ漢字 _Pyceler_literal"']
            Expected = Lines[:]
            for Index in range(2000):
                Line = f'cdef double _Pyceler_Value_{Index} = _Pyceler_Input_{Index} + _Pyceler_Offset'
                Lines.append(Line)
                Expected.append(Line.replace('_Pyceler_', '_Pyceler_X'))
            self.assertEqual(_Native_Prefix(Newline.join(Lines), '_Pyceler_X'), Newline.join(Expected))
