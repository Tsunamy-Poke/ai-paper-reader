"""跨篇搜索：FTS5 全文索引 + LIKE 兜底（中文更稳），按论文聚合返回相关段落。"""
import re

from fastapi import APIRouter, HTTPException, Query

from ..db import get_conn

router = APIRouter(prefix="/search", tags=["search"])


def _tokenize(q: str) -> list[str]:
    """简单分词：英文单词 + 连续中文块。"""
    return [t for t in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", q.lower()) if t]


def _snippet(text: str, token: str, radius: int = 70) -> str:
    idx = text.lower().find(token.lower())
    if idx == -1:
        return text[:160]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(token) + radius)
    s = text[start:end].strip()
    return ("…" if start > 0 else "") + s + ("…" if end < len(text) else "")


@router.get("")
def search(q: str = Query(..., min_length=1)):
    conn = get_conn()
    tokens = _tokenize(q)
    if not tokens:
        conn.close()
        raise HTTPException(400, "搜索词无效")

    # LIKE 兜底检索（对中文连续文本稳定），每篇最多保留 3 段
    agg: dict[int, dict] = {}
    for t in tokens:
        rows = conn.execute(
            """SELECT c.id AS chunk_id, c.paper_id, c.content, c.page, p.title
               FROM chunks c JOIN papers p ON p.id = c.paper_id
               WHERE c.content LIKE ?""",
            (f"%{t}%",),
        ).fetchall()
        for r in rows:
            pid = r["paper_id"]
            if pid not in agg:
                agg[pid] = {"paper_id": pid, "title": r["title"], "matches": []}
            if len(agg[pid]["matches"]) < 3:
                agg[pid]["matches"].append({
                    "chunk_id": r["chunk_id"],
                    "page": r["page"],
                    "snippet": _snippet(r["content"], t),
                })
    conn.close()
    return list(agg.values())