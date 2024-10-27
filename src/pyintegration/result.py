from dataclasses import dataclass
from dataclasses import field
from datetime import timedelta
from typing import List
from typing import Optional


@dataclass
class Result:
    return_value: int = 0
    stdout: List = field(default_factory=list)
    stderr: List = field(default_factory=list)
    timediff: timedelta = timedelta(0)
    command: Optional[str] = None

    def out(self) -> str:
        return "\n".join(self.stdout)

    def err(self) -> str:
        return "\n".join(self.stderr)

    def out_contains(self, needle: str) -> Optional[str]:
        for line in self.stdout:
            if needle in line:
                return line
        return None

    def all(self) -> str:
        return self.out() + "\n" + self.err()
