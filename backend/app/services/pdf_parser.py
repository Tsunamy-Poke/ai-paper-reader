"""PDF 文本抽取：PyMuPDF 提取正文与页码映射。方案 A 只保留文本，PDF 即用即清。"""
try:
    import pymupdf as fitz  # PyMuPDF 1.28+ 推荐导入
except ImportError:
    import fitz  # 旧版兼容


def extract_text(pdf_path: str) -> dict:
    """返回 {"raw_text": str, "pages": [{"page": int, "text": str}]}"""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        pages.append({"page": i + 1, "text": text})
    raw_text = "\n\n".join(f"[第 {p['page']} 页]\n{p['text']}" for p in pages)
    doc.close()
    return {"raw_text": raw_text, "pages": pages}


def guess_title(pages: list[dict]) -> str:
    """从第一页顶部启发式取标题（MVP 简化：取第一页第一行非空文本）。"""
    first_text = pages[0]["text"] if pages else ""
    for line in first_text.splitlines():
        line = line.strip()
        if len(line) >= 4:
            return line[:200]
    return "未命名论文"