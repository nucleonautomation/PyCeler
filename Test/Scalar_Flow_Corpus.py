import ast
import textwrap

Bodies = {
    "Conditional": "Value = Index + 11 if Index % 2 else Index * 3 + 5\nTotal += Value\n",
    "Tuple": "Value, Other = (Index * Index + 5) % Modulus, Total % 101 + Index\nTotal += Value + Other\n",
    "Intermediate": "Value = Index\nValue += 11\nTotal += Value\n",
    "Cached": "Value = 0\nif Index % 2:\n    Value += Index + 1\nTotal += Value\n",
    "Branches": "if Index % 2:\n    Value = (Index ^ 23) + 1\nelse:\n    Value = (Index * 3 + 5) % Modulus\nTotal += Value\n",
    "Overwrite": "Value = Total\nif Index % 2:\n    Value = Index + 11\nelse:\n    Value = Total % 101 + 7\nTotal += Value\n",
}

def Corpus():
    Text = "Module_Results = []\n"
    Names = []
    for Renamed in (False, True):
        for Kind, Body in Bodies.items():
            Loop = "for Index in range(Begin, End, Stride):\n" + textwrap.indent(Body, "    ")
            for Placement in ("Direct", "For", "While", "Branch"):
                Name = f"Compute_{Kind}_{Placement}_{int(Renamed)}"
                Names.append(Name)
                Header = f"def {Name}(Begin, End, Stride, Initial, Modulus, Flag):\n"
                Prelude = "Events = []\nTotal = Initial\nValue = -17\nOther = -19\nIndex = -23\n"
                if Placement == "For":
                    Work = "for Outer in range(2):\n" + textwrap.indent("Events.append(('before', Outer, Total))\n" + Loop + "Events.append(('after', Outer, Total, Value, Other, Index))\n", "    ")
                elif Placement == "While":
                    Work = "Outer = 0\nwhile Outer < 2:\n" + textwrap.indent("Events.append(('before', Outer, Total))\n" + Loop + "Events.append(('after', Outer, Total, Value, Other, Index))\nOuter += 1\n", "    ")
                elif Placement == "Branch":
                    Prelude += "if Flag:\n    Bound = End\nelse:\n    Bound = End + 0\n"
                    Work = Loop.replace("range(Begin, End, Stride)", "range(Begin, Bound, Stride)")
                else:
                    Work = Loop
                Function = Header + textwrap.indent(Prelude + Work + "Events.append(('done', Total))\nreturn Total, Value, Other, Index, Events\n", "    ")
                if Renamed:
                    Function = Rename(Function)
                Text += Function + "\n"
            Module = "Begin = -3\nEnd = 257\nStride = 2\nTotal = 7\nModulus = 999983\nValue = -17\nOther = -19\nIndex = -23\n" + Loop
            Module += "Module_Results.append((Total, Value, Other, Index))\n"
            Text += Rename(Module) if Renamed else Module
    return Text, Names

def Rename(Source):
    class Names(ast.NodeTransformer):
        _Mapping = dict(Total="Accumulator", Value="Term", Other="Scratch", Index="Cursor")

        def visit_Name(self, Node):
            Node.id = self._Mapping.get(Node.id, Node.id)
            return Node
    return ast.unparse(Names().visit(ast.parse(Source))) + "\n"
