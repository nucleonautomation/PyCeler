from dataclasses import dataclass

@dataclass(frozen=True)
class _Loop_Diagnostic:
    Code: str
    Line: int
    Column: int
    End_Line: int
    End_Column: int
    Severity: str
    Message: str
    Suggestion: str

    def __getitem__(self, Key):
        return getattr(self, Key)

    def _As_Dict(self):
        return dict(Code=self.Code, Line=self.Line, Column=self.Column, End_Line=self.End_Line, End_Column=self.End_Column,
                    Severity=self.Severity, Message=self.Message, Suggestion=self.Suggestion)

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
    Diagnostics: tuple[_Loop_Diagnostic, ...] = ()
    Plan: object | None = None
