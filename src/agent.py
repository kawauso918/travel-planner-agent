"""
旅行計画エージェント（テンプレートv2.0準拠）
Tools接続：ReAct順序＋検索回数制御
"""
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.config import MAX_SEARCH_CALLS, MAX_ITERATIONS
from src.utils import build_search_plan, build_queries
from src.tools.web_search import run_serp_search
from src.tools.plan_generator import generate_itinerary
from src.tools.plan_editor import edit_itinerary
from src.memory import get_memory
from src.prompts import SYSTEM_PROMPT, DEVELOPER_PROMPT
from src.schemas import (
    PlanGenerateInput, PlanGenerateOutput,
    PlanEditInput, PlanEditOutput,
    SearchBrief, WebSearchResponse
)
from src.logger import get_logger

logger = get_logger("agent")


def run_agent(user_input: Dict[str, Any], memory_enabled: bool = True) -> Dict[str, Any]:
    """
    Agent本体を実行（ReAct順序＋検索回数制御）
    
    Args:
        user_input: ユーザー入力の辞書
            - destination: 目的地（必須）
            - days: 旅行日数（必須）
            - budget_total: 予算（オプション）
            - themes: 興味テーマのリスト（オプション、デフォルト: []）
            - style: スタイル（オプション、デフォルト: "normal"）
            - start_point: 出発地点（オプション）
            - mobility: 移動手段（オプション、デフォルト: "public"）
            - constraints: 制約条件（オプション、デフォルト: []）
        memory_enabled: Memoryが有効かどうか
    
    Returns:
        PlanGenerateOutputスキーマに準拠した辞書（itinerary_markdownを含む）
    """
    try:
        logger.info(f"旅行計画生成を開始: destination={user_input.get('destination')}, days={user_input.get('days')}, memory_enabled={memory_enabled}")
        
        # Memoryの取得
        memory = get_memory(enabled=memory_enabled)
        
        # 入力の検証とデフォルト値設定
        destination = user_input.get("destination", "")
        days = user_input.get("days", 3)
        budget_total = user_input.get("budget_total")
        themes = user_input.get("themes", [])
        style = user_input.get("style", "normal")
        start_point = user_input.get("start_point")
        mobility = user_input.get("mobility", "public")
        constraints = user_input.get("constraints", [])
        
        if not destination:
            logger.warning("目的地が指定されていません")
            return _generate_fallback_output(
                destination="未指定",
                days=days,
                budget_total=budget_total,
                themes=themes,
                error="目的地が指定されていません"
            )
        
        # 現在の日付を取得
        now = datetime.now()
        year = now.year
        month = now.month
        
        # ReAct順序に従って処理
        
        # 1. 入力条件の整理
        # （不足情報があれば仮定を宣言 - ここではデフォルト値で処理）
        
        # 2. 検索計画の立案
        search_plan = build_search_plan(
            destination=destination,
            themes=themes if themes else ["観光"],
            year=year,
            month=month,
            max_calls=MAX_SEARCH_CALLS
        )
        
        # 3. 検索実行と要約
        queries = build_queries(search_plan)
        logger.info(f"検索クエリ数: {len(queries)}, MAX_SEARCH_CALLS={MAX_SEARCH_CALLS}")
        
        search_briefs = []
        search_count = 0
        search_errors = []  # 検索エラーを記録
        has_429_error = False  # 429エラーの有無
        
        # MAX_SEARCH_CALLSを超えないように検索を実行
        for query_item in queries:
            # 検索回数制限チェック（カウンタで管理）
            if search_count >= MAX_SEARCH_CALLS:
                logger.warning(f"MAX_SEARCH_CALLS ({MAX_SEARCH_CALLS}) に達したため、検索を中断")
                break
            
            topic = query_item["topic"]
            query = query_item["query"]
            logger.debug(f"検索実行: topic={topic}, query={query}, count={search_count + 1}")
            
            # 検索実行
            search_result = run_serp_search(
                query=query,
                location="Japan",
                num_results=5
            )
            
            search_count += 1  # 検索回数をカウント
            
            # エラーチェック
            if search_result.get("error"):
                error_msg = search_result.get("error", "")
                logger.warning(f"検索エラー: topic={topic}, error={error_msg}")
                # 429エラーの検出
                if "429" in error_msg or "API制限" in error_msg or "rate limit" in error_msg.lower():
                    has_429_error = True
                    search_errors.append(f"{topic}: API制限に達しました")
                    logger.error(f"API制限エラー（429）: topic={topic}")
                else:
                    search_errors.append(f"{topic}: {error_msg}")
                continue
            
            # 結果が0件の場合
            results = search_result.get("results", [])
            if len(results) == 0:
                logger.warning(f"検索結果0件: topic={topic}, query={query}")
                search_errors.append(f"{topic}: 検索結果が見つかりませんでした")
                continue
            
            logger.info(f"検索成功: topic={topic}, 結果数={len(results)}")
            
            # SearchBriefに要約
            brief = _create_search_brief(topic, query, search_result)
            if brief:
                search_briefs.append(brief)
        
        # 4. 旅程組み立て
        plan_input = PlanGenerateInput(
            destination=destination,
            days=days,
            budget_total=budget_total,
            themes=themes if themes else ["観光"],
            style=style,
            start_point=start_point,
            mobility=mobility,
            constraints=constraints,
            search_brief=search_briefs
        )
        
        # 旅程生成
        logger.info(f"旅程生成を開始: search_briefs数={len(search_briefs)}")
        output = generate_itinerary(plan_input)
        logger.info("旅程生成が完了しました")
        
        # 検索エラーやsourcesが空の場合、cautionsに追加
        existing_cautions = output.get("cautions", [])
        new_cautions = []
        
        # 429エラーの場合
        if has_429_error:
            new_cautions.append("検索上限に達したため、残りは一般的な情報でお伝えします。最新情報は公式サイトでご確認ください。")
        
        # 検索結果が0件だった場合（クエリ変更して最大2回試行後も0件）
        if len(search_briefs) == 0 and search_errors:
            logger.warning(f"検索結果が0件: errors={len(search_errors)}")
            new_cautions.append("検索結果が取得できなかったため、一般的な情報に基づいて提案しています。すべての情報は要確認です。")
            # エラーメッセージを追加（最大3件まで）
            for error in search_errors[:3]:
                new_cautions.append(f"※ {error}")
        
        # sourcesが空の場合（必ず理由をcautionsに追加）
        sources = output.get("sources", [])
        if len(sources) == 0:
            logger.warning("sourcesが空です")
            if len(search_briefs) == 0:
                # 検索できなかった場合
                if not any("検索" in str(c) for c in existing_cautions):
                    new_cautions.append("検索できなかったため、参照リンクがありません。公式サイトで最新情報をご確認ください。")
            else:
                # 検索はできたがsourcesが抽出できなかった場合
                if not any("参照リンク" in str(c) for c in existing_cautions):
                    new_cautions.append("参照リンクが取得できませんでした。公式サイトで最新情報をご確認ください。")
        
        # cautionsを更新
        if new_cautions:
            output["cautions"] = existing_cautions + new_cautions
        
        # Memoryに保存（enabledの場合）
        if memory:
            memory.add_message("user", f"旅行計画作成: {destination}, {days}日, 予算={budget_total}")
            memory.add_message("assistant", output.get("itinerary_markdown", ""))
        
        logger.info("旅行計画生成が正常に完了しました")
        return output
    
    except Exception as e:
        # 例外が外に出ないようにし、失敗時は一般プランを返す
        logger.error(f"旅行計画生成でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        return _generate_fallback_output(
            destination=user_input.get("destination", "未指定"),
            days=user_input.get("days", 3),
            budget_total=user_input.get("budget_total"),
            themes=user_input.get("themes", []),
            error=f"エラーが発生しました: {str(e)}"
        )


def _create_search_brief(topic: str, query: str, search_result: Dict[str, Any]) -> Optional[SearchBrief]:
    """
    検索結果をSearchBriefに要約
    
    Args:
        topic: トピック
        query: 検索クエリ
        search_result: WebSearchResponseスキーマに準拠した検索結果
    
    Returns:
        SearchBriefまたはNone（エラー時・0件時）
    """
    try:
        # エラーチェック
        if search_result.get("error"):
            # エラーがある場合はNoneを返す（呼び出し元で処理）
            return None
        
        results = search_result.get("results", [])
        if not results or len(results) == 0:
            # 0件の場合はNoneを返す（呼び出し元で処理）
            return None
        
        # 要約を作成（最初の3件を使用）
        summary_parts = []
        urls = []
        
        for item in results[:3]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("url", "")
            
            if url:
                urls.append(url)
            
            if snippet:
                summary_parts.append(f"- {snippet[:100]}")
        
        summary = "\n".join(summary_parts) if summary_parts else f"{topic}に関する情報が見つかりました。"
        
        # 確度を判定（結果数とエラーの有無から）
        if len(results) >= 3 and not search_result.get("error"):
            confidence = "high"
        elif len(results) >= 1:
            confidence = "medium"
        else:
            confidence = "low"
        
        return SearchBrief(
            topic=topic,
            summary=summary,
            urls=urls,
            confidence=confidence
        )
    
    except Exception:
        return None


def _generate_fallback_output(
    destination: str,
    days: int,
    budget_total: Optional[Any],
    themes: List[str],
    error: str = ""
) -> Dict[str, Any]:
    """
    フォールバック出力を生成（エラー時用）
    
    Args:
        destination: 目的地
        days: 旅行日数
        budget_total: 予算
        themes: テーマ
        error: エラーメッセージ
    
    Returns:
        PlanGenerateOutputスキーマに準拠した辞書
    """
    themes_str = ", ".join(themes) if themes else "観光"
    
    itinerary_markdown = f"""# {destination} {days}日プラン
**テーマ**: {themes_str}

---

## 前提・仮定
- 検索できなかったため、一般的な提案をします
- すべての情報は要確認です
{f'- エラー: {error}' if error else ''}

---

## Day 1: {themes_str.split(',')[0] if themes_str else '観光'}

### 🌅 朝（9:00-12:00）
**観光スポット**
- 概要: 一般的な観光スポットを訪問（要確認）
- 所要時間: 約180分
- 料金: 要確認
- 📍 アクセス: 要確認

### 🍽️ 昼（12:00-14:00）
**レストラン**
- ジャンル: 要確認
- 予算: 要確認

---

## 📚 参照リンク

（参照リンクなし）

---

## ⚠️ 注意点・要確認事項

- 検索できなかったため、すべての情報は要確認です
- 公式サイトで最新情報をご確認ください
{f'- エラー: {error}' if error else ''}

---

## 💰 概算予算

| 項目 | 金額 | 備考 |
|------|------|------|
| 交通 | ¥0 | 要確認 |
| 食事 | ¥0 | 要確認 |
| 体験・入場 | ¥0 | 要確認 |
| その他 | ¥0 | 要確認 |
| **合計** | **¥0** | 要確認 |

---

*この旅程は検索できなかったため生成されました。すべての情報は要確認です。*
"""
    
    # cautionsに必ず「検索できなかった」理由を追加
    cautions = [
        "検索できなかったため、すべての情報は要確認です",
        "公式サイトで最新情報をご確認ください"
    ]
    if error:
        cautions.append(f"エラー詳細: {error}")
    
    return PlanGenerateOutput(
        itinerary_markdown=itinerary_markdown,
        budget_breakdown={
            "transportation": 0,
            "food": 0,
            "activities": 0,
            "other": 0,
            "total": 0
        },
        cautions=cautions,
        sources=[],  # sourcesが空でもOK（理由はcautionsに記載）
        warnings=["検索できなかったため、正確な情報が取得できませんでした"]
    ).dict()


class TravelPlannerAgent:
    """旅行計画を作成・管理するエージェント（後方互換性のため残す）"""
    
    def __init__(self):
        self.memory_enabled = True
    
    def create_plan(self, destination: str, duration: int, budget: int) -> Dict[str, Any]:
        """
        旅行計画を作成（後方互換性のため残す）
        
        Args:
            destination: 目的地
            duration: 滞在日数
            budget: 予算
        
        Returns:
            PlanGenerateOutputスキーマに準拠した旅行計画
        """
        user_input = {
            "destination": destination,
            "days": duration,
            "budget_total": budget
        }
        return run_agent(user_input, memory_enabled=self.memory_enabled)
    
    def edit_plan(self, original_plan: Dict[str, Any], edit_request: str) -> Dict[str, Any]:
        """
        旅行計画を編集（後方互換性のため残す）
        
        Args:
            original_plan: 元の計画
            edit_request: 編集リクエスト
        
        Returns:
            編集後の計画
        """
        # 元の計画をMarkdown形式に変換
        if isinstance(original_plan, dict):
            if "itinerary_markdown" in original_plan:
                current_plan = original_plan["itinerary_markdown"]
            else:
                import json
                current_plan = json.dumps(original_plan, ensure_ascii=False, indent=2)
        else:
            current_plan = str(original_plan)
        
        edit_input = PlanEditInput(
            current_plan=current_plan,
            user_request=edit_request,
            additional_search=False
        )
        
        return edit_itinerary(edit_input)
