import random

def _Expression(Generator, Depth):
    if not Depth or Generator.randrange(5) == 0:
        return Generator.choice(("Index", "Value", "1", "7", "(-3)"))
    if Generator.randrange(6) == 0:
        return "(-" + _Expression(Generator, Depth - 1) + ")"
    Operator = Generator.choice(("+", "-", "*", "%", "//"))
    Left = _Expression(Generator, Depth - 1)
    Right = Generator.choice(("Divisor", "7", "(-7)", "(Index - 3)")) if Operator in ("%", "//") else _Expression(Generator, Depth - 1)
    return f"({Left} {Operator} {Right})"

def _Programs():
    Generator = random.Random(20261110)
    Programs = []
    Ranges = ("range(Count)", "range(-Count, Count, 2)", "range(Count, -Count, -3)")
    for Number in range(24):
        Expression = _Expression(Generator, 3)
        Iteration = Ranges[Number % len(Ranges)]
        Initial = Generator.choice((0, 1, 7))
        Programs.append(f"def Sum_{Number}(Count, Value, Divisor):\n    Total = {Initial}\n    for Index in {Iteration}:\n        Total += {Expression}\n    return Total\n")
    for Number in range(12):
        Expression = _Expression(Generator, 3)
        if Number % 2:
            Programs.append(f"def Ordered_{Number}(Count, Value, Divisor):\n    Total = Value + 0\n    for Index in {Ranges[Number % len(Ranges)]}:\n        Scratch = {Expression}\n        if Index % 2 == 0:\n            Total += Scratch\n        else:\n            Total -= Scratch\n    return Total\n")
        else:
            Programs.append(f"def Ordered_{Number}(Count, Value, Divisor):\n    Total = 0\n    Index = 0\n    while Index < Count:\n        Index += 1\n        if Index % 3 == 0:\n            continue\n        Total += {Expression}\n        if Index > 17:\n            break\n    return Total\n")
    for Number in range(12):
        Expression = Generator.choice(("Value % Divisor", "Index % Divisor", "(Value + Index) % Divisor"))
        Statement = f"Result = {Expression}" if Number % 2 else "Result %= Divisor"
        Programs.append(f"def Aliases_{Number}(Count, Value, Divisor):\n    Result = Value\n    Copy = Result\n    Index = -1\n    for Index in range(Count):\n        {Statement}\n        Copy = Result\n    return Result, Copy, Value, Index, Result is Copy, Result is Value, Result is Index\n")
    for Number in range(6):
        Expression = _Expression(Generator, 2)
        Period = Generator.choice((3, 5, 7))
        Programs.append(f"def Callback_{Number}(Count, Value, Divisor, Events):\n    Total = Value + 0\n    for Index in range(Count):\n        Total += {Expression}\n        if Index % {Period} == 0 and Index != 0:\n            Events.append((Index, Total))\n    return Total, Events\n")
    return "\n".join(Programs)
