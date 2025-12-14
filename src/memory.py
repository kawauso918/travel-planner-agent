"""
メモリ管理モジュール（テンプレートv2.0準拠）
Memory運用（ON/OFF）を実装
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from langchain.memory import ConversationSummaryBufferMemory
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    ConversationSummaryBufferMemory = None
    ChatOpenAI = None
    LANGCHAIN_AVAILABLE = False

from src.config import MAX_TOKEN_LIMIT, OPENAI_API_KEY, OPENAI_MODEL


# ============================================
# 保存しない情報のルール（プライバシー保護）
# ============================================
"""
## 保存しない情報（テンプレートv2.0準拠）

以下の情報はプライバシー保護のため、Memoryに保存しません：

1. **個人識別情報**
   - 氏名（姓名、フルネーム）
   - 住所（都道府県、市区町村、番地など）
   - 連絡先（電話番号、メールアドレス）

2. **金融情報**
   - クレジットカード情報（カード番号、有効期限、CVV）
   - 銀行口座情報
   - 決済情報

3. **身分証明情報**
   - パスポート番号
   - 運転免許証番号
   - マイナンバー

4. **具体的な旅行日程**
   - 具体的な出発日・帰着日
   - 宿泊施設の詳細（住所、電話番号）
   - 予約番号

5. **その他の機密情報**
   - 健康情報（アレルギー等は「dietary」として保存可）
   - 家族構成の詳細
   - 職業・勤務先の詳細

## 保存する情報（user_preferences）

以下の情報のみを保存します：

- travel_style: 旅行スタイル（relaxed / normal / packed）
- interests: 興味・関心カテゴリ（リスト）
- mobility: 移動手段の好み（public / car / walk）
- budget_range: 予算感（low / medium / high）
- dislikes: 苦手なこと・避けたいこと（リスト）
- companions: 同行者の傾向（solo / couple / family / group）
- dietary: 食の制約（リスト、例: ["vegetarian", "halal"]）
"""


# ============================================
# 保存対象（preferences）の型定義
# ============================================

PREFERENCE_KEYS = {
    "travel_style": str,      # relaxed / normal / packed
    "interests": list,        # ["歴史", "グルメ"]
    "mobility": str,          # public / car / walk
    "budget_range": str,      # low / medium / high
    "dislikes": list,         # ["混雑", "長時間移動"]
    "companions": str,        # solo / couple / family / group
    "dietary": list           # ["vegetarian", "halal"]
}


class Memory:
    """
    会話履歴とコンテキストを管理するメモリクラス
    
    LangChainのConversationSummaryBufferMemoryを使用して
    会話履歴を管理し、トークン制限を超えた古い履歴を要約します。
    """
    
    def __init__(self, enabled: bool = True):
        """
        メモリを初期化
        
        Args:
            enabled: Memoryが有効かどうか
        """
        self.enabled = enabled
        self.user_preferences: Dict[str, Any] = {}
        
        if enabled and LANGCHAIN_AVAILABLE:
            # ConversationSummaryBufferMemoryを使用
            llm = ChatOpenAI(
                model_name=OPENAI_MODEL,
                openai_api_key=OPENAI_API_KEY,
                temperature=0
            ) if OPENAI_API_KEY else None
            
            if llm:
                self.memory = ConversationSummaryBufferMemory(
                    llm=llm,
                    max_token_limit=MAX_TOKEN_LIMIT,
                    return_messages=True
                )
            else:
                # APIキーがない場合は簡易版を使用
                self.memory = None
                self.conversation_history: List[Dict[str, Any]] = []
        else:
            # LangChainが使えない場合やenabled=Falseの場合は簡易版
            self.memory = None
            self.conversation_history: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str):
        """
        メッセージを履歴に追加
        
        Args:
            role: ロール（"user" または "assistant"）
            content: メッセージ内容
        """
        if not self.enabled:
            return
        
        if self.memory:
            # ConversationSummaryBufferMemoryを使用
            if role == "user":
                self.memory.chat_memory.add_user_message(content)
            elif role == "assistant":
                self.memory.chat_memory.add_ai_message(content)
        else:
            # 簡易版
            self.conversation_history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
    
    def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        最近の会話履歴を取得
        
        Args:
            limit: 取得件数
        
        Returns:
            会話履歴のリスト
        """
        if not self.enabled:
            return []
        
        if self.memory:
            # ConversationSummaryBufferMemoryから取得
            messages = self.memory.chat_memory.messages
            history = []
            for msg in messages[-limit:]:
                history.append({
                    "role": msg.type if hasattr(msg, 'type') else "unknown",
                    "content": msg.content if hasattr(msg, 'content') else str(msg)
                })
            return history
        else:
            # 簡易版
            return self.conversation_history[-limit:]
    
    def update_preferences(self, preferences: Dict[str, Any]):
        """
        ユーザーの好みを更新
        
        Args:
            preferences: 好みの辞書（PREFERENCE_KEYSに定義されたキーのみ保存）
        
        注意: 保存しない情報（氏名、住所、連絡先、カード情報等）は
              自動的に除外されます。
        """
        if not self.enabled:
            return
        
        # 保存対象のキーのみを抽出
        filtered_preferences = {}
        for key, value in preferences.items():
            if key in PREFERENCE_KEYS:
                # 型チェック（簡易版）
                expected_type = PREFERENCE_KEYS[key]
                if isinstance(value, expected_type) or (expected_type == list and isinstance(value, (list, tuple))):
                    filtered_preferences[key] = value
        
        self.user_preferences.update(filtered_preferences)
    
    def get_preferences(self) -> Dict[str, Any]:
        """
        ユーザーの好みを取得
        
        Returns:
            好みの辞書
        """
        if not self.enabled:
            return {}
        return self.user_preferences.copy()
    
    def clear_history(self):
        """会話履歴をクリア"""
        if not self.enabled:
            return
        
        if self.memory:
            self.memory.clear()
        else:
            self.conversation_history = []
    
    def clear_preferences(self):
        """ユーザーの好みをクリア"""
        if not self.enabled:
            return
        self.user_preferences = {}


def get_memory(enabled: bool) -> Optional[Memory]:
    """
    Memoryインスタンスを取得（ON/OFF対応）
    
    Args:
        enabled: Memoryが有効かどうか
            - True: ConversationSummaryBufferMemoryを使用
            - False: Noneを返す（Memory OFF）
    
    Returns:
        MemoryインスタンスまたはNone
    
    使用例:
        memory = get_memory(enabled=True)  # Memory ON
        if memory:
            memory.add_message("user", "京都に行きたい")
        
        memory = get_memory(enabled=False)  # Memory OFF
        # memory is None
    """
    if not enabled:
        return None
    
    return Memory(enabled=True)


