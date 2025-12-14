"""
データスキーマ定義モジュール（テンプレートv2.0準拠）
Tool A/B/C の入出力をPydanticで固定
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

class Activity(BaseModel):
    """アクティビティ情報"""
    name: str = Field(description="アクティビティ名")
    description: str = Field(description="説明")
    location: str = Field(description="場所")
    duration: int = Field(description="所要時間（分）")
    cost: int = Field(description="費用（円）")

class DayPlan(BaseModel):
    """1日の計画"""
    date: str = Field(description="日付")
    activities: List[Activity] = Field(description="アクティビティリスト")
    total_cost: int = Field(description="1日の合計費用")

class ReferenceLink(BaseModel):
    """参照リンク情報"""
    title: str = Field(description="リンクのタイトル")
    url: str = Field(description="URL")
    description: Optional[str] = Field(default=None, description="説明")

class TravelPlan(BaseModel):
    """
    旅行計画（テンプレv2.0順序対応）
    順序: 旅程→参照リンク→注意点→概算予算
    """
    # 基本情報
    destination: str = Field(description="目的地")
    duration: int = Field(description="滞在日数")
    budget: int = Field(description="予算")
    
    # 1. 旅程
    daily_plans: List[DayPlan] = Field(description="日別計画（旅程）")
    
    # 2. 参照リンク
    reference_links: List[ReferenceLink] = Field(default_factory=list, description="参照リンク")
    
    # 3. 注意点
    warnings: List[str] = Field(default_factory=list, description="注意点")
    
    # 4. 概算予算
    total_cost: int = Field(description="合計費用（概算予算）")
    budget_breakdown: Optional[dict] = Field(default=None, description="予算内訳")
    
    # エラーハンドリング用
    error: Optional[str] = Field(default=None, description="エラーメッセージ（エラー時のみ）")

class TravelPlanResponse(BaseModel):
    """旅行計画レスポンス（エラーハンドリング対応）"""
    plan: Optional[TravelPlan] = Field(default=None, description="旅行計画")
    error: Optional[str] = Field(default=None, description="エラーメッセージ")
    search_results: Optional[dict] = Field(default=None, description="検索結果")


# ============================================
# Tool A: Web検索（SerpAPI）の入出力スキーマ
# ============================================

class WebSearchResultItem(BaseModel):
    """Web検索結果の1項目"""
    title: str = Field(description="記事タイトル")
    snippet: str = Field(description="検索結果の要約（150文字程度）")
    url: str = Field(description="URL")
    source: Optional[str] = Field(default=None, description="サイト名")
    date: Optional[str] = Field(default=None, description="日付（例: 2025-01-15）")

class WebSearchResponse(BaseModel):
    """Web検索の出力スキーマ"""
    results: List[WebSearchResultItem] = Field(default_factory=list, description="検索結果リスト")
    meta: Dict[str, Any] = Field(description="メタ情報（query, fetched_at, result_count等）")
    error: Optional[str] = Field(default=None, description="エラーメッセージ（エラー時のみ）")


# ============================================
# Search Brief（検索結果要約）
# ============================================

class SearchBrief(BaseModel):
    """検索結果の要約フォーマット"""
    topic: str = Field(description="トピック（例: 最新イベント）")
    summary: str = Field(description="要約内容")
    urls: List[str] = Field(description="出典URLリスト")
    confidence: str = Field(description="情報の確度（high / medium / low）")


# ============================================
# Tool B: 旅程生成（Plan Generator）の入出力スキーマ
# ============================================

class PlanGenerateInput(BaseModel):
    """旅程生成の入力スキーマ"""
    destination: str = Field(description="行き先")
    days: int = Field(description="旅行日数")
    budget_total: Optional[Union[int, str]] = Field(default=None, description="予算（例: 50000 or \"5万円\"）")
    themes: List[str] = Field(description="興味テーマのリスト")
    style: Optional[str] = Field(default="normal", description="スタイル（relaxed / normal / packed）")
    start_point: Optional[str] = Field(default=None, description="出発地点")
    mobility: Optional[str] = Field(default="public", description="移動手段（public / car / walk）")
    constraints: Optional[List[str]] = Field(default_factory=list, description="制約条件（食の制約、雨天希望など）")
    search_brief: List[SearchBrief] = Field(description="検索結果要約リスト")

class PlanGenerateOutput(BaseModel):
    """旅程生成の出力スキーマ"""
    itinerary_markdown: str = Field(description="旅程（Markdown形式）")
    budget_breakdown: Dict[str, Union[int, float]] = Field(description="予算内訳（transportation, food, activities, other, total）")
    cautions: List[str] = Field(default_factory=list, description="注意事項リスト")
    sources: List[str] = Field(default_factory=list, description="出典URLリスト")
    warnings: List[str] = Field(default_factory=list, description="警告リスト（移動時間が長い等）")


# ============================================
# Tool C: 旅程編集（Plan Editor）の入出力スキーマ
# ============================================

class PlanEditInput(BaseModel):
    """旅程編集の入力スキーマ"""
    current_plan: str = Field(description="現在の旅程（Markdown形式）")
    user_request: str = Field(description="ユーザーの修正指示")
    additional_search: bool = Field(default=False, description="追加検索が必要か")

class PlanEditOutput(BaseModel):
    """旅程編集の出力スキーマ"""
    updated_plan: str = Field(description="更新後の旅程（Markdown形式）")
    change_log: List[str] = Field(default_factory=list, description="変更履歴リスト")
    new_sources: List[str] = Field(default_factory=list, description="新規出典URLリスト")


# ============================================
# ユーザー入力検証スキーマ（改善提案）
# ============================================

class UserInputSchema(BaseModel):
    """ユーザー入力の検証スキーマ（改善提案）"""
    destination: str = Field(..., min_length=1, max_length=100, description="目的地")
    days: int = Field(..., ge=1, le=30, description="旅行日数")
    budget_total: Optional[int] = Field(None, ge=0, description="予算（円）")
    themes: List[str] = Field(default_factory=list, description="興味テーマ")
    style: str = Field(default="normal", description="旅行スタイル")
    start_point: Optional[str] = Field(None, max_length=100, description="出発地点")
    mobility: str = Field(default="public", description="移動手段")
    constraints: List[str] = Field(default_factory=list, description="制約条件")
    
    @validator('destination')
    def validate_destination(cls, v):
        """目的地の検証"""
        if not v or not v.strip():
            raise ValueError('目的地が空です')
        return v.strip()
    
    @validator('style')
    def validate_style(cls, v):
        """スタイルの検証"""
        allowed = ['relaxed', 'normal', 'packed']
        if v not in allowed:
            raise ValueError(f'スタイルは {allowed} のいずれかである必要があります')
        return v
    
    @validator('mobility')
    def validate_mobility(cls, v):
        """移動手段の検証"""
        allowed = ['public', 'car', 'walk']
        if v not in allowed:
            raise ValueError(f'移動手段は {allowed} のいずれかである必要があります')
        return v


# ============================================
# 評価結果スキーマ（LLM as a Judge）
# ============================================

class EvaluationScores(BaseModel):
    """評価スコア（6つの観点）"""
    appropriateness: float = Field(ge=0, le=100, description="適切性（0-100）")
    feasibility: float = Field(ge=0, le=100, description="実現可能性（0-100）")
    accuracy: float = Field(ge=0, le=100, description="情報の正確性（0-100）")
    completeness: float = Field(ge=0, le=100, description="構造の完全性（0-100）")
    budget_validity: float = Field(ge=0, le=100, description="予算の妥当性（0-100）")
    warnings_adequacy: float = Field(ge=0, le=100, description="注意点の適切性（0-100）")

class ScoreEvaluationResult(BaseModel):
    """スコア評価結果"""
    overall_score: float = Field(ge=0, le=100, description="総合スコア（0-100）")
    scores: EvaluationScores = Field(description="各観点のスコア")
    feedback: str = Field(description="フィードバック")
    strengths: List[str] = Field(default_factory=list, description="強みリスト")
    improvements: List[str] = Field(default_factory=list, description="改善点リスト")

class PlanRanking(BaseModel):
    """計画の順位情報"""
    plan_id: int = Field(ge=0, le=4, description="計画のID（0-4）")
    rank: int = Field(ge=1, le=5, description="順位（1-5）")
    score: float = Field(ge=0, le=100, description="スコア（0-100）")
    reason: str = Field(description="順位の理由")

class ComparisonEvaluationResult(BaseModel):
    """比較評価結果"""
    rankings: List[PlanRanking] = Field(description="順位リスト")
    best_plan_id: int = Field(ge=0, le=4, description="最良の計画のID")
    comparison_summary: str = Field(description="比較サマリー")
    detailed_comparison: Dict[str, Any] = Field(default_factory=dict, description="詳細比較")


# ============================================
# QAレビュー結果スキーマ
# ============================================

class QAEvaluationIssue(BaseModel):
    """QA評価の問題点"""
    severity: str = Field(description="重要度（high/medium/low）")
    problem: str = Field(description="問題点（具体的）")
    evidence: str = Field(description="どの部分が問題か（該当箇所の短い引用 or 要約）")
    fix: str = Field(description="どう直せば良いか（具体策）")

class QAEvaluationScores(BaseModel):
    """QA評価スコア（各1-5点）"""
    正確性: int = Field(ge=1, le=5, description="正確性（1-5点）")
    実現可能性: int = Field(ge=1, le=5, description="実現可能性（1-5点）")
    テーマ整合性: int = Field(ge=1, le=5, description="テーマ整合性（1-5点）")
    根拠の明示: int = Field(ge=1, le=5, description="根拠の明示（1-5点）")
    予算妥当性: int = Field(ge=1, le=5, description="予算妥当性（1-5点）")
    出力品質: int = Field(ge=1, le=5, description="出力品質（1-5点）")

class QAReviewResult(BaseModel):
    """QAレビュー結果"""
    scores: QAEvaluationScores = Field(description="各観点のスコア（1-5点）")
    total_30: int = Field(ge=0, le=30, description="合計スコア（0-30点）")
    total_100: float = Field(ge=0, le=100, description="100点換算スコア（0-100点）")
    good_points: List[str] = Field(default_factory=list, description="良い点（最大3つ）")
    issues: List[QAEvaluationIssue] = Field(default_factory=list, description="問題点リスト")
    must_fix_first: List[str] = Field(default_factory=list, description="優先度が最も高い修正点（最大3つ）")
    rewrite_suggestions: List[str] = Field(default_factory=list, description="改善の方向性（最大3つ）")


# ============================================
# プラン比較結果スキーマ
# ============================================

class ComparisonReason(BaseModel):
    """比較理由（各観点）"""
    criterion: str = Field(description="観点名（正確性、実現可能性等）")
    better: str = Field(description="どちらが良いか（A/B/tie）")
    why: str = Field(description="理由")

class PlanComparisonResult(BaseModel):
    """プラン比較結果"""
    winner: str = Field(description="勝者（A/B/tie）")
    reason_summary: str = Field(description="2〜4文で要点")
    detailed_reasons: List[ComparisonReason] = Field(description="各観点の詳細比較")
    suggested_merge: str = Field(description="AとBの良いところを統合するならどうするか（短く）")

