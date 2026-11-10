import sys

_Isolation_Limit = 64 * 1024 * 1024

class _Probe_Resource(ValueError):
    pass

class _Fragmented_Input:
    def __init__(self, Size):
        self._Data = bytes(range(251)) * (Size // 251 + 1)
        self._Position = 0
        self._Requests = []

    def recv(self, Amount):
        self._Requests.append(Amount)
        End = self._Position + min(Amount, 113)
        Chunk = self._Data[self._Position:End]
        self._Position = End
        return Chunk

def _Array_Owner(Value):
    import numpy as Numpy
    if type(Value) is not Numpy.ndarray or Value.dtype.hasobject:
        raise ValueError("Selection supports plain numeric NumPy arrays")
    Owner = Value
    while isinstance(Owner.base, Numpy.ndarray):
        Owner = Owner.base
    if Owner.base is not None or not (Owner.flags.c_contiguous or Owner.flags.f_contiguous):
        raise ValueError("Selection cannot isolate this array's external storage")
    return Owner

def _Storage_Bytes(Args, Limit=_Isolation_Limit):
    Seen = set()
    Storage = set()
    Total = 0
    Pending = [Args]
    while Pending:
        Value = Pending.pop()
        if id(Value) in Seen:
            continue
        Seen.add(id(Value))
        if hasattr(Value, "dtype"):
            Owner = _Array_Owner(Value)
            if id(Owner) not in Storage:
                Storage.add(id(Owner))
                Total += Owner.nbytes
        elif type(Value) in (list, tuple, dict):
            Total += sys.getsizeof(Value)
            Pending.extend(Value.keys() if type(Value) is dict else ())
            Pending.extend(Value.values() if type(Value) is dict else Value)
        elif type(Value) is bytearray:
            Total += len(Value)
        elif isinstance(Value, _Fragmented_Input):
            Total += sys.getsizeof(Value) + sys.getsizeof(Value._Requests)
        elif type(Value) not in (int, float, bool, str, bytes, type(None)):
            raise ValueError("Selection inputs require arrays, bytearrays or plain scalar/container values")
        if Total > Limit:
            raise _Probe_Resource(f"Unique backing storage exceeds the {Limit}-byte isolation budget")
    return Total

def _Copy(Args, Limit=_Isolation_Limit):
    _Storage_Bytes(Args, Limit)
    Memo = {}
    Active = set()
    Readonly = []
    def _Duplicate(Value):
        if id(Value) in Memo:
            return Memo[id(Value)]
        if id(Value) in Active:
            raise ValueError("Selection cannot isolate a cycle through an immutable container")
        Active.add(id(Value))
        if isinstance(Value, _Fragmented_Input):
            Result = _Fragmented_Input(0)
            Result._Data = Value._Data
            Result._Position = Value._Position
            Result._Requests = Value._Requests.copy()
        elif type(Value) is bytearray:
            Result = Value.copy()
        elif hasattr(Value, "dtype"):
            import numpy as Numpy
            Owner = _Array_Owner(Value)
            Key = ("storage", id(Owner))
            if Key not in Memo:
                Memo[Key] = Numpy.ndarray(Owner.shape, dtype=Owner.dtype, strides=Owner.strides)
                Memo[Key][...] = Owner
                Memo[id(Owner)] = Memo[Key]
                if not Owner.flags.writeable:
                    Readonly.append(Memo[Key])
            Offset = Value.__array_interface__["data"][0] - Owner.__array_interface__["data"][0]
            Result = Memo[Key] if Value is Owner else Numpy.ndarray(Value.shape, dtype=Value.dtype, buffer=Memo[Key], offset=Offset, strides=Value.strides)
            if Value is not Owner and not Value.flags.writeable:
                Readonly.append(Result)
        elif type(Value) is list:
            Result = []
            Memo[id(Value)] = Result
            Result.extend(_Duplicate(Item) for Item in Value)
        elif type(Value) is tuple:
            Result = tuple(_Duplicate(Item) for Item in Value)
        elif type(Value) is dict:
            Result = {}
            Memo[id(Value)] = Result
            Result.update((_Duplicate(Key), _Duplicate(Item)) for Key, Item in Value.items())
        else:
            Result = Value
        Memo[id(Value)] = Result
        Active.remove(id(Value))
        return Result
    Result = _Duplicate(Args)
    for Value in Readonly:
        Value.setflags(write=False)
    return Result

def _Value(Value):
    import struct
    Memo = {}
    Nodes = []
    Storage = {}
    def _Visit(Item):
        if id(Item) in Memo:
            return Memo[id(Item)]
        Index = len(Nodes)
        Memo[id(Item)] = Index
        Nodes.append(None)
        if isinstance(Item, _Fragmented_Input):
            Record = (type(Item), Item._Data, Item._Position, _Visit(Item._Requests))
        elif type(Item) is bytearray:
            Record = (type(Item), bytes(Item))
        elif hasattr(Item, "dtype"):
            Owner = _Array_Owner(Item)
            Identity = Storage.setdefault(id(Owner), len(Storage))
            Offset = Item.__array_interface__["data"][0] - Owner.__array_interface__["data"][0]
            Record = (type(Item), Item.dtype.str, Item.shape, Item.strides, bool(Item.flags.writeable),
                      Identity, Offset, Item.tobytes(), _Visit(Item.base) if Item.base is not None else None)
        elif type(Item) is float:
            Record = (type(Item), struct.pack("!d", Item))
        elif type(Item) in (tuple, list):
            Record = (type(Item), tuple(_Visit(Child) for Child in Item))
        elif type(Item) is dict:
            Record = (type(Item), tuple((_Visit(Key), _Visit(Child)) for Key, Child in Item.items()))
        else:
            Record = (type(Item), Item)
        Nodes[Index] = Record
        return Index
    return _Visit(Value), tuple(Nodes)
