"""文本分块：按段落切块，控制每块字符量并记录页码，支撑追问与跨篇检索。"""

# 目标：每块约 1500 字符（约 500-700 token），块尾保留少量重叠
CHUNK_SIZE = 1500
OVERLAP = 150


def split_pages_into_chunks(pages: list[dict]) -> list[dict]:
    """pages: [{"page": int, "text": str}] → [{"chunk_index", "content", "page"}]"""
    chunks = []
    buf = ""
    buf_page = pages[0]["page"] if pages else 0
    idx = 0

    for p in pages:
        for para in _split_paragraphs(p["text"]):
            # 超长段落按字符硬切
            while len(para) > CHUNK_SIZE:
                piece = para[:CHUNK_SIZE]
                para = para[CHUNK_SIZE:]
                chunks.append({"chunk_index": idx, "content": piece, "page": p["page"]})
                idx += 1
            if buf and len(buf) + len(para) > CHUNK_SIZE:
                chunks.append({"chunk_index": idx, "content": buf, "page": buf_page})
                idx += 1
                buf = para[-OVERLAP:] if len(para) > OVERLAP else para
                buf_page = p["page"]
            else:
                buf += ("\n" if buf else "") + para

    if buf:
        chunks.append({"chunk_index": idx, "content": buf, "page": buf_page})
    return chunks


def _split_paragraphs(text: str) -> list[str]:
    """按空行/换行拆段，去掉空白段。"""
    import re
    parts = re.split(r"\n\s*\n", text)
    out = []
    for part in parts:
        part = part.strip()
        if part:
            out.append(part)
    return out