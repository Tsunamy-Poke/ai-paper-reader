"""全局配置：LLM 接入与本地路径。环境变量可覆盖默认值。"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # ai-paper-reader/

load_dotenv(BASE_DIR / ".env")  # 固定加载项目根目录的 .env，与运行目录无关

# LLM 配置：默认 DeepSeek（OpenAI 兼容协议）
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
# 未配置 Key 时默认 mock，骨架阶段可离线跑通全链路
LLM_MOCK = os.getenv("LLM_MOCK", "1" if not LLM_API_KEY else "0") == "1"

# 本地存储（方案 A：只存文本，不存 PDF 原文）
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "reader.db"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "backend" / "uploads"))