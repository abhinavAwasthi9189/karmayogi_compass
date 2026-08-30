"""Orchestrates gap-weighted, RAG-grounded quiz generation:
1. weight questions per domain by that domain's competency gap size
2. retrieve the most relevant PDF passages per domain (RAG)
3. prompt the LLM for strict-JSON MoSPI workplace scenario questions with page citations
"""
from typing import List, Dict, Any
from app.services.rag_service import RAGSession
from app.services.llm_client import complete_json

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
