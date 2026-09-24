"""阅读卡生成：摘要 + 大纲 + 术语解释 + 核心结论，输出结构化 dict。"""
import json

from . import llm

_SYSTEM_PROMPT = (
    "你是一名学术阅读助手。用户会提供一篇论文的正文（分块截取），"
    "请严格按 JSON 输出，字段如下：\n"
    '"summary": 一句话摘要（2-3 句）；\n'
    '"outline": 章节大纲（字符串数组）；\n'
    '"terms": [{"term": "术语", "explanation": "解释"}]；\n'
    '"conclusions": 核心结论（字符串数组）。\n'
    "只输出 JSON，不要输出其他内容。"
)


def generate_reading_card(chunks: list[dict]) -> dict:
    """取正文前若干块（通常含摘要与引言）生成阅读卡。"""
    context = "\n\n".join(c["content"] for c in chunks[:8])
    reply = llm.chat([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"论文正文（分块截取）：\n{context}"},
    ])
    return _parse_json(reply)


def _parse_json(reply: str) -> dict:
    """容错解析：优先提取 ``` 代码块中的 JSON，再回退到首尾大括号截取。"""
    text = reply.strip()
    if "```" in text:
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                text = part
                break
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": reply[:300], "outline": [], "terms": [], "conclusions": []}