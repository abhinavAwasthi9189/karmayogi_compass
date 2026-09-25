"""Orchestrates gap-weighted, RAG-grounded quiz generation:
1. weight questions per domain by that domain's competency gap size
2. retrieve the most relevant PDF passages per domain (RAG)
3. prompt the LLM for strict-JSON MoSPI workplace scenario questions with page citations

A second, LLM-free path (generate_gap_weighted_quiz_from_bank) builds the same
shape of quiz straight from the pre-authored mock/practice_assessments.csv
question bank, so quizzes work even without a PDF upload or an LLM API key.
"""
from typing import List, Dict, Any
from app.services.rag_service import RAGSession
from app.services.llm_client import complete_json
from app.adapters import mock_dataset_loader
from app.services import corpus_rag

TOTAL_QUESTIONS = 10

SYSTEM_PROMPT = """You are an expert assessment designer for MoSPI (Ministry of Statistics and
Programme Implementation), India, writing scenario-based quiz questions for government officials
on the iGOT Karmayogi platform. Every question MUST:
- Present a realistic MoSPI/official-statistics workplace scenario (survey operations, data
  compilation, field supervision, digital governance, or office management) grounded ONLY in the
  provided source excerpts.
- Test practical judgement, not rote recall.
- Have exactly 4 options labelled A, B, C, D with exactly one correct option.
- Cite the page number of the excerpt the question is grounded in.
Respond with ONLY a JSON array, no prose, no markdown fences. Each array element:
{"scenario": str, "question": str, "options": {"A": str, "B": str, "C": str, "D": str},
"correct_option": "A"|"B"|"C"|"D", "explanation": str, "citation_page": int, "difficulty": "easy"|"medium"|"hard"}
"""


def compute_domain_weighting(gaps: List[Dict[str, Any]], total: int = TOTAL_QUESTIONS) -> Dict[str, int]:
    """Allocates quiz questions across domains proportional to each domain's gap size.
    Domains with zero gap are skipped; if every gap is zero, weight evenly across all domains."""
    positive = [g for g in gaps if g["gap"] > 0]
    pool = positive or gaps
    gap_sum = sum(g["gap"] for g in pool) or len(pool)

    weighting: Dict[str, int] = {}
    for g in pool:
        share = (g["gap"] / gap_sum) if gap_sum else (1 / len(pool))
        weighting[g["domain"]] = max(1, round(share * total))

    # trim/pad to hit exactly `total`
    domains = list(weighting.keys())
    while sum(weighting.values()) > total:
        biggest = max(domains, key=lambda d: weighting[d])
        if weighting[biggest] > 1:
            weighting[biggest] -= 1
        else:
            break
    while sum(weighting.values()) < total:
        weighting[domains[0]] += 1
    return weighting


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    return "\n\n".join(f"[Page {c['page']}]: {c['text']}" for c in chunks)


def generate_questions_for_domain(rag: RAGSession, domain: str, count: int, source_name: str) -> List[Dict[str, Any]]:
    chunks = rag.retrieve(domain=domain, k=max(4, count))
    if not chunks:
        return []
    context = _build_context(chunks)
    user_prompt = (
        f"Domain focus: {domain}\n"
        f"Number of questions required: {count}\n\n"
        f"Source excerpts (from an uploaded reference document):\n{context}\n\n"
        f"Generate exactly {count} MoSPI workplace scenario question(s) for the '{domain}' "
        f"competency domain, grounded strictly in the excerpts above."
    )
    raw_questions = complete_json(SYSTEM_PROMPT, user_prompt)
    if not isinstance(raw_questions, list):
        raw_questions = [raw_questions]

    questions = []
    for rq in raw_questions[:count]:
        questions.append({
            "domain": domain,
            "scenario": rq.get("scenario", ""),
            "question": rq.get("question", ""),
            "options": [{"label": k, "text": v} for k, v in rq.get("options", {}).items()],
            "correct_option": rq.get("correct_option"),
            "explanation": rq.get("explanation", ""),
            "citation": f"{source_name}, p.{rq.get('citation_page', chunks[0]['page'])}",
            "difficulty": rq.get("difficulty", "medium"),
        })
    return questions


def generate_gap_weighted_quiz(pdf_bytes: bytes, source_name: str, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    rag = RAGSession()
    rag.ingest(pdf_bytes)

    weighting = compute_domain_weighting(gaps)
    all_questions: List[Dict[str, Any]] = []
    for domain, count in weighting.items():
        all_questions.extend(generate_questions_for_domain(rag, domain, count, source_name))

    # assign sequential ids
    for idx, q in enumerate(all_questions, start=1):
        q["id"] = idx

    return {"domain_weighting": weighting, "questions": all_questions}


def _bank_question_to_internal(q: Dict[str, Any], domain: str) -> Dict[str, Any]:
    return {
        "domain": domain,
        "scenario": q["scenario"],
        "question": q["question"],
        "options": [{"label": k, "text": v} for k, v in q["options"].items()],
        "correct_option": q["correct_option"],
        "explanation": q["explanation"],
        "citation": f"Practice Bank \u2014 {q['course_id']} ({q['assessment_id']})",
        "difficulty": q.get("difficulty", "medium"),
    }


def _bank_available_count(domain: str, exclude_keys: set) -> int:
    return len([
        q for q in mock_dataset_loader.load_practice_assessments()
        if q["domain"] == domain and (q["scenario"], q["question"]) not in exclude_keys
    ])


def generate_gap_weighted_quiz_from_bank(gaps: List[Dict[str, Any]], total: int = TOTAL_QUESTIONS) -> Dict[str, Any]:
    """Builds a gap-weighted quiz entirely from mock/practice_assessments.csv --
    no PDF upload and no LLM call required. Same allocation logic as the
    PDF/LLM path (compute_domain_weighting), but sources real, pre-authored
    questions instead of generating them. If a domain's target count exceeds
    what the bank has available, the shortfall is reallocated to other
    domains that still have spare questions rather than failing outright."""
    if not mock_dataset_loader.practice_bank_available():
        return {"domain_weighting": {}, "questions": []}

    weighting = compute_domain_weighting(gaps, total)
    exclude_keys: set = set()
    final_weighting: Dict[str, int] = {}
    all_questions: List[Dict[str, Any]] = []
    shortfall = 0

    for domain, count in weighting.items():
        available = _bank_available_count(domain, exclude_keys)
        take = min(count, available)
        picked = mock_dataset_loader.pick_bank_questions(domain, take, exclude_keys)
        exclude_keys.update((q["scenario"], q["question"]) for q in picked)
        final_weighting[domain] = take
        shortfall += count - take
        all_questions.extend(_bank_question_to_internal(q, domain) for q in picked)

    # Reallocate any shortfall to domains that still have spare bank questions.
    if shortfall > 0:
        for domain in list(final_weighting.keys()):
            if shortfall <= 0:
                break
            available = _bank_available_count(domain, exclude_keys)
            extra = min(shortfall, available)
            if extra <= 0:
                continue
            picked = mock_dataset_loader.pick_bank_questions(domain, extra, exclude_keys)
            exclude_keys.update((q["scenario"], q["question"]) for q in picked)
            final_weighting[domain] += extra
            shortfall -= extra
            all_questions.extend(_bank_question_to_internal(q, domain) for q in picked)

    for idx, q in enumerate(all_questions, start=1):
        q["id"] = idx

    return {"domain_weighting": {k: v for k, v in final_weighting.items() if v > 0}, "questions": all_questions}


SYSTEM_PROMPT_CORPUS = """You are an expert assessment designer for MoSPI (Ministry of Statistics and
Programme Implementation), India, writing scenario-based quiz questions for government officials
on the iGOT Karmayogi platform. Every question MUST:
- Present a realistic MoSPI/official-statistics workplace scenario (survey operations, data
  compilation, field supervision, digital governance, or office management) grounded ONLY in the
  provided course excerpts.
- Test practical judgement, not rote recall.
- Have exactly 4 options labelled A, B, C, D with exactly one correct option.
- Cite which numbered excerpt below the question is grounded in.
Respond with ONLY a JSON array, no prose, no markdown fences. Each array element:
{"scenario": str, "question": str, "options": {"A": str, "B": str, "C": str, "D": str},
"correct_option": "A"|"B"|"C"|"D", "explanation": str, "citation_index": int, "difficulty": "easy"|"medium"|"hard"}
"""


def _build_corpus_context(chunks: List[Dict[str, Any]]) -> str:
    return "\n\n".join(f"[Excerpt {i+1}]: {c['text']}" for i, c in enumerate(chunks))


def generate_questions_for_domain_from_corpus(
    domain: str, count: int, gap_info: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    extra_query = ""
    history_line = ""
    if gap_info:
        extra_query = f"current score {gap_info.get('current')}, required {gap_info.get('required')}"
        history_line = (
            f"\nLearner history for this domain: current score {gap_info.get('current')}/100, "
            f"required {gap_info.get('required')}/100, gap {gap_info.get('gap')}. "
            f"Skew the scenario toward closing this specific gap.\n"
        )
    chunks = corpus_rag.retrieve(domain=domain, extra_query=extra_query, k=max(4, count))
    if not chunks:
        return []
    context = _build_corpus_context(chunks)
    user_prompt = (
        f"Domain focus: {domain}\n"
        f"Number of questions required: {count}\n"
        f"{history_line}\n"
        f"Source excerpts (from our seeded learning corpus):\n{context}\n\n"
        f"Generate exactly {count} MoSPI workplace scenario question(s) for the '{domain}' "
        f"competency domain, grounded strictly in the excerpts above."
    )
    raw_questions = complete_json(SYSTEM_PROMPT_CORPUS, user_prompt)
    if not isinstance(raw_questions, list):
        raw_questions = [raw_questions]

    questions = []
    for rq in raw_questions[:count]:
        idx = rq.get("citation_index", 1)
        idx = idx - 1 if isinstance(idx, int) and 1 <= idx <= len(chunks) else 0
        questions.append({
            "domain": domain,
            "scenario": rq.get("scenario", ""),
            "question": rq.get("question", ""),
            "options": [{"label": k, "text": v} for k, v in rq.get("options", {}).items()],
            "correct_option": rq.get("correct_option"),
            "explanation": rq.get("explanation", ""),
            "citation": chunks[idx]["citation"],
            "difficulty": rq.get("difficulty", "medium"),
        })
    return questions


def generate_gap_weighted_quiz_from_corpus(gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """RAG-grounded quiz from our own seeded corpus. Requires a working LLM
    key. Callers must catch exceptions and fall back to
    generate_gap_weighted_quiz_from_bank if this raises."""
    weighting = compute_domain_weighting(gaps)
    gap_by_domain = {g["domain"]: g for g in gaps}
    all_questions: List[Dict[str, Any]] = []
    for domain, count in weighting.items():
        all_questions.extend(
            generate_questions_for_domain_from_corpus(domain, count, gap_by_domain.get(domain))
        )

    if not all_questions:
        raise ValueError("No questions could be generated from the seeded corpus")

    for idx, q in enumerate(all_questions, start=1):
        q["id"] = idx

    return {"domain_weighting": weighting, "questions": all_questions}
