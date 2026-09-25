"""文档文本抽取：PDF（PyMuPDF）/ Word（python-docx）/ TXT。方案 A 只保留文本，原件即用即清。"""
try:
    import pymupdf as fitz  # PyMuPDF 1.28+ 推荐导入
except ImportError:
    import fitz  # 旧版兼容


def extract_text(pdf_path: str) -> dict:
    """PDF → {"raw_text": str, "pages": [{"page": int, "text": str}]}"""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        pages.append({"page": i + 1, "text": text})
    raw_text = "\n\n".join(f"[第 {p['page']} 页]\n{p['text']}" for p in pages)
    doc.close()
    return {"raw_text": raw_text, "pages": pages}


def extract_docx(docx_path: str) -> dict:
    """Word .docx → 抽取段落与表格文本；无页码概念，用段落序号近似页码。"""
    from docx import Document

    doc = Document(docx_path)
    texts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                texts.append(" | ".join(cells))
    pages = [{"page": i + 1, "text": t} for i, t in enumerate(texts)]
    raw_text = "\n\n".join(f"[第 {p['page']} 段]\n{p['text']}" for p in pages)
    return {"raw_text": raw_text, "pages": pages}


def extract_txt(txt_path: str) -> dict:
    """纯文本 → 按行抽取；用行号近似页码。"""
    from pathlib import Path

    try:
        text = Path(txt_path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = Path(txt_path).read_text(encoding="gbk", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pages = [{"page": i + 1, "text": line} for i, line in enumerate(lines)]
    raw_text = "\n\n".join(f"[第 {p['page']} 行]\n{p['text']}" for p in pages)
    return {"raw_text": raw_text, "pages": pages}


def guess_title(pages: list[dict]) -> str:
    """从第一页顶部启发式取标题（MVP 简化：取第一页第一行非空文本）。"""
    first_text = pages[0]["text"] if pages else ""
    for line in first_text.splitlines():
        line = line.strip()
        if len(line) >= 4:
            return line[:200]
    return "未命名论文"