"""命令行入口（W1 验收）：解析 → 分块 → 入库 → 阅读卡。
用法：cd backend && python -m app.cli --pdf D:/path/to/paper.pdf
"""
import argparse
import json

from .db import init_db, get_conn
from .services import pdf_parser, chunker, summarizer


def main():
    parser = argparse.ArgumentParser(description="AI 论文阅读助手 CLI（W1 核心链路）")
    parser.add_argument("--pdf", required=True, help="PDF 文件路径")
    parser.add_argument("--no-save", action="store_true", help="不写入文献库，仅打印")
    args = parser.parse_args()

    init_db()
    parsed = pdf_parser.extract_text(args.pdf)
    chunks = chunker.split_pages_into_chunks(parsed["pages"])
    title = pdf_parser.guess_title(parsed["pages"])
    print(f"解析完成：{len(parsed['pages'])} 页，{len(chunks)} 块，标题：{title}")

    if not args.no_save:
        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO papers (title, raw_text) VALUES (?, ?)", (title, parsed["raw_text"])
        )
        pid = cur.lastrowid
        for c in chunks:
            conn.execute(
                "INSERT INTO chunks (paper_id, chunk_index, content, page) VALUES (?, ?, ?, ?)",
                (pid, c["chunk_index"], c["content"], c["page"]),
            )
        conn.commit()
        conn.close()
        print(f"已入库：paper id={pid}")

    card = summarizer.generate_reading_card(chunks)
    print("=== 阅读卡 ===")
    print(json.dumps(card, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()