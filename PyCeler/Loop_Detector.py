from dataclasses import dataclass

@dataclass(frozen=True)
class Loop_Finding:
    Function: str | None
    Line: int
    End_Line: int
    Indexed_Reads: tuple[str, ...]
    Indexed_Writes: tuple[str, ...]
    Classification: str
    Reason: str
    Change: str = "Keep original loop"
    Source: str = ""
    Cost_Score: float = 0.0
    Estimated_Iterations: int | None = None
    Nesting_Depth: int = 0
    Cost_Reason: str = ""
    Constraints: tuple[str, ...] = ()
    Transformations: tuple[str, ...] = ()
