"""
ユーティリティ関数モジュール（テンプレートv2.0準拠）
検索計画とクエリ生成機能を含む
"""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# ============================================
# 既存のユーティリティ関数
# ============================================

def format_plan_output(plan_data: Dict[str, Any]) -> str:
    """旅行計画をフォーマットして文字列として返す"""
    if isinstance(plan_data, dict):
        return json.dumps(plan_data, ensure_ascii=False, indent=2)
    return str(plan_data)

def validate_budget(budget: int, total_cost: int) -> bool:
    """予算が合計費用を超えていないか確認"""
    return total_cost <= budget

def calculate_budget_ratio(used: int, total: int) -> float:
    """予算使用率を計算"""
    if total == 0:
        return 0.0
    return (used / total) * 100


# ============================================
# 検索計画とクエリ生成
# ============================================

def build_search_plan(
    destination: str,
    themes: List[str],
    year: int,
    month: int,
    max_calls: int
) -> Dict[str, Any]:
    """
    検索計画を作成（テンプレートv2.0準拠）
    
    Args:
        destination: 目的地
        themes: 興味テーマのリスト（例: ["グルメ", "アート"]）
        year: 年（例: 2025）
        month: 月（例: 1）
        max_calls: 最大検索回数
    
    Returns:
        検索計画の辞書
    """
    # 優先順位：イベント > 営業情報 > アクセス > 定番
    plan = {
        "destination": destination,
        "themes": themes,
        "year": year,
        "month": month,
        "max_calls": max_calls,
        "priority_order": [
            "イベント",
            "営業情報",
            "アクセス",
            "定番"
        ],
        "search_items": []
    }
    
    # 1. イベント（最優先）
    if max_calls > 0:
        plan["search_items"].append({
            "priority": 1,
            "topic": "最新イベント",
            "description": "最新イベント・季節情報（差別化のため最優先）"
        })
    
    # 2. 営業情報
    if max_calls > 1:
        plan["search_items"].append({
            "priority": 2,
            "topic": "営業情報",
            "description": "営業時間・定休日・料金（旅程破綻防止）"
        })
    
    # 3. アクセス
    if max_calls > 2:
        plan["search_items"].append({
            "priority": 3,
            "topic": "アクセス",
            "description": "アクセス・移動手段（現実性担保）"
        })
    
    # 4. 定番（テーマ別）
    remaining_calls = max_calls - len(plan["search_items"])
    if remaining_calls > 0 and themes:
        # テーマごとに定番スポットを検索
        for i, theme in enumerate(themes[:remaining_calls]):
            plan["search_items"].append({
                "priority": 4 + i,
                "topic": f"定番スポット（{theme}）",
                "description": f"{theme}テーマの定番スポット（初訪問対応）",
                "theme": theme
            })
    
    return plan


def build_queries(plan: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    検索計画からクエリリストを生成
    
    Args:
        plan: build_search_planで生成された検索計画
    
    Returns:
        {topic, query}の形のクエリリスト（max_callsを超えない）
    """
    destination = plan["destination"]
    themes = plan.get("themes", [])
    year = plan["year"]
    month = plan["month"]
    max_calls = plan["max_calls"]
    
    queries = []
    
    for item in plan["search_items"][:max_calls]:
        topic = item["topic"]
        priority = item["priority"]
        
        if priority == 1:  # イベント
            query = f"{destination} イベント {year}年{month}月"
            queries.append({"topic": topic, "query": query})
        
        elif priority == 2:  # 営業情報
            # テーマに関連する人気スポットの営業情報
            if themes:
                theme = themes[0]  # 最初のテーマを使用
                query = f"{destination} {theme} 人気店 営業時間 料金 {year}"
            else:
                query = f"{destination} 観光 営業時間 料金 {year}"
            queries.append({"topic": topic, "query": query})
        
        elif priority == 3:  # アクセス
            query = f"{destination} 観光 移動 おすすめ"
            queries.append({"topic": topic, "query": query})
        
        elif priority >= 4:  # 定番スポット
            theme = item.get("theme", themes[0] if themes else "")
            if theme:
                query = f"{destination} {theme} おすすめ 人気"
            else:
                query = f"{destination} 観光 モデルコース {year}"
            queries.append({"topic": topic, "query": query})
    
    return queries


def broaden_query(query: str) -> str:
    """
    クエリを広げる/簡略化して再試行用のクエリを生成（0件時に使用）
    
    Args:
        query: 元のクエリ
    
    Returns:
        広げた/簡略化したクエリ
    """
    # 年や月などの具体的な日付情報を削除
    query = re.sub(r"\d{4}年\d{1,2}月", "", query)
    query = re.sub(r"\d{4}-\d{2}", "", query)
    query = re.sub(r"\d{4}", "", query)  # 年のみも削除
    
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


def dedupe_urls(urls: List[str]) -> List[str]:
    """
    URLの重複を削除（正規化して比較）
    
    Args:
        urls: URLのリスト
    
    Returns:
        重複を削除したURLのリスト（元の順序を保持）
    """
    seen = set()
    result = []
    
    for url in urls:
        if not url:
            continue
        
        # URLを正規化（末尾のスラッシュ、クエリパラメータの順序など）
        normalized = url.rstrip("/").lower()
        
        # クエリパラメータをソート（同じパラメータでも順序が違う場合を考慮）
        if "?" in normalized:
            base, params = normalized.split("?", 1)
            param_pairs = sorted(params.split("&"))
            normalized = base + "?" + "&".join(param_pairs)
        
        if normalized not in seen:
            seen.add(normalized)
            result.append(url)  # 元のURLを保持
    
    return result


