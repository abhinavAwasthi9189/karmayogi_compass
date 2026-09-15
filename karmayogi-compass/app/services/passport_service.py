"""Scores a submitted quiz, then propagates the result into the user's
CompetencyProfile scores and CompetencyPassport (readiness index + validated skills)."""
from datetime import datetime
from typing import Dict, Any, List
from sqlmodel import Session

from app.models import User, CompetencyProfile, CompetencyPassport, Assessment
from app.adapters.mock_data import DOMAINS, DOMAIN_LABELS
from app.services.skillgap_service import compute_skill_gaps, persist_gaps

MAX_BOOST_PER_DOMAIN = 8.0          # max score points a domain can gain from one assessment
VALIDATION_THRESHOLD = 0.7          # >=70% accuracy in a domain marks that skill "validated"

LABEL_TO_FIELD = {v: k for k, v in DOMAIN_LABELS.items()}


def grade_assessment(assessment: Assessment, answers: List[str]) -> Dict[str, Any]:
    total = len(assessment.questions)
    correct = 0
    domain_stats: Dict[str, Dict[str, int]] = {}

    for i, q in enumerate(assessment.questions):
        domain = q["domain"]
        domain_stats.setdefault(domain, {"correct": 0, "total": 0})
        domain_stats[domain]["total"] += 1
        submitted = answers[i] if i < len(answers) else None
        if submitted and submitted.strip().upper() == str(q.get("correct_option", "")).strip().upper():
            correct += 1
            domain_stats[domain]["correct"] += 1

    score = round((correct / total) * 100, 2) if total else 0.0
    domain_breakdown = {
        d: {"correct": s["correct"], "total": s["total"], "accuracy": round(s["correct"] / s["total"], 3)}
        for d, s in domain_stats.items()
    }
    return {"score": score, "correct_count": correct, "total": total, "domain_breakdown": domain_breakdown}


def update_profile_and_passport(
    session: Session, user: User, profile: CompetencyProfile, passport: CompetencyPassport,
    assessment: Assessment, domain_breakdown: Dict[str, Any],
) -> Dict[str, Any]:
    updated_scores: Dict[str, float] = {}
    newly_validated: List[Dict[str, Any]] = []

    for domain_label, stats in domain_breakdown.items():
        field = LABEL_TO_FIELD.get(domain_label)
        if not field:
            continue
        accuracy = stats["accuracy"]
        boost = accuracy * MAX_BOOST_PER_DOMAIN
        current = getattr(profile, field)
        new_score = min(round(current + boost, 2), 100.0)
        setattr(profile, field, new_score)
        updated_scores[domain_label] = new_score

        if accuracy >= VALIDATION_THRESHOLD:
            newly_validated.append({
                "domain": domain_label,
                "accuracy": accuracy,
                "assessment_id": assessment.id,
                "validated_on": datetime.utcnow().isoformat(),
            })

    session.add(profile)

    # recompute gaps against the freshly updated scores
    gaps = compute_skill_gaps(session, user, profile)
    persist_gaps(session, profile, gaps)

    passport.validated_skills = passport.validated_skills + newly_validated
    passport.overall_readiness_index = round(
        sum(getattr(profile, f) for f in DOMAINS) / len(DOMAINS), 2
    )
    passport.last_updated = datetime.utcnow()
    session.add(passport)
    session.commit()
    session.refresh(profile)
    session.refresh(passport)

    return {"updated_scores": updated_scores, "overall_readiness_index": passport.overall_readiness_index}
