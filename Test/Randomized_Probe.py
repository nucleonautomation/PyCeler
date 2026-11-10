import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path
import numpy as np

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name + ".Structural_Loops", File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Cases(Seed):
    Random = random.Random(Seed)
    Dtypes = (np.int8, np.uint8, np.int16, np.uint16, np.int32, np.int64, np.float32, np.float64)
    Families = (("Fused_Maps", 2, ()), ("Local_Values", 2, ()), ("Repeated_Scores", 2, (1,)),
                ("Invariant_Scale", 1, (2, -3)), ("Versioned_Reads", 2, ()), ("Temporary_Pipeline", 1, (2, 1)),
                ("Augmented_Outputs", 2, ()), ("Augmented_Locals", 1, ()), ("Sequential_Updates", 1, ()),
                ("Independent_Updates", 1, ()))
    for Dtype in Dtypes:
        for Variant in range(12):
            Size = Random.choice((0, 1, 2, 7, 17, 63))
            Values = np.array([Random.randrange(0, 9) if np.dtype(Dtype).kind == "u" else Random.randrange(-8, 9) for Index in range(Size * 2)], dtype=Dtype)
            if Size and Variant in (0, 1):
                Limit = np.iinfo(Dtype) if np.dtype(Dtype).kind in "iu" else np.finfo(Dtype)
                Values[0] = Limit.min if Variant == 0 else Limit.max
            if Size and np.dtype(Dtype).kind == "f" and Variant in (2, 3, 4, 5):
                Values[0] = {2: -0.0, 3: np.nan, 4: np.inf, 5: 0.125}[Variant]
            for Name, Count, Tail in Families:
                Input = Values[::2] if Variant == 6 else Values[:Size].copy()
                Outputs = [np.full_like(Input, 3) for Index in range(Count)]
                if Variant == 7:
                    Outputs[0] = Input
                if Variant == 8:
                    Input, Outputs[0] = Values[:Size], Values[1:Size + 1]
                if Variant == 9:
                    Outputs[0].setflags(write=False)
                if Variant == 10:
                    Outputs[0] = Outputs[0][:-1]
                if Variant == 11:
                    Input = Input.astype(Input.dtype.newbyteorder())
                Extra = (0, -3) if Name == "Invariant_Scale" and Variant == 2 else Tail
                yield Name, (Input, *Outputs, *Extra), dict(Dtype=np.dtype(Dtype).str, Variant=Variant, Size=Size)

def _Run(Binary, Seed, Only=None):
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    from PyCeler.Selection_Worker import _Observe
    Reference = _Load("Reference", Root / "Test" / "Structural_Loops.py")
    Native = _Load("Native", Binary)
    Count = 0
    for Index, (Name, Args, Metadata) in enumerate(_Cases(Seed)):
        if Only is not None and Index != Only:
            continue
        Expected = _Observe(getattr(Reference, Name), Args)[0]
        Actual = _Observe(getattr(Native, Name), Args)[0]
        if Actual != Expected:
            Folder = Root / "Test_Run" / "Randomized_Failures"
            Folder.mkdir(parents=True, exist_ok=True)
            Report = dict(Seed=Seed, Case=Index, Function=Name, Metadata=Metadata, Expected=repr(Expected), Actual=repr(Actual),
                          Reproduce=f'python -B Test/Randomized_Probe.py --binary "{Binary}" --seed {Seed} --case {Index}')
            File = Folder / f"Seed_{Seed}_Case_{Index}.json"
            File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
            raise AssertionError(f"Differential mismatch; reproducible case saved to {File}")
        Count += 1
    if Count == 0:
        raise ValueError("No randomized cases selected")
    print(json.dumps(dict(Status="passed", Seed=Seed, Cases=Count)))

if __name__ == "__main__":
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--binary", type=Path, required=True)
    Parser.add_argument("--seed", type=int, default=73129)
    Parser.add_argument("--case", type=int)
    Options = Parser.parse_args()
    _Run(Options.binary, Options.seed, Options.case)
