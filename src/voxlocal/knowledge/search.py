"""Meeting retrieval and local Q&A (RAG) assistant."""

import logging

import httpx

from voxlocal.knowledge.database import KnowledgeDB, SearchResult

logger = logging.getLogger(__name__)


def ask_meetings(
    question: str,
    db: KnowledgeDB,
    ollama_url: str = "http://localhost:11434",
    model_name: str = "llama3.2",
    limit: int = 8,
) -> str:
    """Retrieve relevant dialogue segments and synthesize an answer using local LLM."""
    results: list[SearchResult] = db.search(question, limit=limit)

    if not results:
        return f"No matching dialogue or meeting notes found for query: '{question}'."

    # Build context from search results
    context_blocks = []
    for r in results:
        m = int(r.start_sec // 60)
        s = int(r.start_sec % 60)
        context_blocks.append(
            f"[{r.date}] Meeting: '{r.title}' at {m:02d}:{s:02d}\n"
            f"{r.speaker}: \"{r.text}\""
        )

    context_str = "\n\n".join(context_blocks)

    prompt = f"""You are VoxLocal Assistant. Answer the user's question accurately using ONLY the meeting dialogue excerpts provided below.
Cite the meeting title and date in your answer. If the excerpts do not contain the answer, state that clearly.

Meeting Context:
{context_str}

User Question: {question}

Answer:"""

    # Attempt query to local Ollama
    answer = _query_ollama_qa(prompt, ollama_url=ollama_url, model_name=model_name)
    if answer:
        return answer.strip()

    # Fallback to direct excerpt reporting if LLM is offline
    lines = [
        f"Answer to: '{question}' (Offline Extractive Retrieval):",
        "",
        "Relevant excerpts found in past meetings:",
    ]
    for r in results[:5]:
        m = int(r.start_sec // 60)
        s = int(r.start_sec % 60)
        lines.append(f"- **{r.title}** ({r.date} [{m:02d}:{s:02d}]): {r.speaker}: \"{r.text}\"")

    return "\n".join(lines)


def _query_ollama_qa(prompt: str, ollama_url: str, model_name: str) -> str | None:
    """Query local Ollama endpoint."""
    url = f"{ollama_url.rstrip('/')}/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
        },
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                return data.get("response", "")
    except Exception as exc:
        logger.debug("Failed querying Ollama for QA: %s", exc)

    return None
