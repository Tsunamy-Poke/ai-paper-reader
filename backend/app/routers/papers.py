"""论文上传与文献库管理：上传(即用即清 PDF) / 列表 / 详情 / 删除。"""
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from .. import config
from ..db import get_conn
from ..services import pdf_parser, chunker

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), source_note: str = Form("")):
    """上传 PDF → 抽取文本 → 入库（仅文本）→ 清理 PDF 本体（方案 A）。"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")
    Path(config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    tmp = Path(config.UPLOAD_DIR) / f"{uuid.uuid4().hex}.pdf"
    try:
        with open(tmp, "wb") as f:
            f.write(await file.read())
        parsed = pdf_parser.extract_text(str(tmp))
        if not parsed["raw_text"].strip():
            raise HTTPException(400, "无法从 PDF 提取文本（可能是扫描件/图片型 PDF，暂不支持）")
        title = pdf_parser.guess_title(parsed["pages"])
        chunks = chunker.split_pages_into_chunks(parsed["pages"])

        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO papers (title, source_note, raw_text) VALUES (?, ?, ?)",
            (title, source_note, parsed["raw_text"]),
        )
        paper_id = cur.lastrowid
        for c in chunks:
            conn.execute(
                "INSERT INTO chunks (paper_id, chunk_index, content, page) VALUES (?, ?, ?, ?)",
                (paper_id, c["chunk_index"], c["content"], c["page"]),
            )
        conn.commit()
        conn.close()
        return {"id": paper_id, "title": title, "pages": len(parsed["pages"]), "chunks": len(chunks), "source_note": source_note}
    finally:
        tmp.unlink(missing_ok=True)  # 解析后即清理，不常驻


@router.get("")
def list_papers():
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.id, p.title, p.authors, p.created_at,
               (SELECT COUNT(*) FROM chunks c WHERE c.paper_id = p.id) AS chunk_count
        FROM papers p ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/{paper_id}")
def get_paper(paper_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "论文不存在")
    chunk_count = conn.execute("SELECT COUNT(*) FROM chunks WHERE paper_id = ?", (paper_id,)).fetchone()[0]
    conn.close()
    data = dict(row)
    data["chunk_count"] = chunk_count
    return data


@router.delete("/{paper_id}")
def delete_paper(paper_id: int):
    conn = get_conn()
    cur = conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "论文不存在")
    return {"deleted": paper_id}