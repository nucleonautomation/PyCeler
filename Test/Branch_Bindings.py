def Choose(Flag, Other, First, Second, Output, Events, Callback):
    if Flag:
        Source = First
        Offset = 1
    else:
        Source = Second
        Offset = 2
    Events.append("before")
    Callback(Source, Output, Events)
    for Index in range(len(Output)):
        Output[Index] = Source[Index] + Offset
    Events.append("after")
    Callback(Source, Output, Events)
    return Output

def Nested(Flag, Other, First, Second, Output, Events, Callback):
    if Flag:
        if Other:
            Source, Offset = First, 1
        else:
            Source, Offset = Second, 2
    else:
        if Other:
            Source, Offset = Second, 3
        else:
            Source, Offset = First, 4
    Events.append("before")
    Callback(Source, Output, Events)
    for Index in range(len(Output)):
        Output[Index] = Source[Index] + Offset
    Events.append("after")
    Callback(Source, Output, Events)
    return Output

def Annotated(Flag, Other, First, Second, Output, Events, Callback):
    if Flag:
        Source: object = First
        Offset: int = 1
    else:
        Source: object = Second
        Offset: int = 2
    Events.append("before")
    Callback(Source, Output, Events)
    for Index in range(len(Output)):
        Output[Index] = Source[Index] + Offset
    Events.append("after")
    Callback(Source, Output, Events)
    return Output

class Processor:
    def Choose(self, Flag, Other, First, Second, Output, Events, Callback):
        if Flag:
            Source, Offset = First, 1
        else:
            Source, Offset = Second, 2
        Events.append("before")
        Callback(Source, Output, Events)
        for Index in range(len(Output)):
            Output[Index] = Source[Index] + Offset
        Events.append("after")
        Callback(Source, Output, Events)
        return Output

def Partial(Flag, Other, First, Second, Output, Events, Callback):
    if Flag:
        Source = First
    Events.append("before")
    for Index in range(len(Output)):
        Output[Index] = Source[Index] + 1
    Events.append("after")
    return Output

def Annotation_Only(Flag, Other, First, Second, Output, Events, Callback):
    if Flag:
        Source: object
    else:
        Source: object
    Events.append("before")
    for Index in range(len(Output)):
        Output[Index] = Source[Index] + 1
    Events.append("after")
    return Output

def Walrus_Only(Flag, Other, First, Second, Output, Events, Callback):
    if Flag:
        Temporary = False and (Source := First)
    else:
        Temporary = False and (Source := Second)
    Events.append("before")
    for Index in range(len(Output)):
        Output[Index] = Source[Index] + 1
    Events.append("after")
    return Output

def Returning_Branch(Flag, Other, First, Second, Output, Events, Callback):
    if Flag:
        return Output
    else:
        Source = First
    Events.append("before")
    for Index in range(len(Output)):
        Output[Index] = Source[Index] + 1
    Events.append("after")
    return Output
