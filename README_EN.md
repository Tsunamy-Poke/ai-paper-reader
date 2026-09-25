# AI Paper Reader

> Drag in a **PDF / Word(.docx) / TXT** file, get an AI-generated **summary / outline / glossary / key conclusions** in one click. Ask follow-up questions against the original text, search across your whole library, and export a clean reading card.

**English** | [中文](./README.md)

An open-source, local-first reading assistant for academic papers and long documents. Powered by FastAPI + PyMuPDF + SQLite FTS5 + a DeepSeek-compatible LLM layer, with a zero-build single-page frontend.

## Features

- 📄 **One-click reading card** — upload a paper PDF / Word / TXT, get summary, chapter outline, term glossary and key conclusions in seconds
- 💬 **Follow-up Q&A** — ask anything about the paper; answers are grounded in the original text chunks
- 🔍 **Cross-paper search** — full-text search across your entire library, with page numbers, highlighted snippets and relevance scores
- ⬇️ **Export** — download any reading card as a clean, printable HTML page
- 🪶 **Local-first storage (Plan A)** — only extracted text is kept; PDFs are deleted right after parsing (≈50–200 MB per 1,000 papers)
- 🧩 **Zero-build frontend** — React + Tailwind via CDN, no Node.js or bundler required
- 🔌 **LLM-agnostic** — works with DeepSeek (or any OpenAI-compatible API); falls back to a built-in mock when no API key is set, so the skeleton runs offline

## Screenshots

| | |
|---|---|
| Home — upload, cross-paper search, library | Reading card — summary / outline / glossary / conclusions |
| ![Home](docs/screenshot-home.png) | ![Reading card](docs/w2-reader-page.png) |
| Exported HTML reading card | |
| ![Exported card](docs/w3-export-page.png) | |

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# Run one paper from the CLI (mock mode by default, no API key needed)
python -m app.cli --pdf D:\path\to\paper.pdf

# Start the API server (API docs at http://127.0.0.1:8000/docs)
python -m uvicorn app.main:app --port 8000
```

Then open `frontend/index.html` in a browser (no build step). Or just double-click `start.bat` to launch everything.

## Configure a Real LLM (Optional)

Create a `.env` file in the project root:

```
LLM_API_KEY=your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

Without a key, the app automatically runs in mock mode so the whole pipeline works offline.

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Health check |
| POST | `/papers/upload` | Upload PDF / Word(.docx) / TXT (original file is deleted after parsing) |
| GET | `/papers` | List library |
| GET | `/papers/{id}` | Paper detail |
| GET | `/papers/{id}/reading-card` | Generate reading card |
| POST | `/papers/{id}/ask` | Ask follow-up questions against the paper |
| DELETE | `/papers/{id}` | Delete paper |
| GET | `/search?q=` | Full-text search across papers (relevance-ranked with scores) |
| GET | `/search/rank?topic=` | Rank your whole library by topic relevance |
| GET | `/papers/{id}/export` | Export reading card as HTML |

## Project Structure

```
ai-paper-reader/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry
│   │   ├── cli.py             # CLI entry
│   │   ├── config.py          # LLM / path config (.env)
│   │   ├── db.py              # SQLite + FTS5 (with sync triggers)
│   │   ├── routers/           # papers.py / chat.py / search.py
│   │   └── services/          # pdf_parser / chunker / llm / summarizer
│   ├── uploads/               # temp dir (cleaned after parsing)
│   └── tests/
├── frontend/                  # zero-build single page (React + Tailwind CDN)
├── docs/                      # screenshots
├── start.bat                  # one-click launcher
└── README.md
```

## Roadmap

- v2.0 candidates: figure/formula understanding, batch import, browser extension, multi-model switching, relevance ranking

## License

MIT
