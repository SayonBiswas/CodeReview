import hashlib
import uuid
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, Depends, Header, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .database import engine, get_db, Base
from .models import ScanSession, ReviewItem, MistakePattern
from .schemas import (
    ScanRequest, ScanResponse, Finding, IssueStatusUpdate,
    SessionResponse, HistoryResponse, AnalyticsResponse, HealthResponse
)
from .auth import get_client_id, verify_admin_token, limiter, is_private_ip
from .reviewers.security_reviewer import SecurityReviewer
from .reviewers.quality_reviewer import QualityReviewer
from .reviewers.bug_reviewer import BugReviewer
from .reviewers.practices_reviewer import PracticesReviewer
from .reviewers.dep_reviewer import DepReviewer
from .aggregator import Aggregator
from .explainer import Explainer
from .report import ReportGenerator
from .config import settings

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CodeReview AI")

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT"],
    allow_headers=["Content-Type", "X-Client-ID", "Authorization"],
)

# Security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# Serve static files
import os
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Initialize components
security_reviewer = SecurityReviewer()
quality_reviewer = QualityReviewer()
bug_reviewer = BugReviewer()
practices_reviewer = PracticesReviewer()
dep_reviewer = DepReviewer()
aggregator = Aggregator()
explainer = Explainer()
report_generator = ReportGenerator()


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/health")
async def health_check():
    return HealthResponse(status="healthy", timestamp=datetime.now())


@app.post("/scan", response_model=ScanResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def scan_code(
    request: Request,
    scan_req: ScanRequest,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db)
):
    # Check for private/internal URLs
    if is_private_ip(scan_req.code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Private/internal URLs are not permitted"
        )

    # Compute code hash
    code_hash = hashlib.sha256(scan_req.code.encode()).hexdigest()

    # Select reviewers based on review type
    reviewers = []
    if scan_req.review_type in ["quick", "full", "security"]:
        reviewers.append(security_reviewer)
    if scan_req.review_type == "full":
        reviewers.append(quality_reviewer)
        reviewers.append(bug_reviewer)
        reviewers.append(practices_reviewer)
    if scan_req.review_type in ["full", "security"]:
        if scan_req.requirements:
            reviewers.append(dep_reviewer)

    # Run reviewers
    all_findings = []
    warnings = []
    for reviewer in reviewers:
        try:
            findings = reviewer.analyze(
                scan_req.code,
                scan_req.language,
                requirements=scan_req.requirements
            )
            all_findings.extend(findings)
        except Exception as e:
            warnings.append(f"{reviewer.category} reviewer failed: {str(e)}")

    # Convert to Finding dataclass format
    finding_objects = []
    for f in all_findings:
        finding_objects.append(Finding(
            rule_id=f.rule_id,
            category=f.category,
            severity=f.severity,
            line_no=f.line_no,
            title=f.title,
            description=f.description,
            fix=f.fix,
            ai_explanation=f.ai_explanation,
            fix_code=f.fix_code
        ))

    # Merge and sort findings
    merged_findings = aggregator.merge_findings([finding_objects])
    sorted_findings = aggregator.sort_findings(merged_findings)

    # Calculate score and grade
    score = aggregator.calculate_score(sorted_findings)
    grade = aggregator.calculate_grade(score)
    summary_counts = aggregator.get_summary_counts(sorted_findings)

    # AI explanations
    ai_status = "ok"
    try:
        findings_for_ai = aggregator.select_for_ai(sorted_findings, settings.MAX_AI_EXPLANATIONS_PER_SCAN)
        if findings_for_ai:
            sorted_findings = explainer.explain_findings(findings_for_ai, scan_req.language)
    except Exception as e:
        ai_status = "unavailable"
        warnings.append(f"AI explanation failed: {str(e)}")

    # Convert to Finding schema
    findings_response = []
    for f in sorted_findings:
        findings_response.append(Finding(
            rule_id=f.rule_id,
            category=f.category,
            severity=f.severity,
            line_no=f.line_no,
            title=f.title,
            description=f.description,
            fix=f.fix,
            ai_explanation=f.ai_explanation,
            fix_code=f.fix_code
        ))

    # Create session
    session = ScanSession(
        id=str(uuid.uuid4()),
        created_at=datetime.now(),
        language=scan_req.language,
        review_type=scan_req.review_type,
        overall_score=score,
        grade=grade,
        code_length=len(scan_req.code),
        code_hash=code_hash,
        client_id=client_id,
        parent_session_id=scan_req.parent_session_id
    )
    db.add(session)
    db.flush()

    # Create review items
    for f in findings_response:
        item = ReviewItem(
            id=str(uuid.uuid4()),
            session_id=session.id,
            category=f.category,
            severity=f.severity,
            line_number=f.line_no,
            title=f.title,
            description=f.description,
            ai_explanation=f.ai_explanation,
            fix_suggestion=f.fix,
            status="open",
            rule_id=f.rule_id
        )
        db.add(item)

    # Update mistake patterns - deduplicate within the same scan
    unique_patterns = {}
    for f in findings_response:
        pattern_type = f"{f.category}_{f.rule_id}"
        if pattern_type not in unique_patterns:
            unique_patterns[pattern_type] = 0
        unique_patterns[pattern_type] += 1

    for pattern_type, count in unique_patterns.items():
        existing = db.query(MistakePattern).filter(
            MistakePattern.client_id == client_id,
            MistakePattern.language == scan_req.language,
            MistakePattern.pattern_type == pattern_type
        ).first()

        if existing:
            existing.occurrence_count += count
            existing.last_seen = datetime.now()
        else:
            new_pattern = MistakePattern(
                id=str(uuid.uuid4()),
                client_id=client_id,
                language=scan_req.language,
                pattern_type=pattern_type,
                occurrence_count=count,
                last_seen=datetime.now()
            )
            db.add(new_pattern)

    db.commit()

    # Comparison if parent session
    comparison = None
    if scan_req.parent_session_id:
        parent_session = db.query(ScanSession).filter(
            ScanSession.id == scan_req.parent_session_id
        ).first()
        if parent_session:
            parent_items = db.query(ReviewItem).filter(
                ReviewItem.session_id == parent_session.id
            ).all()
            old_findings = [Finding(
                rule_id=i.rule_id or "",
                category=i.category,
                severity=i.severity,
                line_no=i.line_number,
                title=i.title,
                description=i.description,
                fix=i.fix_suggestion or ""
            ) for i in parent_items]
            comparison = aggregator.compare_sessions(old_findings, findings_response)

    return ScanResponse(
        session_id=session.id,
        overall_score=score,
        grade=grade,
        summary_counts=summary_counts,
        findings=findings_response,
        warnings=warnings,
        ai_status=ai_status,
        comparison=comparison
    )


@app.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db)
):
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid session ID")

    session = db.query(ScanSession).filter(ScanSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    items = db.query(ReviewItem).filter(ReviewItem.session_id == session_id).all()
    findings = [Finding(
        rule_id=i.rule_id or "",
        category=i.category,
        severity=i.severity,
        line_no=i.line_number,
        title=i.title,
        description=i.description,
        fix=i.fix_suggestion or "",
        ai_explanation=i.ai_explanation or "",
        fix_code=""
    ) for i in items]

    return SessionResponse(
        id=session.id,
        created_at=session.created_at,
        language=session.language,
        review_type=session.review_type,
        overall_score=session.overall_score,
        grade=session.grade,
        code_length=session.code_length,
        findings=findings
    )


@app.get("/sessions")
async def list_sessions(
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db)
):
    sessions = db.query(ScanSession).filter(
        ScanSession.client_id == client_id
    ).order_by(ScanSession.created_at.desc()).limit(20).all()

    return [{"id": s.id, "created_at": s.created_at, "language": s.language,
            "score": s.overall_score, "grade": s.grade} for s in sessions]


@app.patch("/issue/{item_id}")
async def update_issue_status(
    item_id: str,
    update: IssueStatusUpdate,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db)
):
    try:
        uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid issue ID")

    item = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    session = db.query(ScanSession).filter(ScanSession.id == item.session_id).first()
    if session.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    item.status = update.status
    db.commit()

    return {"status": "updated"}


@app.get("/report/{session_id}/pdf")
@limiter.limit("10/hour")
async def download_report(
    request: Request,
    session_id: str,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db)
):
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid session ID")

    session = db.query(ScanSession).filter(ScanSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    items = db.query(ReviewItem).filter(ReviewItem.session_id == session_id).all()
    findings = [Finding(
        rule_id=i.rule_id or "",
        category=i.category,
        severity=i.severity,
        line_no=i.line_number,
        title=i.title,
        description=i.description,
        fix=i.fix_suggestion or "",
        ai_explanation=i.ai_explanation or "",
        fix_code=""
    ) for i in items]

    pdf_bytes = report_generator.generate_pdf(
        session_id=session.id,
        overall_score=session.overall_score,
        grade=session.grade,
        language=session.language,
        review_type=session.review_type,
        findings=findings
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{session_id}.pdf"}
    )


@app.get("/history", response_model=HistoryResponse)
async def get_history(
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db)
):
    patterns = db.query(MistakePattern).filter(
        MistakePattern.client_id == client_id
    ).order_by(MistakePattern.occurrence_count.desc()).limit(10).all()

    patterns_data = [
        {
            "pattern_type": p.pattern_type,
            "language": p.language,
            "occurrence_count": p.occurrence_count,
            "last_seen": p.last_seen
        }
        for p in patterns
    ]

    return HistoryResponse(patterns=patterns_data)


@app.get("/admin/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    admin_verified: bool = Depends(verify_admin_token),
    db: Session = Depends(get_db)
):
    from sqlalchemy import func

    # Scans per day
    scans_per_day = db.query(
        func.date(ScanSession.created_at).label('date'),
        func.count(ScanSession.id).label('count')
    ).group_by(func.date(ScanSession.created_at)).all()
    scans_per_day_dict = {str(d): c for d, c in scans_per_day}

    # Grade distribution
    grade_dist = db.query(
        ScanSession.grade,
        func.count(ScanSession.id).label('count')
    ).group_by(ScanSession.grade).all()
    grade_distribution = {g: c for g, c in grade_dist}

    # Top categories
    top_categories = db.query(
        ReviewItem.category,
        func.count(ReviewItem.id).label('count')
    ).group_by(ReviewItem.category).order_by(func.count(ReviewItem.id).desc()).limit(5).all()
    top_categories_list = [{"category": c, "count": cnt} for c, cnt in top_categories]

    return AnalyticsResponse(
        scans_per_day=scans_per_day_dict,
        grade_distribution=grade_distribution,
        top_categories=top_categories_list
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
