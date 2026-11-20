import ast
import textwrap
# Test support/workload for integer operators, freshness and native admission.
Expressions = {
    "And": "(Initial + Index) & Operand",
    "Or": "(Initial + Index) | Operand",
    "Xor": "(Initial + Index) ^ Operand",
    "Left": "(Initial + Index) << Operand",
    "Right": "(Initial + Index) >> Operand",
    "Right_Literal": "Initial >> 1",
    "Power": "(Index % 3) ** Operand",
    "Negate": "-Initial",
    "Invert": "~Initial",
    "Positive_Fresh": "+(Initial + Index)",
    "Conditional": "~Initial if Index % 2 else Initial ^ Operand",
    "Modulo_Fresh": "(~Initial) % Operand",
    "Negative_Cached": "-1",
}
Updates = {"Aug_And": "&=", "Aug_Or": "|=", "Aug_Xor": "^=", "Aug_Left": "<<=", "Aug_Right": ">>=", "Aug_Power": "**="}

def Corpus():
    Text, Names = "Module_Results = []\n", []
    Bodies = {Name: "Value = " + Expression + "\n" for Name, Expression in Expressions.items()}
    Bodies.update({Name: "Value = Index + 2\nValue " + Operator + " " + ("1" if Name == "Aug_Right" else "Operand") + "\n" for Name, Operator in Updates.items()})
    Bodies["Conditional_Xor"] = "Value = Initial + Index\nif Index % 2:\n    Value ^= Operand\nif Value % 7 == 0:\n    Value += Index\n"
    for Renamed in (False, True):
        for Kind, Body in Bodies.items():
            for Placement in ("Whole", "Region", "Nested"):
                Name = f"Compute_{Kind}_{Placement}_{int(Renamed)}"
                Names.append(Name)
                Header = f"def {Name}(Count, Initial, Operand):\n"
                Prelude = "Value = 0\nTotal = 0\nIndex = 0\n"
                Loop = "for Index in range(Count):\n" + textwrap.indent(Body + "Total += Value\n", "    ")
                if Placement == "Whole":
                    Work = Prelude + Loop + "return Value\n"
                elif Placement == "Region":
                    Work = Prelude + Loop + "return Value, Total, Index\n"
                else:
                    Work = Prelude + "Events = []\nfor Outer in range(2):\n" + textwrap.indent(Loop + "Events.append((Value, Total, Index))\n", "    ") + "return Events\n"
                Function = Header + textwrap.indent(Work, "    ")
                if Renamed:
                    Function = _Rename(Function)
                Text += Function + "\n"
            Module = "Initial = 19\nOperand = 2\nValue = 0\nTotal = 0\nIndex = 0\nCount = 17\n" + Loop + "Module_Results.append((Value, Total, Index))\n"
            Text += _Rename(Module) if Renamed else Module
    return Text, Names

def _Rename(Source):
    Tree = ast.parse(Source)
    Mapping = dict(Value="Term", Total="Sum", Index="Cursor")
    for Node in ast.walk(Tree):
        if isinstance(Node, ast.Name):
            Node.id = Mapping.get(Node.id, Node.id)
    return ast.unparse(Tree) + "\n"
