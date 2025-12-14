"""
設定管理モジュール（テンプレートv2.0準拠）
"""
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

# SERPAPI設定
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

# ============================================
# Agent設定（パラメータ固定）
# ============================================
MAX_SEARCH_CALLS = 5          # 検索回数上限
MAX_ITERATIONS = 10           # Agentの最大試行回数
TIMEOUT_SECONDS = 30          # タイムアウト（秒）

# ============================================
# Memory設定（パラメータ固定）
# ============================================
MEMORY_TYPE = "ConversationSummaryBufferMemory"  # Memory種類
MAX_TOKEN_LIMIT = 2000        # 履歴保持の上限トークン

# ============================================
# 旅程密度設定
# ============================================
STYLE_CONFIG = {
    "relaxed": {"slots_per_day": 3, "description": "ゆったり"},
    "normal": {"slots_per_day": 4, "description": "標準"},
    "packed": {"slots_per_day": 5, "description": "充実"}
}

# ============================================
# 検索結果の採用基準（優先順位）
# ============================================
SOURCE_PRIORITY = [
    "公式サイト",
    "自治体・観光協会",
    "大手メディア（じゃらん、るるぶ等）",
    "旅行ブログ・レビュー"
]

