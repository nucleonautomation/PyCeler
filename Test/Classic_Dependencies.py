def Scatter_Best(Cells, Scores, Best, Winners):
    for I in range(len(Cells)):
        Cell = Cells[I]
        if Scores[I] > Best[Cell]:
            Best[Cell] = Scores[I]
            Winners[Cell] = I
    return Winners

def Ordered_Moments(Values, Labels, Totals):
    for I in range(len(Values)):
        Totals[Labels[I]] += float(Values[I])
    return Totals

def Median_Depth(Depth, Output, Radius):
    Rows, Columns = Depth.shape
    for Y in range(Rows):
        for X in range(Columns):
            if Depth[Y, X] == 0:
                Output[Y, X] = 0
                continue
            Samples = []
            for V in range(max(0, Y - Radius), min(Rows, Y + Radius + 1)):
                for U in range(max(0, X - Radius), min(Columns, X + Radius + 1)):
                    Value = int(Depth[V, U])
                    if Value:
                        Samples.append(Value)
            Samples.sort()
            Half = len(Samples) // 2
            Output[Y, X] = Samples[Half] if len(Samples) % 2 else round((Samples[Half - 1] + Samples[Half]) / 2)
    return Output
