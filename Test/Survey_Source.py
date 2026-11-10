from pathlib import Path

def _Separable(Vertical, Horizontal):
    return tuple(tuple(Y * X for X in Horizontal) for Y in Vertical)

def _Filters():
    Smooth = (1, 2, 1)
    Gaussian = (1, 4, 6, 4, 1)
    Slope = (-1, 0, 1)
    Bend = (1, -2, 1)
    return (
        ("Box_Mean", _Separable((1, 1, 1), (1, 1, 1)), 9),
        ("Gaussian_Fine", _Separable(Smooth, Smooth), 16),
        ("Gaussian_Wide", _Separable(Gaussian, Gaussian), 256),
        ("Sobel_East", _Separable(Smooth, Slope), 8),
        ("Sobel_South", _Separable(Slope, Smooth), 8),
        ("Scharr_East", _Separable((3, 10, 3), Slope), 32),
        ("Scharr_South", _Separable(Slope, (3, 10, 3)), 32),
        ("Axial_Laplacian", ((0, 1, 0), (1, -4, 1), (0, 1, 0)), 1),
        ("Diagonal_Laplacian", ((1, 0, 1), (0, -4, 0), (1, 0, 1)), 2),
        ("Isotropic_Laplacian", ((1, 4, 1), (4, -20, 4), (1, 4, 1)), 6),
        ("Ridge_East", _Separable(Smooth, Bend), 4),
        ("Ridge_South", _Separable(Bend, Smooth), 4),
        ("Mixed_Curvature", _Separable(Slope, Slope), 4),
        ("Cross_Curvature", _Separable(Bend, Bend), 1),
        ("Wide_Slope_East", _Separable(Gaussian, (-1, -2, 0, 2, 1)), 128),
        ("Wide_Slope_South", _Separable((-1, -2, 0, 2, 1), Gaussian), 128),
        ("Fourth_Difference_East", _Separable(Smooth, (1, -4, 6, -4, 1)), 4),
        ("Fourth_Difference_South", _Separable((1, -4, 6, -4, 1), Smooth), 4),
        ("Unsharp_Response", ((-1, -2, -1), (-2, 28, -2), (-1, -2, -1)), 16),
        ("Diamond_Mean", ((0, 0, 1, 0, 0), (0, 1, 1, 1, 0), (1, 1, 1, 1, 1), (0, 1, 1, 1, 0), (0, 0, 1, 0, 0)), 13),
        ("Checkerboard_Contrast", _Separable((1, -1, 1, -1, 1), (1, -1, 0, 1, -1)), 10),
        ("Wide_Box_Mean", _Separable((1,) * 5, (1,) * 5), 25),
    )

def _Index(Name, Offset):
    if Offset < 0:
        return f"{Name} - {-Offset}"
    if Offset > 0:
        return f"{Name} + {Offset}"
    return Name

def _Stencil(Name, Weights, Divisor):
    Height, Width = len(Weights) // 2, len(Weights[0]) // 2
    Lines = [f"def {Name}(Frame, Valid, Missing):",
             "    if Frame.shape != Valid.shape:", '        raise ValueError("Validity shape differs from frame shape")',
             "    Rows, Columns = Frame.shape", "    Output = Numpy.full((Rows, Columns), Missing, dtype=Numpy.int64)",
             f"    for Row in range({Height}, Rows - {Height}):", f"        for Column in range({Width}, Columns - {Width}):",
             "            Total = 0"]
    for Y, Row in enumerate(Weights):
        for X, Weight in enumerate(Row):
            if Weight:
                Location = f"{_Index('Row', Y - Height)}, {_Index('Column', X - Width)}"
                Lines.extend([f"            if not Valid[{Location}]:", "                continue",
                              f"            Value = int(Frame[{Location}])", f"            Total += {Weight} * Value"])
    Lines.extend([f"            Output[Row, Column] = Total // {Divisor}", "    return Output"])
    return "\n".join(Lines)

def Write_Survey(File):
    Core = Path(__file__).with_name("Survey_Pipeline.py.in").read_text(encoding="utf-8").rstrip()
    Filters = _Filters()
    Sections = [Core, *(_Stencil(*Filter) for Filter in Filters)]
    Sections.append("Filter_Bank = (\n" + "\n".join(f"    ({Name!r}, {Name})," for Name, Weights, Divisor in Filters) + "\n)")
    Source = "\n\n".join(Sections) + "\n"
    if not 1000 <= len(Source.splitlines()) <= 2000:
        raise ValueError("Survey stress fixture must contain 1,000 to 2,000 lines")
    File.write_text(Source, encoding="utf-8")
    return File
