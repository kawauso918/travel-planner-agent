# コード評価レポート

## 📊 評価サマリー

- **コード品質**: ⭐⭐⭐⭐ (4/5)
- **エラーハンドリング**: ⭐⭐⭐⭐⭐ (5/5)
- **保守性**: ⭐⭐⭐⭐ (4/5)
- **セキュリティ**: ⭐⭐⭐⭐⭐ (5/5)
- **パフォーマンス**: ⭐⭐⭐ (3/5)

## ✅ 良い点

1. **適切なエラーハンドリング**: すべての主要処理でtry-exceptが実装されている
2. **ログ出力**: デプロイ後の問題追跡が可能
3. **型安全性**: Pydanticスキーマによる厳密な型チェック
4. **機密情報の保護**: APIキーのマスク機能
5. **フォールバック機能**: エラー時もユーザーに結果を返す

## 🔧 改善が必要な箇所

### 1. **型ヒントの一貫性** (優先度: 中)

**問題**: 一部の関数で型ヒントが不完全

**改善案**:
```python
# 改善前
def _create_search_brief(topic: str, query: str, search_result: Dict[str, Any]) -> Optional[SearchBrief]:

# 改善後（より具体的な型）
def _create_search_brief(
    topic: str, 
    query: str, 
    search_result: WebSearchResponse
) -> Optional[SearchBrief]:
```

### 2. **重複コードの削減** (優先度: 高)

**問題**: `app.py`でエラーハンドリングが重複している

**改善案**: 共通のエラーハンドラ関数を作成

```python
def _handle_error(e: Exception, context: str) -> None:
    """共通のエラーハンドリング"""
    logger.error(f"{context}でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
    st.error(f"❌ エラーが発生しました: {str(e)}")
    st.info("💡 別の条件で再試行するか、しばらく時間をおいてから再度お試しください。")
    with st.expander("エラー詳細（開発者向け）"):
        st.exception(e)
```

### 3. **入力検証の強化** (優先度: 中)

**問題**: ユーザー入力の検証が不十分

**改善案**: Pydanticモデルで入力検証

```python
from pydantic import BaseModel, Field, validator

class UserInput(BaseModel):
    destination: str = Field(..., min_length=1, max_length=100)
    days: int = Field(..., ge=1, le=30)
    budget_total: Optional[int] = Field(None, ge=0)
    
    @validator('destination')
    def validate_destination(cls, v):
        if not v.strip():
            raise ValueError('目的地が空です')
        return v.strip()
```

### 4. **非同期処理の検討** (優先度: 低)

**問題**: 長時間の処理でUIがブロックされる可能性

**改善案**: Streamlitの非同期処理やプログレスバーの改善

### 5. **キャッシュ機能の追加** (優先度: 中)

**問題**: 同じクエリで複数回検索が発生する可能性

**改善案**: 
```python
from functools import lru_cache
from datetime import timedelta

@lru_cache(maxsize=100)
def cached_search(query: str, cache_duration: int = 3600):
    """検索結果をキャッシュ（1時間）"""
    # 実装
```

### 6. **設定の外部化** (優先度: 低)

**問題**: 一部の設定がハードコードされている

**改善案**: 設定ファイル（YAML/JSON）から読み込み

## 🚀 追加できる機能

### 1. **旅程のエクスポート機能** (優先度: 高)

**要件**:
- PDF形式でのエクスポート
- カレンダー形式（.ics）でのエクスポート
- Markdownファイルとして保存

**実装例**:
```python
def export_to_pdf(itinerary_markdown: str) -> bytes:
    """旅程をPDF形式でエクスポート"""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    # 実装
```

### 2. **旅程の比較機能** (優先度: 中)

**要件**:
- 複数の旅程案を並べて比較
- 差分のハイライト表示

### 3. **お気に入り機能** (優先度: 中)

**要件**:
- 生成した旅程を保存
- 過去の旅程を参照・再利用

### 4. **リアルタイム検索進捗表示** (優先度: 低)

**要件**:
- 検索の進捗をリアルタイムで表示
- どのトピックを検索中か表示

### 5. **多言語対応** (優先度: 低)

**要件**:
- 英語版のUI
- 多言語での旅程生成

## 📝 具体的な改善コード

### 改善1: エラーハンドラの共通化

```python
# app.py に追加
def _handle_error(e: Exception, context: str, user_message: str = None) -> None:
    """
    共通のエラーハンドリング
    
    Args:
        e: 例外オブジェクト
        context: エラーが発生したコンテキスト（例: "旅程生成"）
        user_message: ユーザー向けのカスタムメッセージ
    """
    logger.error(f"{context}でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
    st.error(f"❌ エラーが発生しました: {str(e)}")
    
    if user_message:
        st.info(user_message)
    else:
        st.info("💡 別の条件で再試行するか、しばらく時間をおいてから再度お試しください。")
    
    with st.expander("エラー詳細（開発者向け）"):
        st.exception(e)
```

### 改善2: 入力検証の強化

```python
# src/schemas.py に追加
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class UserInputSchema(BaseModel):
    """ユーザー入力の検証スキーマ"""
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
        if not v or not v.strip():
            raise ValueError('目的地が空です')
        return v.strip()
    
    @validator('style')
    def validate_style(cls, v):
        allowed = ['relaxed', 'normal', 'packed']
        if v not in allowed:
            raise ValueError(f'スタイルは {allowed} のいずれかである必要があります')
        return v
    
    @validator('mobility')
    def validate_mobility(cls, v):
        allowed = ['public', 'car', 'walk']
        if v not in allowed:
            raise ValueError(f'移動手段は {allowed} のいずれかである必要があります')
        return v
```

### 改善3: キャッシュ機能

```python
# src/utils.py に追加
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib
import json

class SearchCache:
    """検索結果のキャッシュ管理"""
    
    def __init__(self, cache_duration_hours: int = 1):
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cache: Dict[str, tuple] = {}  # {hash: (result, timestamp)}
    
    def _get_cache_key(self, query: str, location: str) -> str:
        """キャッシュキーを生成"""
        key_str = f"{query}:{location}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, query: str, location: str) -> Optional[Dict[str, Any]]:
        """キャッシュから取得"""
        key = self._get_cache_key(query, location)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.cache_duration:
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, query: str, location: str, result: Dict[str, Any]) -> None:
        """キャッシュに保存"""
        key = self._get_cache_key(query, location)
        self.cache[key] = (result, datetime.now())

# グローバルキャッシュインスタンス
search_cache = SearchCache(cache_duration_hours=1)
```

## 🎯 優先度別の実装順序

### 高優先度（すぐに実装推奨）
1. ✅ エラーハンドラの共通化
2. ✅ 入力検証の強化
3. ✅ 旅程のエクスポート機能

### 中優先度（次期リリースで実装）
4. キャッシュ機能の追加
5. 旅程の比較機能
6. お気に入り機能

### 低優先度（将来の拡張）
7. 非同期処理の改善
8. リアルタイム検索進捗表示
9. 多言語対応

## 📌 その他の推奨事項

1. **テストコードの追加**: 単体テスト・統合テストの実装
2. **CI/CDの導入**: GitHub Actionsでの自動テスト・デプロイ
3. **ドキュメントの充実**: APIドキュメント（Sphinx等）の生成
4. **パフォーマンステスト**: 負荷テストの実施
5. **セキュリティ監査**: 脆弱性スキャンの実施
