"""LLM 接口层：默认 DeepSeek（OpenAI 兼容协议）。未配置 Key 时自动 mock，离线可跑通骨架。"""
from .. import config


def chat(messages: list[dict], temperature: float = 0.3) -> str:
    """messages: [{"role": "system"|"user"|"assistant", "content": str}] → 模型回复文本"""
    if config.LLM_MOCK:
        return _mock_reply(messages)

    from openai import OpenAI
    client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
    resp = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content


def _mock_reply(messages: list[dict]) -> str:
    """按 system 指令判断任务类型：阅读卡请求返回 JSON，问答请求返回占位回答。"""
    system_text = next((m["content"] for m in messages if m["role"] == "system"), "")
    if any(k in system_text for k in ("JSON", "阅读卡", "摘要")):
        return (
            "```json\n"
            "{\"summary\": \"这是一篇示例论文，研究了相关主题的方法与实验。\", "
            "\"outline\": [\"1. 引言\", \"2. 方法\", \"3. 实验\", \"4. 结论\"], "
            "\"terms\": [{\"term\": \"示例术语\", \"explanation\": \"一个占位解释。\"}], "
            "\"conclusions\": [\"主要发现一。\", \"局限性与展望。\"]}\n"
            "```\n"
            "(当前为 mock 输出：未配置 LLM_API_KEY，配置后可获得真实阅读卡。)"
        )
    return (
        "【Mock 回答】基于原文相关段落：作者在方法部分提出了核心方案，"
        "并在实验部分给出验证。（配置 LLM_API_KEY 后可获得真实回答。）"
    )