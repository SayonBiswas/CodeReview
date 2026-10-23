from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Finding:
    rule_id: str
    category: str
    severity: str
    line_no: int
    title: str
    description: str
    fix: str
    ai_explanation: str = ""
    fix_code: str = ""


class Reviewer(ABC):
    @abstractmethod
    def analyze(self, code: str, language: str, **kwargs) -> List[Finding]:
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        pass
