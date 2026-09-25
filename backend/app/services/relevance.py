"""相关度打分：跨篇搜索与文献库按主题排序共用一套逻辑。

打分 = 命中次数 × (1 + 覆盖率)，其中覆盖率 = 命中的分块数 / 全部分块数。
命中越多分越高，命中分布越广（说明主题是全文性而非偶发）加成越多。
"""
import re

from ..db import get_conn


def tokenize(q: str) -> list[str]:
    """简单分词：英文单词 + 连续中文块（与 search.py 保持一致）。"""
    return [t for t in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", q.lower()) if t]


def score_papers(conn, tokens: list[str], include_zero: bool = False) -> list[dict]:
    """对全库论文打分，返回按相关度从高到低排序的结果。

    默认仅返回命中的论文；include_zero=True 时返回全库（未命中论文 score=0 排最后）。

    返回项: paper_id / title / score / hit_chunks / total_chunks / hits
    """
    rows = conn.execute(
        """SELECT c.paper_id, c.content, p.title
           FROM chunks c JOIN papers p ON p.id = c.paper_id
           ORDER BY c.paper_id, c.chunk_index"""
    ).fetchall()

    papers: dict[int, dict] = {}
    for r in rows:
        pid = r["paper_id"]
        if pid not in papers:
            papers[pid] = {"paper_id": pid, "title": r["title"], "chunks": []}
        papers[pid]["chunks"].append(r["content"])

    results = []
    zero_papers = []  # 未命中论文（include_zero=True 时追加到末尾）
    for pid, p in papers.items():
        hits = 0
        hit_chunks = 0
        for content in p["chunks"]:
            cnt = sum(content.lower().count(t) for t in tokens)
            if cnt:
                hit_chunks += 1
                hits += cnt
        total = len(p["chunks"])
        item = {
            "paper_id": pid,
            "title": p["title"],
            "score": 0.0,
            "hits": hits,
            "hit_chunks": hit_chunks,
            "total_chunks": total,
        }
        if hits == 0:
            zero_papers.append(item)
            continue
        coverage = hit_chunks / total if total else 0.0
        item["score"] = round(hits * (1 + coverage), 2)
        results.append(item)
    results.sort(key=lambda x: x["score"], reverse=True)
    if include_zero:
        results.extend(zero_papers)
    return results


if __name__ == "__main__":
    # 快速自测：python -m app.services.relevance
    conn = get_conn()
    for t in (["transformer"], ["深度学习"], ["attention"]):
        print(t, "->", [r["title"] for r in score_papers(conn, t)][:5])
    conn.close()
