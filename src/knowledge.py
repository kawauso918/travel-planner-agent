"""
RAG（自前ナレッジ）管理モジュール
お気に入りリスト、旅行メモ、過去旅程を管理
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from src.logger import get_logger

logger = get_logger("knowledge")

# データ保存ディレクトリ
KNOWLEDGE_DIR = Path("knowledge_data")
KNOWLEDGE_DIR.mkdir(exist_ok=True)

# データファイル
FAVORITES_FILE = KNOWLEDGE_DIR / "favorites.json"
MEMOS_FILE = KNOWLEDGE_DIR / "travel_memos.json"
PAST_ITINERARIES_FILE = KNOWLEDGE_DIR / "past_itineraries.json"


class KnowledgeBase:
    """
    RAG用のナレッジベース
    お気に入りリスト、旅行メモ、過去旅程を管理
    """
    
    def __init__(self):
        """ナレッジベースを初期化"""
        self.favorites: List[Dict[str, Any]] = []
        self.travel_memos: List[Dict[str, Any]] = []
        self.past_itineraries: List[Dict[str, Any]] = []
        self._load_all()
    
    def _load_all(self):
        """すべてのデータを読み込む"""
        self._load_favorites()
        self._load_memos()
        self._load_itineraries()
    
    def _load_favorites(self):
        """お気に入りリストを読み込む"""
        try:
            if FAVORITES_FILE.exists():
                with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                    self.favorites = json.load(f)
            else:
                self.favorites = []
        except Exception as e:
            logger.error(f"お気に入りリストの読み込みエラー: {e}")
            self.favorites = []
    
    def _load_memos(self):
        """旅行メモを読み込む"""
        try:
            if MEMOS_FILE.exists():
                with open(MEMOS_FILE, 'r', encoding='utf-8') as f:
                    self.travel_memos = json.load(f)
            else:
                self.travel_memos = []
        except Exception as e:
            logger.error(f"旅行メモの読み込みエラー: {e}")
            self.travel_memos = []
    
    def _load_itineraries(self):
        """過去旅程を読み込む"""
        try:
            if PAST_ITINERARIES_FILE.exists():
                with open(PAST_ITINERARIES_FILE, 'r', encoding='utf-8') as f:
                    self.past_itineraries = json.load(f)
            else:
                self.past_itineraries = []
        except Exception as e:
            logger.error(f"過去旅程の読み込みエラー: {e}")
            self.past_itineraries = []
    
    def _save_favorites(self):
        """お気に入りリストを保存"""
        try:
            with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"お気に入りリストの保存エラー: {e}")
    
    def _save_memos(self):
        """旅行メモを保存"""
        try:
            with open(MEMOS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.travel_memos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"旅行メモの保存エラー: {e}")
    
    def _save_itineraries(self):
        """過去旅程を保存"""
        try:
            with open(PAST_ITINERARIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.past_itineraries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"過去旅程の保存エラー: {e}")
    
    # ============================================
    # お気に入りリスト管理
    # ============================================
    
    def add_favorite(self, name: str, category: str, location: str = "", notes: str = "", url: str = "") -> bool:
        """
        お気に入りを追加
        
        Args:
            name: 名前（例: "金閣寺"）
            category: カテゴリ（例: "観光スポット", "レストラン", "ホテル"）
            location: 場所（例: "京都"）
            notes: メモ
            url: URL
        
        Returns:
            成功した場合True
        """
        # 既存のIDを確認して、一意のIDを生成
        existing_ids = {fav.get("id") for fav in self.favorites if fav.get("id")}
        new_id = 1
        while new_id in existing_ids:
            new_id += 1
        
        favorite = {
            "id": new_id,
            "name": name,
            "category": category,
            "location": location,
            "notes": notes,
            "url": url,
            "created_at": datetime.now().isoformat()
        }
        self.favorites.append(favorite)
        self._save_favorites()
        logger.info(f"お気に入りを追加: ID={new_id}, name={name}, category={category}")
        return True
    
    def get_favorites(self, category: Optional[str] = None, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        お気に入りリストを取得
        
        Args:
            category: カテゴリでフィルタ（オプション）
            location: 場所でフィルタ（オプション）
        
        Returns:
            お気に入りリスト
        """
        result = self.favorites.copy()
        if category:
            result = [f for f in result if f.get("category") == category]
        if location:
            result = [f for f in result if location in f.get("location", "")]
        return result
    
    def remove_favorite(self, favorite_id: int) -> bool:
        """お気に入りを削除"""
        self.favorites = [f for f in self.favorites if f.get("id") != favorite_id]
        self._save_favorites()
        logger.info(f"お気に入りを削除: ID={favorite_id}")
        return True
    
    # ============================================
    # 旅行メモ管理
    # ============================================
    
    def add_memo(self, title: str, content: str, tags: List[str] = None) -> bool:
        """
        旅行メモを追加
        
        Args:
            title: タイトル
            content: 内容
            tags: タグリスト（オプション）
        
        Returns:
            成功した場合True
        """
        memo = {
            "id": len(self.travel_memos) + 1,
            "title": title,
            "content": content,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.travel_memos.append(memo)
        self._save_memos()
        logger.info(f"旅行メモを追加: {title}")
        return True
    
    def get_memos(self, tags: Optional[List[str]] = None, search_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        旅行メモを取得
        
        Args:
            tags: タグでフィルタ（オプション）
            search_text: テキスト検索（オプション）
        
        Returns:
            旅行メモリスト
        """
        result = self.travel_memos.copy()
        if tags:
            result = [m for m in result if any(tag in m.get("tags", []) for tag in tags)]
        if search_text:
            search_lower = search_text.lower()
            result = [
                m for m in result 
                if search_lower in m.get("title", "").lower() or search_lower in m.get("content", "").lower()
            ]
        return result
    
    def update_memo(self, memo_id: int, title: Optional[str] = None, content: Optional[str] = None, tags: Optional[List[str]] = None) -> bool:
        """旅行メモを更新"""
        for memo in self.travel_memos:
            if memo.get("id") == memo_id:
                if title:
                    memo["title"] = title
                if content:
                    memo["content"] = content
                if tags is not None:
                    memo["tags"] = tags
                memo["updated_at"] = datetime.now().isoformat()
                self._save_memos()
                logger.info(f"旅行メモを更新: ID={memo_id}")
                return True
        return False
    
    def remove_memo(self, memo_id: int) -> bool:
        """旅行メモを削除"""
        self.travel_memos = [m for m in self.travel_memos if m.get("id") != memo_id]
        self._save_memos()
        logger.info(f"旅行メモを削除: ID={memo_id}")
        return True
    
    # ============================================
    # 過去旅程管理
    # ============================================
    
    def save_itinerary(self, destination: str, days: int, itinerary_markdown: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        過去旅程を保存
        
        Args:
            destination: 目的地
            days: 旅行日数
            itinerary_markdown: 旅程（Markdown形式）
            metadata: メタデータ（予算、テーマなど）
        
        Returns:
            保存された旅程のID
        """
        # 既存のIDを確認して、一意のIDを生成
        existing_ids = {itinerary.get("id") for itinerary in self.past_itineraries if itinerary.get("id")}
        new_id = 1
        while new_id in existing_ids:
            new_id += 1
        
        itinerary = {
            "id": new_id,
            "destination": destination,
            "days": days,
            "itinerary_markdown": itinerary_markdown,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        self.past_itineraries.append(itinerary)
        self._save_itineraries()
        logger.info(f"過去旅程を保存: ID={new_id}, destination={destination}, days={days}")
        return new_id
    
    def get_itineraries(self, destination: Optional[str] = None, days: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        過去旅程を取得
        
        Args:
            destination: 目的地でフィルタ（オプション）
            days: 旅行日数でフィルタ（オプション）
            limit: 取得件数上限
        
        Returns:
            過去旅程リスト
        """
        result = self.past_itineraries.copy()
        if destination:
            result = [i for i in result if destination in i.get("destination", "")]
        if days:
            result = [i for i in result if i.get("days") == days]
        # 最新順にソート
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result[:limit]
    
    def get_itinerary(self, itinerary_id: int) -> Optional[Dict[str, Any]]:
        """特定の過去旅程を取得"""
        for itinerary in self.past_itineraries:
            if itinerary.get("id") == itinerary_id:
                return itinerary
        return None
    
    def remove_itinerary(self, itinerary_id: int) -> bool:
        """過去旅程を削除"""
        self.past_itineraries = [i for i in self.past_itineraries if i.get("id") != itinerary_id]
        self._save_itineraries()
        logger.info(f"過去旅程を削除: ID={itinerary_id}")
        return True
    
    # ============================================
    # RAG用の検索・取得
    # ============================================
    
    def search_relevant_knowledge(
        self, 
        destination: str, 
        themes: List[str] = None,
        days: int = None
    ) -> Dict[str, Any]:
        """
        目的地・テーマに関連するナレッジを検索（RAG用）
        
        Args:
            destination: 目的地
            themes: 興味テーマ
            days: 旅行日数
        
        Returns:
            関連するナレッジの辞書
        """
        relevant_knowledge = {
            "favorites": [],
            "memos": [],
            "past_itineraries": []
        }
        
        # お気に入りを検索
        favorites = self.get_favorites(location=destination)
        if themes:
            # テーマに関連するカテゴリのお気に入りを追加
            category_map = {
                "グルメ": "レストラン",
                "アート": "美術館",
                "歴史": "観光スポット",
                "自然": "観光スポット",
                "温泉": "ホテル",
                "ショッピング": "ショップ"
            }
            for theme in themes:
                category = category_map.get(theme, "観光スポット")
                theme_favorites = self.get_favorites(category=category, location=destination)
                favorites.extend(theme_favorites)
        # 重複を削除
        seen_ids = set()
        unique_favorites = []
        for f in favorites:
            if f.get("id") not in seen_ids:
                seen_ids.add(f.get("id"))
                unique_favorites.append(f)
        relevant_knowledge["favorites"] = unique_favorites[:10]  # 最大10件
        
        # 旅行メモを検索
        memos = self.get_memos(search_text=destination)
        if themes:
            for theme in themes:
                theme_memos = self.get_memos(tags=[theme])
                memos.extend(theme_memos)
        # 重複を削除
        seen_ids = set()
        unique_memos = []
        for m in memos:
            if m.get("id") not in seen_ids:
                seen_ids.add(m.get("id"))
                unique_memos.append(m)
        relevant_knowledge["memos"] = unique_memos[:5]  # 最大5件
        
        # 過去旅程を検索
        past_itineraries = self.get_itineraries(destination=destination, days=days, limit=3)
        relevant_knowledge["past_itineraries"] = past_itineraries
        
        logger.info(f"関連ナレッジを検索: destination={destination}, favorites={len(relevant_knowledge['favorites'])}, memos={len(relevant_knowledge['memos'])}, itineraries={len(relevant_knowledge['past_itineraries'])}")
        
        return relevant_knowledge
    
    def format_knowledge_for_prompt(self, knowledge: Dict[str, Any]) -> str:
        """
        ナレッジをプロンプト用のテキストに整形
        
        Args:
            knowledge: search_relevant_knowledge()の結果
        
        Returns:
            プロンプト用のテキスト
        """
        text_parts = []
        
        # お気に入りリスト
        if knowledge.get("favorites"):
            text_parts.append("## お気に入りリスト")
            for fav in knowledge["favorites"]:
                text_parts.append(f"- **{fav.get('name')}** ({fav.get('category')})")
                if fav.get("location"):
                    text_parts.append(f"  場所: {fav.get('location')}")
                if fav.get("notes"):
                    text_parts.append(f"  メモ: {fav.get('notes')}")
                if fav.get("url"):
                    text_parts.append(f"  URL: {fav.get('url')}")
            text_parts.append("")
        
        # 旅行メモ
        if knowledge.get("memos"):
            text_parts.append("## 旅行メモ")
            for memo in knowledge["memos"]:
                text_parts.append(f"- **{memo.get('title')}**")
                text_parts.append(f"  {memo.get('content', '')[:200]}")  # 最初の200文字
                if memo.get("tags"):
                    text_parts.append(f"  タグ: {', '.join(memo.get('tags', []))}")
            text_parts.append("")
        
        # 過去旅程
        if knowledge.get("past_itineraries"):
            text_parts.append("## 過去の旅程（参考）")
            for itin in knowledge["past_itineraries"]:
                text_parts.append(f"- **{itin.get('destination')} {itin.get('days')}日プラン** (作成日: {itin.get('created_at', '')[:10]})")
                # 旅程の一部を抜粋（最初の500文字）
                markdown = itin.get("itinerary_markdown", "")
                if markdown:
                    excerpt = markdown[:500].replace("\n", " ")
                    text_parts.append(f"  {excerpt}...")
            text_parts.append("")
        
        return "\n".join(text_parts) if text_parts else ""


# グローバルインスタンス
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """
    ナレッジベースインスタンスを取得（シングルトン）
    
    Returns:
        KnowledgeBaseインスタンス
    """
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base





