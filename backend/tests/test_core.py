"""核心链路测试：生成示例 PDF → 解析 → 分块 → mock 阅读卡（无需 API Key）。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import pymupdf as fitz  # noqa: E402
except ImportError:
    import fitz  # noqa: E402
from app.services import pdf_parser, chunker, summarizer  # noqa: E402


def make_sample_pdf(path: str, pages: int = 10):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i+1} - Sample Paper on Deep Learning")
        for j in range(20):
            page.insert_text((72, 100 + j * 16),
                f"Paragraph {j}: This paper studies deep learning methods for document understanding. "
                "We propose a novel architecture combining transformers and attention mechanisms, "
                "and evaluate it on multiple benchmarks. Results show significant improvement over baselines.")
    doc.save(path)
    doc.close()


def test_pipeline():
    tmp = tempfile.mkdtemp()
    pdf = os.path.join(tmp, "sample.pdf")
    make_sample_pdf(pdf, pages=10)

    parsed = pdf_parser.extract_text(pdf)
    assert len(parsed["pages"]) == 10
    assert len(parsed["raw_text"]) > 100

    chunks = chunker.split_pages_into_chunks(parsed["pages"])
    assert len(chunks) >= 1
    assert all(c["page"] >= 1 for c in chunks)

    title = pdf_parser.guess_title(parsed["pages"])
    assert title

    card = summarizer.generate_reading_card(chunks)  # mock 模式
    assert "summary" in card
    print(f"核心链路 OK: {len(parsed['pages'])} 页 -> {len(chunks)} 块 -> 阅读卡: {card['summary'][:40]}")