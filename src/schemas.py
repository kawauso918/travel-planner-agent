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
