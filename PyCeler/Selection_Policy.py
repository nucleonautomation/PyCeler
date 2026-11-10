import math
import statistics
import os

def _Candidate_Code(Name):
    if Name in ("Python", "Serial", "OpenMP", "Optimized", "Tiled"):
        return {"Python": 0, "Serial": 1, "OpenMP": 2, "Optimized": 3, "Tiled": 4}[Name]
    Family, Value = Name.split("_")
    return (100 if Family == "OpenMP" else 10000) + int(Value)

def _Candidate_Name(Code):
    if Code in (0, 1, 2, 3, 4):
        return {0: "Python", 1: "Serial", 2: "OpenMP", 3: "Optimized", 4: "Tiled"}[Code]
    if 102 <= Code <= 164:
        return "OpenMP_" + str(Code - 100)
    if Code - 10000 in (8, 16, 32, 64, 128):
        return "Tiled_" + str(Code - 10000)
    raise ValueError("Unknown candidate code")

def _Candidate_Order(Names):
    Order = {"Serial": 1, "Optimized": 2, "Tiled": 3, "OpenMP": 4}
    return sorted((Name for Name in Names if Name != "Python"), key=lambda Name: (Order[Name.split("_")[0]], _Candidate_Code(Name)))

def _Normalize_Tuning(Tuning):
    if Tuning is None or Tuning is False or type(Tuning) is dict and not Tuning:
        return {}
    if Tuning is True:
        Tuning = dict(Threads=[Value for Value in (2, 4) if Value <= (os.cpu_count() or 1)], Tiles=[16, 32, 64], Budget_Seconds=20)
    if type(Tuning) is not dict or set(Tuning) - {"Threads", "Tiles", "Budget_Seconds"}:
        raise ValueError("Tuning must be True, False or a Threads/Tiles/Budget_Seconds mapping")
    Result = {}
    for Name, Allowed in (("Threads", range(2, 65)), ("Tiles", (8, 16, 32, 64, 128))):
        Values = Tuning.get(Name, [])
        if not isinstance(Values, (list, tuple)) or len(Values) > 4 or any(type(Value) is not int or Value not in Allowed for Value in Values):
            raise ValueError(f"Tuning {Name} must contain at most four supported integer values")
        Result[Name] = sorted(set(Values))
    Budget = Tuning.get("Budget_Seconds", 20)
    if type(Budget) not in (int, float) or not math.isfinite(Budget) or not 1 <= Budget <= 60:
        raise ValueError("Tuning Budget_Seconds must be between 1 and 60 per function")
    Result["Budget_Seconds"] = Budget
    return Result

def _Explain_Selection(Item):
    Decisions = []
    for Case in Item.get("Cases", []):
        Winner = Case.get("Dispatch_Winner", "Python")
        Timing = Case["Timings"].get(Winner)
        Python = Case["Timings"].get("Python")
        Decisions.append(dict(Dtype=Case["Key"], Size=Case["Size"], Shape=Case.get("Shape"), Winner=Winner,
                              Speedup=Python["Median_Ns"] / Timing["Median_Ns"] if Python and Timing else None,
                              Reason="Validated complete-call measurements support promotion in this workload band" if Winner != "Python" else "No eligible candidate established the required gain across this band and its holdouts"))
    Item["Summary"] = dict(Function=Item["Function"], Transformations=Item.get("Transformations", []),
                           Baseline="Python", Timing_Includes="Function call, runtime checks, dispatch and kernel", Decisions=Decisions,
                           Skipped_Candidates=Item.get("Skipped_Candidates", {}), Fallback_Reason=Item.get("Reason"))

def _Promotes(Case, Previous, Candidate, Gain):
    if Case["Validation"].get(Candidate) != "valid" or Previous not in Case["Timings"] or Candidate not in Case["Timings"]:
        return False
    Left = Case["Timings"][Previous]["Samples_Ns"]
    Right = Case["Timings"][Candidate]["Samples_Ns"]
    return bool(Left and len(Left) == len(Right) and statistics.median(Left) >= Gain * statistics.median(Right) and
                sum(A >= Gain * B for A, B in zip(Left, Right)) >= math.ceil(0.75 * len(Right)))

def _Selection_Table(Cases, Gain, Bounded=False):
    Table = {}
    Invalid = {Name for Case in Cases for Name, Status in Case["Validation"].items() if Status.startswith("invalid")}
    for Key in sorted({Case["Key"] for Case in Cases}):
        Group = [Case for Case in Cases if Case["Key"] == Key]
        Bounds = sorted({Case["Size"] for Case in Group if not Case.get("Holdout", False)})
        Bands = []
        for Index, Low in enumerate(Bounds):
            High = Bounds[Index + 1] if Index + 1 < len(Bounds) else math.inf
            Evidence = [Case for Case in Group if Low <= Case["Size"] < High]
            Winner = "Python"
            for Candidate in _Candidate_Order({Name for Case in Evidence for Name in Case["Validation"]}):
                if Evidence and Candidate not in Invalid and all(_Promotes(Case, Winner, Candidate, Gain) for Case in Evidence):
                    Winner = Candidate
            Bands.append((Low, _Candidate_Code(Winner)))
        if Bounded and Group:
            Bands.append((max(Case["Size"] for Case in Group) + 1, 0))
        Table[Key] = list(reversed(Bands))
    return Table
