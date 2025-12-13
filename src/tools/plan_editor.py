"""
旅行計画編集ツール（Tool C）
既存旅程にユーザー指示を反映し、差分（change_log）を返す
"""
import re
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.prompts import SYSTEM_PROMPT
from src.schemas import PlanEditInput, PlanEditOutput
from src.logger import get_logger

logger = get_logger("plan_editor")


def edit_itinerary(input_data: PlanEditInput) -> Dict[str, Any]:
    """
    既存旅程にユーザー指示を反映して更新（Tool C）
    
    Args:
        input_data: PlanEditInputスキーマ
    
    Returns:
        PlanEditOutputスキーマに準拠した辞書
    """
    # APIキーがない場合
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEYが設定されていません")
        return _generate_fallback_edit_output(input_data, "OPENAI_API_KEYが設定されていません")
    
    try:
        logger.info(f"旅程編集開始: user_request長={len(input_data.user_request)}, current_plan長={len(input_data.current_plan)}")
        
        # LangChainのChatOpenAIを使用
        llm = ChatOpenAI(
            model_name=OPENAI_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.7
        )
        
        # プロンプトを構築
        prompt = _build_edit_prompt(input_data)
        logger.debug(f"プロンプト長: {len(prompt)}文字")
        
        # LLMにリクエスト
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        logger.debug("LLM呼び出しを開始")
        response = llm.invoke(messages)
        updated_plan = response.content
        logger.info(f"LLM呼び出し成功: 出力長={len(updated_plan)}文字")
        
        # 出力を解析してPlanEditOutputに変換
        output = _parse_edit_output(updated_plan, input_data)
        logger.info(f"旅程編集完了: change_log数={len(output.change_log)}, new_sources数={len(output.new_sources)}")
        
        return output.dict()
    
    except Exception as e:
        # エラー時はフォールバック出力を返す
        logger.error(f"旅程編集でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        return _generate_fallback_edit_output(input_data, f"LLM呼び出しエラー: {str(e)}")


def _build_edit_prompt(input_data: PlanEditInput) -> str:
    """
    旅程編集用のプロンプトを構築
    """
    current_plan = input_data.current_plan
    user_request = input_data.user_request
    additional_search = input_data.additional_search
    
    search_note = ""
    if additional_search:
        search_note = "\n\n【注意】additional_search=Trueが指定されています。必要に応じて追加の検索情報を参照してください（このTool内で検索を実行しても構いませんが、MVPでは省略可能です）。"
    
    prompt = f"""以下の旅行計画を編集してください。

## 現在の旅程

{current_plan}

---

## ユーザーの編集リクエスト

{user_request}
{search_note}

---

## 編集指示

1. **変更内容の明確化**:
   - ユーザーのリクエストに基づいて、具体的にどの部分を変更するか明確にしてください
   - 変更前後の差分を明確に示してください

2. **change_logの生成**:
   - 変更内容を簡潔に記録してください（最低1行以上）
   - 例：「Day1昼：「○○寺」→「△△神社」に変更」
   - 例：「Day2夜：「レストランA」を追加」
   - 例：「Day2午後を自然中心のプランに変更」

3. **Markdown構造の維持**:
   - 編集後の計画もテンプレートv2.0の順序（旅程→参照リンク→注意点→概算予算）を守ってください
   - 既存のMarkdown構造を崩さないでください

4. **出典URLの管理**:
   - 新規に追加した情報の出典URLがあれば、new_sourcesに記載してください
   - 既存のURLは維持してください

5. **注意事項**:
   - 検索していない情報を「最新」や「現在の情報」と断言しないでください
   - 不確かな情報は「要確認」と明記してください
   - 移動時間が3時間を超える場合は警告を追加してください

---

## 出力形式

以下の形式で出力してください：

```markdown
# 更新後の旅程（Markdown）

[編集後の旅程をMarkdown形式で記載]

---

## 変更履歴（change_log）

1. [変更内容1]
2. [変更内容2]
3. [変更内容3]

---

## 新規出典URL（new_sources）

- [URL1]（新規追加した情報の出典）
- [URL2]（新規追加した情報の出典）
```

上記の形式で、更新後の旅程、change_log、new_sourcesを生成してください。"""
    
    return prompt


def _parse_edit_output(updated_plan: str, input_data: PlanEditInput) -> PlanEditOutput:
    """
    LLMの出力を解析してPlanEditOutputに変換
    """
    # change_logセクションを抽出
    change_log = []
    change_log_pattern = r'## 変更履歴.*?\n(.*?)(?=\n---|\n##|$)'
    change_log_match = re.search(change_log_pattern, updated_plan, re.DOTALL)
    
    if change_log_match:
        change_log_text = change_log_match.group(1)
        # リストアイテムを抽出
        log_items = re.findall(r'^\d+\.\s*(.+)$', change_log_text, re.MULTILINE)
        change_log = [item.strip() for item in log_items if item.strip()]
    
    # change_logが空の場合は、変更内容を推定
    if not change_log:
        # ユーザーリクエストから簡易的なchange_logを生成
        user_request = input_data.user_request
        if "追加" in user_request or "加える" in user_request:
            change_log.append(f"ユーザーリクエストに基づいて項目を追加: {user_request[:50]}")
        elif "変更" in user_request or "変える" in user_request:
            change_log.append(f"ユーザーリクエストに基づいて変更: {user_request[:50]}")
        elif "削除" in user_request or "除く" in user_request:
            change_log.append(f"ユーザーリクエストに基づいて削除: {user_request[:50]}")
        else:
            change_log.append(f"ユーザーリクエストを反映: {user_request[:50]}")
    
    # new_sourcesセクションを抽出
    new_sources = []
    sources_pattern = r'## 新規出典URL.*?\n(.*?)(?=\n---|\n##|$)'
    sources_match = re.search(sources_pattern, updated_plan, re.DOTALL)
    
    if sources_match:
        sources_text = sources_match.group(1)
        # URLを抽出
        url_pattern = r'https?://[^\s\)\]]+'
        urls = re.findall(url_pattern, sources_text)
        new_sources = urls
    
    # 更新後の旅程から変更履歴セクションを削除（cleanなMarkdownを返す）
    clean_plan = updated_plan
    # プロンプトの指示テキストを削除
    clean_plan = re.sub(r'^## 更新後の旅程.*?\n', '', clean_plan, flags=re.MULTILINE)
    # 変更履歴セクションを削除
    clean_plan = re.sub(r'---\s*\n## 変更履歴.*?(?=\n---|\n##|$)', '', clean_plan, flags=re.DOTALL)
    # 新規出典URLセクションを削除
    clean_plan = re.sub(r'---\s*\n## 新規出典URL.*?(?=\n---|\n##|$)', '', clean_plan, flags=re.DOTALL)
    # 余分な空行を削除
    clean_plan = re.sub(r'\n{3,}', '\n\n', clean_plan)
    
    return PlanEditOutput(
        updated_plan=clean_plan.strip(),
        change_log=change_log,
        new_sources=new_sources
    )


def _generate_fallback_edit_output(input_data: PlanEditInput, error_msg: str) -> Dict[str, Any]:
    """
    フォールバック出力を生成（エラー時用）
    """
    current_plan = input_data.current_plan
    user_request = input_data.user_request
    
    # 最低限の変更ログを生成
    change_log = [f"エラーにより編集できませんでした: {error_msg}"]
    if user_request:
        change_log.append(f"ユーザーリクエスト: {user_request[:100]}")
    
    return PlanEditOutput(
        updated_plan=current_plan,  # 元の計画をそのまま返す
        change_log=change_log,
        new_sources=[]
    ).dict()


class PlanEditor:
    """旅行計画を編集するツール（後方互換性のため残す）"""
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.model = OPENAI_MODEL
    
    def edit(self, original_plan: Dict[str, Any], edit_request: str) -> Dict[str, Any]:
        """
        旅行計画を編集（後方互換性のため残す）
        
        Args:
            original_plan: 元の計画（TravelPlanスキーマまたは辞書）
            edit_request: 編集リクエスト
        
        Returns:
            TravelPlanResponseスキーマに準拠した編集後の計画
        """
        # TODO: 後で実装予定（既存のedit_itineraryを使用）
        pass
