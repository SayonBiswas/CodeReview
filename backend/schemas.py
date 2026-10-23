from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class ScanRequest(BaseModel):
    code: str = Field(..., min_length=10, max_length=50000, description="Source code to analyze")
    language: str = Field(..., pattern="^(python|javascript|html)$", description="Programming language")
    review_type: str = Field(..., pattern="^(quick|full|security)$", description="Type of review")
    requirements: Optional[str] = Field(None, max_length=10000, description="Optional requirements.txt content")
    parent_session_id: Optional[str] = Field(None, description="Previous session ID for comparison")

    @field_validator('code')
    @classmethod
    def code_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code cannot be whitespace only")
        return v.replace('\x00', '')


class Finding(BaseModel):
    rule_id: str
    category: str
    severity: str
    line_no: Optional[int]
    title: str
    description: str
    fix: str
    ai_explanation: str = ""
    fix_code: str = ""


class ComparisonResult(BaseModel):
    resolved: List[str]
    still_open: List[str]
    new: List[str]


class ScanResponse(BaseModel):
    session_id: str
    overall_score: int
    grade: str
    summary_counts: Dict[str, int]
    findings: List[Finding]
    warnings: List[str]
    ai_status: str
    comparison: Optional[ComparisonResult] = None


class IssueStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|acknowledged|in_progress|resolved|ignored)$")


class SessionResponse(BaseModel):
    id: str
    created_at: datetime
    language: str
    review_type: str
    overall_score: int
    grade: str
    code_length: int
    findings: List[Finding]


class HistoryResponse(BaseModel):
    patterns: List[Dict[str, Any]]


class AnalyticsResponse(BaseModel):
    scans_per_day: Dict[str, int]
    grade_distribution: Dict[str, int]
    top_categories: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
