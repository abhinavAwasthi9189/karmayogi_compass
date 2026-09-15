from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, CompetencyProfile
from app.schemas.course import RecommendationResponse, CourseOut, CourseModulesResponse, CourseModuleOut
from app.api.deps import get_current_user
from app.services.skillgap_service import compute_skill_gaps
from app.services.recommendation_service import recommend_courses
from app.adapters.factory import get_igot_adapter
from app.adapters.mock_dataset_loader import load_rag_corpus

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/course/{external_id}", response_model=CourseOut)
async def get_course(external_id: str, current_user: User = Depends(get_current_user)):
    adapter = get_igot_adapter()
    course = await adapter.get_course_by_id(external_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseOut(**course)


@router.get("/course/{external_id}/modules", response_model=CourseModulesResponse)
async def get_course_modules(external_id: str, current_user: User = Depends(get_current_user)):
    """Real per-module learning content for this course, sourced from
    mock/rag_learning_corpus_flat.csv. Returns an empty module list (not a
    404) for courses outside the mock dataset -- the course itself may still
    be valid, it just has no detailed module content bundled yet."""
    adapter = get_igot_adapter()
    course = await adapter.get_course_by_id(external_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    rows = [r for r in load_rag_corpus() if r["course_id"] == external_id]
    rows.sort(key=lambda r: r["module_no"])
    modules = [
        CourseModuleOut(
            module_no=r["module_no"],
            module_title=r["module_title"],
            study_material=r["study_material"],
            module_learning_outcome=r["module_learning_outcome"],
        )
        for r in rows
    ]
    return CourseModulesResponse(course_id=external_id, course_title=course["title"], modules=modules)


@router.get("/{user_id}/learning-course", response_model=CourseOut)
async def get_learning_course(
    user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    """The single course the Learning page should open by default: the real,
    mock-dataset course (with actual module content) for the user's biggest
    gap domain if one exists, otherwise their top overall recommendation.
    Keeps recommend_courses()'s ordering (used by Dashboard/Path) untouched --
    this is a separate, Learning-page-specific pick so the built-in
    curated fixtures don't crowd out the richer mock content by default."""
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another user's recommendations")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = session.exec(select(CompetencyProfile).where(CompetencyProfile.user_id == user_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Competency profile not found")

    gaps = compute_skill_gaps(session, user, profile)
    adapter = get_igot_adapter()

    top_domain = gaps[0]["domain"] if gaps else None
    if top_domain:
        domain_courses = await adapter.get_courses(domain=top_domain, limit=50)
        corpus_course = next((c for c in domain_courses if c["source"] == "Sample Karmayogi Learning Content"), None)
        if corpus_course:
            return CourseOut(**corpus_course)

    fallback = await recommend_courses(adapter, gaps, limit=1)
    if fallback:
        return CourseOut(**fallback[0])
    raise HTTPException(status_code=404, detail="No course available")


@router.get("/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another user's recommendations")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = session.exec(select(CompetencyProfile).where(CompetencyProfile.user_id == user_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Competency profile not found")

    gaps = compute_skill_gaps(session, user, profile)
    adapter = get_igot_adapter()
    courses = await recommend_courses(adapter, gaps)

    return RecommendationResponse(
        user_id=user_id,
        based_on_gaps=[g["domain"] for g in gaps if g["gap"] > 0],
        courses=[CourseOut(**c) for c in courses],
    )
