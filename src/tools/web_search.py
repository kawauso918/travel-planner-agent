"""
Web検索ツール（Tool A: SerpAPI検索＋フォールバック）
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

try:
    from serpapi import GoogleSearch
    SERPAPI_AVAILABLE = True
except ImportError:
    GoogleSearch = None
    SERPAPI_AVAILABLE = False

from src.config import SERPAPI_API_KEY, MAX_SEARCH_CALLS
from src.schemas import WebSearchResponse, WebSearchResultItem
from src.logger import get_logger

logger = get_logger("web_search")


def run_serp_search(
    query: str,
    location: Optional[str] = "Japan",
    num_results: int = 5,
    time_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    SerpAPIを使用してWeb検索を実行（Tool A）
    
    Args:
        query: 検索クエリ（日本語推奨）
        location: 地域指定（例: "Japan" / "Tokyo"）、デフォルト: "Japan"
        num_results: 取得件数（デフォルト: 5、最大: 10）
        time_filter: 時間フィルタ（"d"(24h) / "w"(1週間) / "m"(1ヶ月)）
    
    Returns:
        WebSearchResponseスキーマに準拠した辞書
    """
    # APIキーがない場合
    if not SERPAPI_API_KEY:
        logger.error("SERPAPI_API_KEYが設定されていません")
        return WebSearchResponse(
            results=[],
            meta={
                "query": query,
                "fetched_at": datetime.now().isoformat(),
                "result_count": 0
            },
            error="SERPAPI_API_KEYが設定されていません"
        ).dict()
    
    # google-search-resultsパッケージがない場合
    if not SERPAPI_AVAILABLE or GoogleSearch is None:
        logger.error("SerpAPIパッケージがインストールされていません")
        return WebSearchResponse(
            results=[],
            meta={
                "query": query,
                "fetched_at": datetime.now().isoformat(),
                "result_count": 0
            },
            error="google-search-resultsパッケージがインストールされていません。pip install google-search-results を実行してください。"
        ).dict()
    
    # 最大2回まで再試行（結果0件の場合）
    max_retries = 2
    current_query = query
    
    for attempt in range(max_retries + 1):
        try:
            # SerpAPIパラメータを設定
            params = {
                "q": current_query,
                "api_key": SERPAPI_API_KEY,
                "engine": "google",
                "num": min(num_results, 10),  # 最大10件
                "hl": "ja",  # 日本語
                "gl": "jp"   # 日本
            }
            
            # location指定
            if location:
                params["location"] = location
            
            # time_filter指定
            if time_filter:
                params["tbs"] = f"qdr:{time_filter}"  # d=日, w=週, m=月
            
            # 検索実行
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # エラーチェック（SerpAPIからのエラーレスポンス）
            if "error" in results:
                error_msg = results.get("error", "不明なエラー")
                # 429エラーの検出
                if "429" in str(error_msg) or "rate limit" in str(error_msg).lower():
                    logger.error(f"API制限エラー（429）: query={query}")
                    return WebSearchResponse(
                        results=[],
                        meta={
                            "query": query,
                            "fetched_at": datetime.now().isoformat(),
                            "result_count": 0
                        },
                        error="API制限に達しました（HTTP 429）。しばらく時間をおいてから再試行してください。"
                    ).dict()
                # その他のエラー
                logger.error(f"SerpAPIエラー: query={query}, error={error_msg}")
                return WebSearchResponse(
                    results=[],
                    meta={
                        "query": query,
                        "fetched_at": datetime.now().isoformat(),
                        "result_count": 0
                    },
                    error=f"SerpAPIエラー: {error_msg}"
                ).dict()
            
            # 結果をパース
            search_items = []
            if "organic_results" in results:
                for item in results["organic_results"][:num_results]:
                    search_items.append(
                        WebSearchResultItem(
                            title=item.get("title", ""),
                            snippet=item.get("snippet", "")[:150],  # 150文字程度
                            url=item.get("link", ""),
                            source=item.get("source", None),
                            date=_extract_date(item)
                        )
                    )
            
            # 結果が0件で、まだ再試行可能な場合
            if len(search_items) == 0 and attempt < max_retries:
                logger.warning(f"検索結果0件（試行{attempt + 1}/{max_retries + 1}）: query={current_query}")
                # クエリを広げる/簡略化
                current_query = _broaden_query(current_query)
                logger.info(f"クエリを変更: {current_query}")
                continue
            
            # 成功した場合
            logger.info(f"検索成功: query={query}, 結果数={len(search_items)}")
            return WebSearchResponse(
                results=search_items,
                meta={
                    "query": query,
                    "fetched_at": datetime.now().isoformat(),
                    "result_count": len(search_items)
                },
                error=None
            ).dict()
        
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"検索例外: query={query}, attempt={attempt + 1}, error_type={error_type}, error={error_msg}", exc_info=True)
            
            # HTTP 429 (Rate Limit) の検出
            if "429" in error_msg or "rate limit" in error_msg.lower() or "RateLimitError" in error_type:
                logger.error(f"API制限エラー（429）: query={query}")
                return WebSearchResponse(
                    results=[],
                    meta={
                        "query": query,
                        "fetched_at": datetime.now().isoformat(),
                        "result_count": 0
                    },
                    error="API制限に達しました（HTTP 429）。しばらく時間をおいてから再試行してください。"
                ).dict()
            
            # タイムアウトの検出
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower() or "Timeout" in error_type:
                logger.warning(f"タイムアウト: query={query}")
                return WebSearchResponse(
                    results=[],
                    meta={
                        "query": query,
                        "fetched_at": datetime.now().isoformat(),
                        "result_count": 0
                    },
                    error="検索がタイムアウトしました。"
                ).dict()
            
            # その他の例外（最後の試行の場合のみエラーを返す）
            if attempt >= max_retries:
                logger.error(f"検索エラー（最終試行）: query={query}, error={error_msg}")
                return WebSearchResponse(
                    results=[],
                    meta={
                        "query": query,
                        "fetched_at": datetime.now().isoformat(),
                        "result_count": 0
                    },
                    error=f"検索エラー: {error_msg}"
                ).dict()
            
            # 再試行可能な場合はクエリを変更して再試行
            current_query = _broaden_query(current_query)
    
    # すべての試行が失敗した場合
    return WebSearchResponse(
        results=[],
        meta={
            "query": query,
            "fetched_at": datetime.now().isoformat(),
            "result_count": 0
        },
        error="検索結果が見つかりませんでした（最大再試行回数に達しました）"
    ).dict()


def _extract_date(item: Dict[str, Any]) -> Optional[str]:
    """
    検索結果から日付を抽出
    
    Args:
        item: 検索結果の項目
    
    Returns:
        日付文字列（YYYY-MM-DD形式）またはNone
    """
    # dateフィールドがある場合
    if "date" in item:
        return item["date"]
    
    # snippetから日付を抽出を試みる
    snippet = item.get("snippet", "")
    date_patterns = [
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
        r"(\d{4})/(\d{1,2})/(\d{1,2})"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, snippet)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return None


def _broaden_query(query: str) -> str:
    """
    クエリを広げる/簡略化して再試行用のクエリを生成
    
    Args:
        query: 元のクエリ
    
    Returns:
        広げた/簡略化したクエリ
    """
    # 年や月などの具体的な日付情報を削除
    query = re.sub(r"\d{4}年\d{1,2}月", "", query)
    query = re.sub(r"\d{4}-\d{2}", "", query)
    
    # 余分な空白を削除
    query = re.sub(r"\s+", " ", query).strip()
    
    # クエリが短すぎる場合は元のクエリを返す
    if len(query) < 3:
        return query
    
    # 最後の単語を削除（簡略化）
    words = query.split()
    if len(words) > 2:
        return " ".join(words[:-1])
    
    return query


class WebSearchTool:
    """Web検索を実行するツール（SERPAPI使用）"""
    
    def __init__(self):
        self.api_key = SERPAPI_API_KEY
        self.search_count = 0
        self.max_search_calls = MAX_SEARCH_CALLS
    
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Web検索を実行（SERPAPI使用）
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
        
        Returns:
            検索結果の辞書（エラー時はerrorフィールドを含む）
        """
        return run_serp_search(query=query, num_results=max_results)
    
    def search_travel_info(self, destination: str) -> Dict[str, Any]:
        """
        旅行情報を検索
        
        Args:
            destination: 目的地
        
        Returns:
            検索結果の辞書
        """
        query = f"{destination} 旅行 観光 最新情報"
        return run_serp_search(query=query, location="Japan", num_results=5)
    
    def reset_search_count(self):
        """検索回数カウンターをリセット"""
        self.search_count = 0
    
    def get_remaining_searches(self) -> int:
        """残りの検索可能回数を取得"""
        return max(0, self.max_search_calls - self.search_count)
