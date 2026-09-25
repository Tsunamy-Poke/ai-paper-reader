"""阅读卡生成与追问：检索相关分块后调用 LLM，回答带页码出处。"""
import io
import json
import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import HTMLResponse, Response

from ..db import get_conn
from ..services import llm, summarizer

router = APIRouter(prefix="/papers/{paper_id}", tags=["chat"])


def _save_highlights(conn, paper_id: int, card: dict):
    """把阅读卡四要素沉淀到 highlights，供后续读取复用（省 AI 额度）。"""
    if card.get("summary"):
        conn.execute(
            "INSERT INTO highlights (paper_id, type, content) VALUES (?, 'summary', ?)",
            (paper_id, card["summary"]),
        )
    for o in card.get("outline", []):
        conn.execute(
            "INSERT INTO highlights (paper_id, type, content) VALUES (?, 'outline', ?)",
            (paper_id, o),
        )
    for term in card.get("terms", []):
        conn.execute(
            "INSERT INTO highlights (paper_id, type, content) VALUES (?, 'term', ?)",
            (paper_id, json.dumps(term, ensure_ascii=False)),
        )
    for c in card.get("conclusions", []):
        conn.execute(
            "INSERT INTO highlights (paper_id, type, content) VALUES (?, 'conclusion', ?)",
            (paper_id, c),
        )


def _get_or_generate_card(conn, paper_id: int) -> tuple[dict, bool]:
    """返回 (阅读卡, 是否重新调用了 AI)。缓存四要素齐全则直接复用，不消耗额度。"""
    hl = conn.execute("SELECT * FROM highlights WHERE paper_id = ?", (paper_id,)).fetchall()
    types = {h["type"] for h in hl}
    if hl and {"summary", "outline", "term", "conclusion"} <= types:
        card = {
            "summary": next((h["content"] for h in hl if h["type"] == "summary"), ""),
            "outline": [h["content"] for h in hl if h["type"] == "outline"],
            "terms": [json.loads(h["content"]) for h in hl if h["type"] == "term"],
            "conclusions": [h["content"] for h in hl if h["type"] == "conclusion"],
        }
        return card, False

    rows = conn.execute(
        "SELECT * FROM chunks WHERE paper_id = ? ORDER BY chunk_index", (paper_id,)
    ).fetchall()
    if not rows:
        return {}, False
    card = summarizer.generate_reading_card([dict(r) for r in rows])
    _save_highlights(conn, paper_id, card)
    conn.commit()
    return card, True


@router.get("/reading-card")
def reading_card(paper_id: int):
    conn = get_conn()
    card, _ = _get_or_generate_card(conn, paper_id)
    conn.close()
    if not card:
        raise HTTPException(404, "论文不存在或无可生成内容")
    return card


@router.post("/ask")
def ask(paper_id: int, body: dict = Body(...)):
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "question 必填")
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM chunks WHERE paper_id = ? ORDER BY chunk_index", (paper_id,)
    ).fetchall()
    if not rows:
        conn.close()
        raise HTTPException(404, "论文不存在")

    # 简单相关度检索：问题中的词在分块中出现的次数，取 Top 3
    tokens = [t for t in re.split(r"\W+", question) if len(t) >= 2]
    scored = []
    for r in rows:
        score = sum(r["content"].count(t) for t in tokens)
        if score > 0:
            scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [r for _, r in scored[:3]] or list(rows[:3])

    context = "\n\n".join(f"[第{r['page']}页]\n{r['content']}" for r in top)
    answer = llm.chat([
        {"role": "system", "content": "你是学术阅读助手。基于用户提供的论文片段回答；信息不足时明确说明，并尽量标注来源页码。"},
        {"role": "user", "content": f"论文相关片段：\n{context}\n\n问题：{question}"},
    ])
    conn.execute(
        "INSERT INTO questions (paper_id, question, answer) VALUES (?, ?, ?)",
        (paper_id, question, answer),
    )
    conn.commit()
    conn.close()
    return {"question": question, "answer": answer}


@router.get("/export")
def export_paper(paper_id: int, format: str = "html"):
    """导出阅读卡：format=html（默认，浏览器打开可打印）| format=pdf（直接下载 PDF 文件）。"""
    conn = get_conn()
    paper = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not paper:
        conn.close()
        raise HTTPException(404, "论文不存在")

    # 与阅读卡共用缓存：四要素齐全则直接复用，不重复调用 AI
    card, _ = _get_or_generate_card(conn, paper_id)
    conn.close()

    if format.lower() == "pdf":
        buf = _render_card_pdf(dict(paper), card)
        filename = quote(f"阅读卡-{paper['title'][:20]}.pdf")
        return Response(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )

    return HTMLResponse(_render_card_html(dict(paper), card))


def _render_card_html(paper: dict, card: dict) -> str:
    """渲染自包含 HTML 阅读卡（可浏览器打印/保存为 PDF）。"""
    summary = card.get("summary") or "（暂无摘要）"
    outline = card.get("outline") or []
    terms = card.get("terms") or []
    conclusions = card.get("conclusions") or []

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>阅读卡 - {paper["title"]}</title>
<style>
  body {{ font-family: "PingFang SC","Microsoft YaHei",sans-serif; max-width: 720px; margin: 40px auto; padding: 0 24px; color: #1f2937; }}
  h1 {{ font-size: 22px; }}
  .meta {{ color: #6b7280; font-size: 13px; margin-bottom: 28px; }}
  h2 {{ font-size: 16px; border-left: 4px solid #2563eb; padding-left: 10px; margin-top: 28px; }}
  p, li {{ line-height: 1.7; font-size: 14px; }}
  .term {{ font-weight: 600; }}
  footer {{ margin-top: 40px; color: #9ca3af; font-size: 12px; border-top: 1px solid #e5e7eb; padding-top: 12px; }}
</style>
</head>
<body>
<h1>{paper["title"]}</h1>
<div class="meta">由 AI 论文阅读助手生成 · {paper["created_at"]}</div>

<h2>一句话摘要</h2>
<p>{summary}</p>

<h2>章节大纲</h2>
<ol>
  {"".join(f"<li>{o}</li>" for o in outline)}
</ol>

<h2>术语解释</h2>
<ul>
  {"".join(f'<li><span class="term">{t.get("term", "")}</span> — {t.get("explanation", "")}</li>' for t in terms)}
</ul>

<h2>核心结论</h2>
<ul>
  {"".join(f"<li>{c}</li>" for c in conclusions)}
</ul>

<footer>仅供个人阅读辅助，请尊重原论文版权。</footer>
</body>
</html>"""


def _render_card_pdf(paper: dict, card: dict) -> bytes:
    """用 PyMuPDF Story 渲染多页 A4 PDF（原生支持中文，自动分页）。"""
    import pymupdf as fitz

    summary = card.get("summary") or "（暂无摘要）"
    outline = card.get("outline") or []
    terms = card.get("terms") or []
    conclusions = card.get("conclusions") or []

    outline_html = "".join(f"<li>{o}</li>" for o in outline)
    terms_html = "".join(
        f"<li><b>{t.get('term', '')}</b> — {t.get('explanation', '')}</li>" for t in terms
    )
    conclusions_html = "".join(f"<li>{c}</li>" for c in conclusions)

    html = f"""<h1 style="font-size:20px;">{paper["title"]}</h1>
<p style="font-size:12px;color:#888888;">由 AI 论文阅读助手生成 · {paper["created_at"]}</p>
<h2 style="font-size:15px;color:#1d4ed8;">一句话摘要</h2>
<p style="font-size:13px;line-height:1.7;">{summary}</p>
<h2 style="font-size:15px;color:#1d4ed8;">章节大纲</h2>
<ol>{outline_html}</ol>
<h2 style="font-size:15px;color:#1d4ed8;">术语解释</h2>
<ul>{terms_html}</ul>
<h2 style="font-size:15px;color:#1d4ed8;">核心结论</h2>
<ul>{conclusions_html}</ul>
<p style="font-size:10px;color:#aaaaaa;margin-top:24px;">仅供个人阅读辅助，请尊重原论文版权。</p>"""

    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    rect = fitz.paper_rect("a4")
    story = fitz.Story(html=html)
    while True:
        dev = writer.begin_page(rect)
        more, _ = story.place(rect)
        story.draw(dev)
        writer.end_page()
        if not more:
            break
    writer.close()
    return buf.getvalue()