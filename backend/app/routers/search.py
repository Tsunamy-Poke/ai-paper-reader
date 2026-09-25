"""跨篇搜索：FTS5 全文索引 + LIKE 兜底（中文更稳），按论文聚合返回相关段落。

- 论文间按相关度分数排序（命中次数 × 覆盖率，见 services/relevance.py）
- 段落内按命中位置排序（命中靠前的段落优先展示）
- GET /search/rank?topic= 可按主题给全库论文排序
"""
import re

from fastapi import APIRouter, HTTPException, Query

from ..db import get_conn
from ..services import relevance

router = APIRouter(prefix="/search", tags=["search"])


def _tokenize(q: str) -> list[str]:
    """简单分词：英文单词 + 连续中文块。"""
    return relevance.tokenize(q)


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

    # 先算全库相关度分，决定论文展示顺序
    scored = relevance.score_papers(conn, tokens)
    pid_score = {p["paper_id"]: p["score"] for p in scored}

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
                pos = r["content"].lower().find(t.lower())
                agg[pid]["matches"].append({
                    "chunk_id": r["chunk_id"],
                    "page": r["page"],
                    "snippet": _snippet(r["content"], t),
                    "pos": pos if pos >= 0 else 10**9,  # 用于段落内排序
                })

    results = []
    for pid, item in agg.items():
        item["score"] = pid_score.get(pid, 0.0)
        item["matches"].sort(key=lambda m: m["pos"])  # 命中靠前的段落优先
        results.append(item)
    results.sort(key=lambda x: x["score"], reverse=True)  # 论文间按相关度降序
    conn.close()
    return results


@router.get("/rank")
def rank_papers(topic: str = Query(..., min_length=1)):
    """按主题给文献库全库排序：输入主题词，返回相关度从高到低的论文列表。"""
    conn = get_conn()
    tokens = _tokenize(topic)
    if not tokens:
        conn.close()
        raise HTTPException(400, "主题词无效")
    results = relevance.score_papers(conn, tokens)
    conn.close()
    return results
