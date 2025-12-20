"""
旅行計画生成ツール（Tool B）
検索要約（search_brief）を元に旅程Markdownを生成
"""
import json
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import OPENAI_API_KEY, OPENAI_MODEL, STYLE_CONFIG
from src.prompts import SYSTEM_PROMPT, DEVELOPER_PROMPT
from src.schemas import PlanGenerateInput, PlanGenerateOutput, SearchBrief
from src.logger import get_logger

logger = get_logger("plan_generator")


def generate_itinerary(input_data: PlanGenerateInput) -> Dict[str, Any]:
    """
    検索要約を元に旅程Markdownを生成（Tool B）
    
    Args:
        input_data: PlanGenerateInputスキーマ
    
    Returns:
        PlanGenerateOutputスキーマに準拠した辞書
    """
    # APIキーがない場合
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEYが設定されていません")
        return _generate_fallback_output(input_data, "OPENAI_API_KEYが設定されていません")
    
    try:
        logger.info(f"旅程生成開始: destination={input_data.destination}, days={input_data.days}, search_briefs={len(input_data.search_brief)}")
        
        # LangChainのChatOpenAIを使用
        llm = ChatOpenAI(
            model_name=OPENAI_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.7
        )
        
        # プロンプトを構築
        prompt = _build_itinerary_prompt(input_data)
        logger.debug(f"プロンプト長: {len(prompt)}文字")
        
        # LLMにリクエスト
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        logger.debug("LLM呼び出しを開始")
        response = llm.invoke(messages)
        itinerary_markdown = response.content
        logger.info(f"LLM呼び出し成功: 出力長={len(itinerary_markdown)}文字")
        
        # 出力を解析してPlanGenerateOutputに変換
        output = _parse_llm_output(itinerary_markdown, input_data)
        logger.info(f"旅程生成完了: sources数={len(output.sources)}, cautions数={len(output.cautions)}")
        
        return output.dict()
    
    except Exception as e:
        # エラー時はフォールバック出力を返す
        logger.error(f"旅程生成でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        return _generate_fallback_output(input_data, f"LLM呼び出しエラー: {str(e)}")


def _build_itinerary_prompt(input_data: PlanGenerateInput) -> str:
    """
    旅程生成用のプロンプトを構築
    """
    destination = input_data.destination
    days = input_data.days
    budget_total = input_data.budget_total or "未指定"
    themes = ", ".join(input_data.themes)
    style = input_data.style or "normal"
    style_desc = STYLE_CONFIG.get(style, {}).get("description", "標準")
    start_point = input_data.start_point or "未指定"
    mobility = input_data.mobility or "public"
    # constraintsを整形（参考情報を含む）
    constraints_list = []
    for constraint in input_data.constraints:
        if constraint.startswith("【参考情報】"):
            # 参考情報はそのまま追加
            constraints_list.append(constraint)
        else:
            constraints_list.append(constraint)
    constraints = "\n".join(constraints_list) if constraints_list else "なし"
    
    # search_briefを整形
    search_brief_text = ""
    if input_data.search_brief:
        search_brief_text = "\n\n## 検索結果要約（Search Brief）\n\n"
        for i, brief in enumerate(input_data.search_brief, 1):
            search_brief_text += f"### {i}. {brief.topic}\n"
            search_brief_text += f"**要約**: {brief.summary}\n"
            search_brief_text += f"**確度**: {brief.confidence}\n"
            search_brief_text += f"**出典URL**:\n"
            for url in brief.urls:
                search_brief_text += f"- {url}\n"
            search_brief_text += "\n"
    else:
        search_brief_text = "\n\n## 検索結果要約\n\n検索結果がありません。一般的な情報に基づいて提案しますが、すべて「要確認」と明記してください。\n"
    
    # 参考情報（RAG）を抽出
    reference_info = ""
    if "【参考情報】" in constraints:
        # 参考情報セクションを抽出
        parts = constraints.split("【参考情報】")
        if len(parts) > 1:
            reference_info = "\n\n## 参考情報（ユーザーのお気に入り・メモ・過去旅程）\n\n" + parts[1]
            constraints = parts[0].strip() if parts[0].strip() else "なし"
    
    prompt = f"""以下の情報を基に旅行旅程をMarkdown形式で作成してください。

## 入力条件

- **目的地**: {destination}
- **旅行日数**: {days}日
- **予算**: {budget_total}
- **興味テーマ**: {themes}
- **スタイル**: {style}（{style_desc}）
- **出発地点**: {start_point}
- **移動手段**: {mobility}
- **やりたいこと・希望事項**: {constraints}
{reference_info}
{search_brief_text}

## 出力形式（テンプレートv2.0準拠）

**重要：出力順序は必ず以下の順序を守ってください：**
1. 旅程（Day 1, Day 2...）
2. 参照リンク（📚 参照リンク）
3. 注意点・要確認事項（⚠️ 注意点・要確認事項）
4. 概算予算（💰 概算予算）

以下のMarkdown構造で出力してください：

```markdown
# {destination} {days}日プラン
**テーマ**: {themes}
**スタイル**: {style}（{style_desc}）

---

## 前提・仮定
- [不足情報があれば仮定を明記]

---

## Day 1: [テーマ名]

### 🌅 朝（9:00-12:00）
**[スポット名]**
- 概要: [説明]（[出典URL]より）
- 所要時間: 約[分数]分
- 料金: [金額]円（[出典URL]より）
- 📍 アクセス: [アクセス情報]（[地図リンク: https://www.google.com/maps/search/?api=1&query=スポット名+エリア]）
- ⚠️ [予約推奨/事前確認推奨など]
- 📚 参照: [出典URL]

### 🍽️ 昼（12:00-14:00）
**[レストラン名]**
- ジャンル: [ジャンル]
- 予算: [金額]円
- ⚠️ 予約推奨

### 🌆 夕（14:00-18:00）
[同様の形式]

### 🌙 夜（18:00-21:00）
[同様の形式]

---

## Day 2: [テーマ名]
[同様の形式で続く]

---

## 📚 参照リンク

1. [サイト名] - [URL]
2. [サイト名] - [URL]

---

## ⚠️ 注意点・要確認事項

- [注意点1]
- [注意点2]
- ⚠️ [移動時間が長い等の警告]

---

## 💰 概算予算

| 項目 | 金額 | 備考 |
|------|------|------|
| 交通 | ¥[金額] | [備考] |
| 食事 | ¥[金額] | 1日[回数]食想定 |
| 体験・入場 | ¥[金額] | |
| その他 | ¥[金額] | お土産・予備費 |
| **合計** | **¥[合計]** | |

---

*この旅程は[生成日時]時点の情報に基づいています。最新情報は各公式サイトでご確認ください。*
```

## 重要な注意事項

1. **検索結果の使用**:
   - search_briefがある場合は、その情報を優先的に使用してください
   - search_briefが少ない/空の場合は、一般的な提案をしつつ「要確認」と明記してください
   - **検索していない情報を「最新」や「現在の情報」と断言しないでください**

2. **参考情報（RAG）の活用**:
   - 参考情報セクションにユーザーのお気に入り・メモ・過去旅程がある場合は、積極的に活用してください
   - お気に入りリストのスポットやレストランを旅程に組み込むことを推奨します
   - 過去旅程の良い点を参考にしつつ、新しい提案も加えてください
   - 旅行メモの情報（混雑時間、注意点など）を旅程に反映してください

3. **出典URLの明記（引用の扱い）**:
   - 営業時間・料金・定休日などの重要情報には必ず出典URLを添えてください
   - 例：「金閣寺公式サイト（https://...）によると、営業時間は9:00-17:00です」
   - **検索結果（search_brief）に基づく情報は、必ず該当するURLを明記してください**
   - **検索していない情報を「最新」や「確実」と断言しないでください**
   - **各スポットの情報には、可能な限り引用元（URL）を紐付けてください**
   - 引用がない情報は「要確認」と明記してください
   - **引用元が見えるように、各スポットの説明に「（[出典URL]より）」や「📚 参照: [URL]」の形式で明記してください**
   - **最終出力の「📚 参照リンク」セクションに、使用したすべてのURLをリストアップしてください**

4. **移動時間の警告**:
   - 1日の移動総時間が3時間を超える場合は、warningsセクションに「DayXの移動時間が3時間超（推定）」と記載してください
   - MVPでは推定でOKですが、推定である旨をcautionsに明記してください

5. **予算内訳**:
   - transportation（交通費）
   - food（食事代）
   - activities（体験・入場料）
   - other（その他）
   - total（合計）

6. **エラーハンドリング**:
   - 情報が不確かな場合は「要確認」と明記
   - 矛盾情報がある場合は「情報源により異なります。公式サイトでの確認を推奨します」と記載

上記の形式でMarkdownを生成してください。"""
    
    return prompt


def _parse_llm_output(itinerary_markdown: str, input_data: PlanGenerateInput) -> PlanGenerateOutput:
    """
    LLMの出力を解析してPlanGenerateOutputに変換
    """
    # URLを抽出（sources用）
    import re
    url_pattern = r'https?://[^\s\)\]]+'
    urls = re.findall(url_pattern, itinerary_markdown)
    
    # search_briefからもURLを抽出（優先）
    for brief in input_data.search_brief:
        urls.extend(brief.urls)
    
    # URLの重複を削除
    from src.utils import dedupe_urls
    sources = dedupe_urls(urls) if urls else []
    
    # 警告を抽出（移動時間が3時間超など）
    warnings = []
    cautions = []
    
    # 移動時間の警告を検出
    if "移動時間が3時間" in itinerary_markdown or "移動時間が3時間超" in itinerary_markdown:
        # Day Xの移動時間が3時間超を検出
        day_pattern = r'Day\s*(\d+)'
        day_matches = re.findall(day_pattern, itinerary_markdown)
        for day in day_matches:
            warnings.append(f"Day{day}の移動時間が3時間超（推定）")
            cautions.append("移動時間は推定値です。実際の交通状況により変動する可能性があります。")
    
    # 要確認事項を抽出
    if "要確認" in itinerary_markdown:
        cautions.append("一部の情報は要確認です。公式サイトで最新情報をご確認ください。")
    
    # 予算内訳を抽出（Markdownテーブルから）
    budget_breakdown = _extract_budget_breakdown(itinerary_markdown, input_data)
    
    return PlanGenerateOutput(
        itinerary_markdown=itinerary_markdown,
        budget_breakdown=budget_breakdown,
        cautions=cautions,
        sources=sources,
        warnings=warnings
    )


def _extract_budget_breakdown(itinerary_markdown: str, input_data: PlanGenerateInput) -> Dict[str, Any]:
    """
    Markdownから予算内訳を抽出（簡易版）
    """
    import re
    
    budget_breakdown = {
        "transportation": 0,
        "food": 0,
        "activities": 0,
        "other": 0,
        "total": 0
    }
    
    # テーブルから数値を抽出
    # | 交通 | ¥15000 | ... |
    patterns = {
        "transportation": [r"交通[^|]*?¥(\d+)", r"交通費[^|]*?¥(\d+)"],
        "food": [r"食事[^|]*?¥(\d+)", r"食事代[^|]*?¥(\d+)"],
        "activities": [r"体験[^|]*?¥(\d+)", r"入場[^|]*?¥(\d+)"],
        "other": [r"その他[^|]*?¥(\d+)", r"予備[^|]*?¥(\d+)"],
        "total": [r"合計[^|]*?¥(\d+)", r"\*\*合計\*\*[^|]*?¥(\d+)"]
    }
    
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            try:
                match = re.search(pattern, itinerary_markdown, re.IGNORECASE)
                if match:
                    try:
                        budget_breakdown[key] = int(match.group(1).replace(",", ""))
                        break
                    except (ValueError, IndexError):
                        pass
            except re.error:
                # 正規表現エラーが発生した場合はスキップ
                pass
    
    # 予算が指定されている場合は合計を調整
    if input_data.budget_total:
        if isinstance(input_data.budget_total, int):
            if budget_breakdown["total"] == 0:
                # 合計が抽出できなかった場合、予算から推定
                budget_breakdown["total"] = input_data.budget_total
        elif isinstance(input_data.budget_total, str):
            # "5万円"のような文字列を数値に変換
            import re
            num_match = re.search(r'(\d+)', input_data.budget_total)
            if num_match:
                budget_breakdown["total"] = int(num_match.group(1))
    
    return budget_breakdown


def _generate_fallback_output(input_data: PlanGenerateInput, error_msg: str) -> Dict[str, Any]:
    """
    フォールバック出力を生成（エラー時用）
    """
    destination = input_data.destination
    days = input_data.days
    themes = ", ".join(input_data.themes)
    
    itinerary_markdown = f"""# {destination} {days}日プラン
**テーマ**: {themes}

---

## 前提・仮定
- エラーが発生したため、一般的な提案をします
- すべての情報は要確認です

---

## Day 1: {themes.split(',')[0] if themes else '観光'}

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

- エラー: {error_msg}
- すべての情報は要確認です
- 公式サイトで最新情報をご確認ください

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

*この旅程はエラーにより生成されました。すべての情報は要確認です。*
"""
    
    return PlanGenerateOutput(
        itinerary_markdown=itinerary_markdown,
        budget_breakdown={
            "transportation": 0,
            "food": 0,
            "activities": 0,
            "other": 0,
            "total": 0
        },
        cautions=[f"エラー: {error_msg}", "すべての情報は要確認です"],
        sources=[],
        warnings=["エラーにより正確な情報が取得できませんでした"]
    ).dict()


class PlanGenerator:
    """旅行計画を生成するツール（後方互換性のため残す）"""
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.model = OPENAI_MODEL
    
    def generate(self, destination: str, duration: int, budget: int, search_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        旅行計画を生成（後方互換性のため残す）
        
        Args:
            destination: 目的地
            duration: 滞在日数
            budget: 予算
            search_results: 検索結果（オプション）
        
        Returns:
            TravelPlanResponseスキーマに準拠した辞書
        """
        # TODO: 後で実装予定（既存のgenerate_itineraryを使用）
        pass





