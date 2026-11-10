def Clipped_Median(Input, Output):
    Height, Width = Input.shape
    for Row in range(Height):
        for Column in range(Width):
            Values = []
            for Y in range(max(0, Row - 1), min(Height, Row + 2)):
                for X in range(max(0, Column - 1), min(Width, Column + 2)):
                    Values.append(int(Input[Y, X]))
            Values.sort()
            Output[Row, Column] = Values[len(Values) // 2]
    return Output

def Channel_Distance(Red, Green, Blue, Output, Target_Red, Target_Green, Target_Blue):
    for Index in range(len(Output)):
        Delta_Red = Red[Index] - Target_Red
        Delta_Green = Green[Index] - Target_Green
        Delta_Blue = Blue[Index] - Target_Blue
        Output[Index] = Delta_Red * Delta_Red + Delta_Green * Delta_Green + Delta_Blue * Delta_Blue
    return Output
