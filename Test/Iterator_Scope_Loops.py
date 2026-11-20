import math
# Test support/workload for iterator construction, target bindings and strict mismatch.
def Empty_Capture():
    Output = []
    def Run(Source: 'numpy.ndarray'):
        for Index in range(len(Source)):
            Output[Index] = math.sin(Source[Index])
        return 17
    del Output
    return Run

def Both(Source: 'numpy.ndarray', Output: 'numpy.ndarray'):
    Marker = 0
    for Index in range(len(Source)):
        Value = math.sin(Source[Index])
        for Repeat in range(12):
            Value = math.sin(Value + 0.125)
        Output[Index] = Value
    return Output

def Zip_Rows(Sources, Outputs):
    for Values, Destinations in zip(Sources, Outputs):
        for Column in range(len(Values)):
            Destinations[Column] = math.sin(Values[Column]) + math.cos(Values[Column])
    return Outputs

def Array_Rows(Sources: 'numpy.ndarray', Outputs: 'numpy.ndarray'):
    for Values, Destinations in zip(Sources, Outputs):
        for Column in range(len(Values)):
            Destinations[Column] = math.sin(Values[Column]) + math.cos(Values[Column])
    return Outputs

def Enumerated_Rows(Sources: 'numpy.ndarray', Outputs: 'numpy.ndarray'):
    for Row, Values in enumerate(Sources):
        Destinations = Outputs[Row]
        for Column in range(len(Values)):
            Destinations[Column] = math.sin(Values[Column]) + math.cos(Values[Column])
    return Outputs
