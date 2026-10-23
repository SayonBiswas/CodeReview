import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from .database import Base

class ScanSession(Base):
    __tablename__ = "scan_sessions"

    # Using UUID strings for cross-database compatibility (SQLite/Postgres)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    language = Column(String, nullable=False)
    review_type = Column(String, nullable=False)
    overall_score = Column(Integer, nullable=True)
    grade = Column(String, nullable=True)
    code_length = Column(Integer, nullable=False)
    code_hash = Column(String, index=True, nullable=False)
    client_id = Column(String, index=True, nullable=False)
    parent_session_id = Column(String, ForeignKey("scan_sessions.id"), nullable=True)

    # Relationship (1:N)
    review_items = relationship("ReviewItem", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScanSession(id={self.id}, language={self.language}, score={self.overall_score})>"

class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    session_id = Column(String, ForeignKey("scan_sessions.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    ai_explanation = Column(Text, nullable=True)
    fix_suggestion = Column(Text, nullable=True)
    status = Column(String, default="open")
    rule_id = Column(String, nullable=True)

    # Relationship (N:1)
    session = relationship("ScanSession", back_populates="review_items")

    def __repr__(self):
        return f"<ReviewItem(id={self.id}, severity={self.severity}, status={self.status})>"

class MistakePattern(Base):
    __tablename__ = "mistake_patterns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    client_id = Column(String, index=True, nullable=False)
    language = Column(String, nullable=False)
    pattern_type = Column(String, nullable=False)  # e.g., "hardcoded_api_key", "bare_except"
    occurrence_count = Column(Integer, default=1)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index('idx_client_language_pattern', 'client_id', 'language', 'pattern_type', unique=True),
    )

    def __repr__(self):
        return f"<MistakePattern(pattern={self.pattern_type}, count={self.occurrence_count})>"