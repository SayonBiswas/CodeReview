import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, true
from sqlalchemy.orm import relationship
from database import Base

class ScanSession(Base):
    __tablename__ = "scan_sessions"

    #Using UUID strings for cross-database compatibility (SQLite/Postgres)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    language = Column(String, nullable=False)
    review_type = Column(String, nullable=False)
    overall_score = Column(Integer, nullable=True)

    #From Security Implementation 5.6: Store hash instead of raw code
    code_hash = Column(String, index=True, nullable=False)

    #Relationship (1:N)
    review_items = relationship("ReviewItem", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScanSession(id={self.id}, language{self.language}, score={self.overall_score})>"

class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    session_id = Column(String, ForeignKey("scan_session.id"), nullable=False)
    category = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    ai_explanation = Column(Text, nullable=True)
    fix_suggestion = Column(Text, nullable=True)
    status = Column(String, default="OPEN")

    # Relationship (N:1)
    session = relationship("ScanSession", back_populates="review_items")

    def __repr__(self):
        return f"<ReviewItem(id={self.id}, severity={self.severity}, status={self.status})>"


class MistakePattern(Base):
    __tablename__ = "mistake_patterns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    language = Column(String, nullable=False)
    pattern_type = Column(String, nullable=False)  # e.g., "hardcoded_api_key", "bare_except"
    occurrence_count = Column(Integer, default=1)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<MistakePattern(pattern={self.pattern_type}, count={self.occurrence_count})>"