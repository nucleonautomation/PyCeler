import math
# Test support/workload for array metadata without copying or reading object data.
def Shape_List(Template, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sin(Index * 0.01) + len(Template) * 0.125
    return Output

def Shape_Path(Template, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sin(Index * 0.01) + len(Template[Index]) * 0.125
    return Output

def Shape_Array(Template: 'numpy.ndarray', Output: 'numpy.ndarray'):
    for Index in range(len(Output)):
        Output[Index] = math.sin(Index * 0.01) + Template.shape[1] * 0.125
    return Output

def Shape_Bound(Template, Output):
    for Index in range(len(Template)):
        Output[Index] = math.sin(Index * 0.01)
    return Output
