from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session, select
from typing import Optional

from app.database import get_session
from app.models import User, CompetencyProfile, CompetencyPassport, Assessment
from app.schemas.quiz import (
    QuizGenerateResponse, QuizQuestion, QuizOption, QuizSubmitRequest, QuizSubmitResponse,
)
from app.api.deps import get_current_user
from app.services.skillgap_service import compute_skill_gaps
from app.services.passport_service import grade_assessment, update_profile_and_passport
from app.services.quiz_service import (
    generate_gap_weighted_quiz, generate_gap_weighted_quiz_from_bank, generate_gap_weighted_quiz_from_corpus,
)
from app.adapters import mock_dataset_loader
from app.config import get_settings
from app.services.llm_client import describe_llm_error

router = APIRouter(prefix="/quiz", tags=["Quiz"])


def _clean_for_client(q: dict) -> QuizQuestion:
    """Strips the correct answer/explanation before the quiz is sent to the client."""
    return QuizQuestion(
        id=q["id"], domain=q["domain"], scenario=q["scenario"], question=q["question"],
        options=[QuizOption(**o) for o in q["options"]], citation=q["citation"], difficulty=q["difficulty"],
        correct_option=None, explanation=None,
    )


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(
    user_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot generate a quiz for another user")

    user = session.get(User, user_id)
    profile = session.exec(select(CompetencyProfile).where(CompetencyProfile.user_id == user_id)).first()
    if not user or not profile:
        raise HTTPException(status_code=404, detail="User or competency profile not found")

    gaps = compute_skill_gaps(session, user, profile)

    if file is not None:
        # PDF + LLM path: RAG-grounded questions generated from the uploaded document.
        if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF uploads are supported")
        pdf_bytes = await file.read()
        try:
            result = generate_gap_weighted_quiz(pdf_bytes, file.filename, gaps)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        source_document = file.filename
    else:
        result = None
        source_document = None
        # RAG-on-our-own-corpus path: only attempted once a real Gemini key is
        # configured. If the key is empty, or the call fails for any reason
        # (rate limit, bad model, network issue), we fall straight back to
        # the practice bank so the demo never breaks.
        settings = get_settings()
        if settings.GEMINI_API_KEY and mock_dataset_loader.course_corpus_available():
            try:
                result = generate_gap_weighted_quiz_from_corpus(gaps)
                source_document = "Seeded Learning Corpus (AI-generated, RAG)"
            except Exception as e:
                print(f"[quiz] Corpus RAG generation failed, falling back to bank: {describe_llm_error(e)}")       
        if result is None:
            if not mock_dataset_loader.practice_bank_available():
                raise HTTPException(
                    status_code=400,
                    detail="No reference document was provided, and no practice question bank is available. "
                            "Upload a PDF to generate an assessment.",
                )
            result = generate_gap_weighted_quiz_from_bank(gaps)
            source_document = "Practice Assessment Bank (mock dataset)"

        print(f"[quiz] Generated from: {source_document}")

    if not result["questions"]:
        raise HTTPException(status_code=422, detail="Could not generate any questions for this assessment")

    assessment = Assessment(
        user_id=user_id, questions=result["questions"], answers=[], source_document=source_document,
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)

    return QuizGenerateResponse(
        assessment_id=assessment.id,
        user_id=user_id,
        domain_weighting=result["domain_weighting"],
        questions=[_clean_for_client(q) for q in result["questions"]],
    )


@router.post("/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    payload: QuizSubmitRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    if current_user.role != "admin" and current_user.id != payload.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit a quiz for another user")

    assessment = session.get(Assessment, payload.assessment_id)
    if not assessment or assessment.user_id != payload.user_id:
        raise HTTPException(status_code=404, detail="Assessment not found for this user")
    if assessment.score is not None:
        raise HTTPException(status_code=400, detail="This assessment has already been submitted")

    grading = grade_assessment(assessment, payload.answers)
    assessment.answers = payload.answers
    assessment.score = grading["score"]
    assessment.domain_breakdown = grading["domain_breakdown"]
    session.add(assessment)
    session.commit()

    user = session.get(User, payload.user_id)
    profile = session.exec(select(CompetencyProfile).where(CompetencyProfile.user_id == payload.user_id)).first()
    passport = session.exec(select(CompetencyPassport).where(CompetencyPassport.user_id == payload.user_id)).first()

    update_result = update_profile_and_passport(
        session, user, profile, passport, assessment, grading["domain_breakdown"]
    )

    return QuizSubmitResponse(
        assessment_id=assessment.id,
        score=grading["score"],
        correct_count=grading["correct_count"],
        total_questions=grading["total"],
        domain_breakdown=grading["domain_breakdown"],
        updated_scores=update_result["updated_scores"],
        overall_readiness_index=update_result["overall_readiness_index"],
    )
