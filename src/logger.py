"""
ログ管理モジュール（デプロイ後の問題追跡用）
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# ログディレクトリ
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# ログファイル名（日付付き）
LOG_FILE = LOG_DIR / f"travel_planner_{datetime.now().strftime('%Y%m%d')}.log"


def setup_logger(
    name: str = "travel_planner",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    ロガーを設定
    
    Args:
        name: ロガー名
        level: ログレベル（デフォルト: INFO）
        log_to_file: ファイルにログを出力するか
        log_to_console: コンソールにログを出力するか
    
    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)
    
    # 既にハンドラーが設定されている場合はスキップ
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # フォーマッター（機密情報を除外）
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # ファイルハンドラー
    if log_to_file:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def sanitize_message(message: str) -> str:
    """
    ログメッセージから機密情報を除去
    
    Args:
        message: 元のメッセージ
    
    Returns:
        機密情報を除去したメッセージ
    """
    # APIキーのパターンを検出してマスク
    import re
    
    # OpenAI APIキー（sk-で始まる）
    message = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***MASKED***', message)
    
    # SerpAPI APIキー（通常の文字列）
    # 注意: 完全な検出は困難なため、明示的にマスクする必要がある場合は呼び出し側で処理
    
    # メールアドレス（部分的にマスク）
    message = re.sub(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
                     r'\1@***MASKED***', message)
    
    return message


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    ロガーを取得（シングルトン的な使用）
    
    Args:
        name: ロガー名（Noneの場合はデフォルト名を使用）
    
    Returns:
        ロガーインスタンス
    """
    logger_name = name or "travel_planner"
    return setup_logger(logger_name)


# デフォルトロガー
logger = get_logger()


