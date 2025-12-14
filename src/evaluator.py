"""
LLM as a Judgeによる評価モジュール
スコア評価と回答比較評価を実装
"""
import json
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.prompts import EVALUATION_PROMPT, COMPARISON_EVALUATION_PROMPT, QA_REVIEW_PROMPT, PLAN_COMPARISON_PROMPT
from src.schemas import QAReviewResult, QAEvaluationIssue, PlanComparisonResult, ComparisonReason
from src.logger import get_logger

logger = get_logger("evaluator")


def evaluate_plan_score(
    plan: Dict[str, Any],
    user_requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """
    スコアによる評価を実行
    
    Args:
        plan: 評価対象の旅行計画（PlanGenerateOutput形式）
        user_requirements: ユーザーの要求条件
            - destination: 目的地
            - days: 日数
            - budget_total: 予算
            - themes: テーマリスト
            - style: スタイル
            - constraints: 制約条件
    
    Returns:
        評価結果の辞書
        {
            "overall_score": float,  # 総合スコア（0-100）
            "scores": {
                "appropriateness": float,  # 適切性（0-100）
                "feasibility": float,      # 実現可能性（0-100）
                "accuracy": float,         # 情報の正確性（0-100）
                "completeness": float,     # 構造の完全性（0-100）
                "budget_validity": float,  # 予算の妥当性（0-100）
                "warnings_adequacy": float # 注意点の適切性（0-100）
            },
            "feedback": str,  # フィードバック
            "strengths": List[str],  # 強み
            "improvements": List[str]  # 改善点
        }
    """
    try:
        logger.info("スコア評価を開始")
        
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEYが設定されていません")
            return _generate_fallback_evaluation("APIキーが設定されていません")
        
        # LLMを初期化
        llm = ChatOpenAI(
            model_name=OPENAI_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.3  # 評価は一貫性が重要なので低め
        )
        
        # プロンプトを構築
        prompt = _build_score_evaluation_prompt(plan, user_requirements)
        
        # LLMにリクエスト
        messages = [
            SystemMessage(content=EVALUATION_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        logger.debug("LLM呼び出しを開始（スコア評価）")
        response = llm.invoke(messages)
        evaluation_text = response.content
        
        # 評価結果をパース
        evaluation_result = _parse_evaluation_result(evaluation_text)
        logger.info(f"スコア評価完了: 総合スコア={evaluation_result.get('overall_score', 0)}")
        
        return evaluation_result
    
    except Exception as e:
        logger.error(f"スコア評価でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        return _generate_fallback_evaluation(f"評価エラー: {str(e)}")


def evaluate_plan_comparison(
    plans: List[Dict[str, Any]],
    user_requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """
    回答比較による評価を実行（5つの回答を比較）
    
    Args:
        plans: 評価対象の旅行計画リスト（最大5つ、PlanGenerateOutput形式）
        user_requirements: ユーザーの要求条件
    
    Returns:
        比較評価結果の辞書
        {
            "rankings": [
                {
                    "plan_id": int,  # 計画のインデックス（0-4）
                    "rank": int,     # 順位（1-5）
                    "score": float,  # スコア（0-100）
                    "reason": str    # 順位の理由
                },
                ...
            ],
            "best_plan_id": int,  # 最良の計画のID
            "comparison_summary": str,  # 比較サマリー
            "detailed_comparison": Dict[str, Any]  # 詳細比較
        }
    """
    try:
        logger.info(f"回答比較評価を開始: 計画数={len(plans)}")
        
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEYが設定されていません")
            return _generate_fallback_comparison("APIキーが設定されていません")
        
        # 計画数が5つでない場合は警告
        if len(plans) != 5:
            logger.warning(f"計画数が5つではありません: {len(plans)}")
        
        # LLMを初期化
        llm = ChatOpenAI(
            model_name=OPENAI_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.3
        )
        
        # プロンプトを構築
        prompt = _build_comparison_evaluation_prompt(plans, user_requirements)
        
        # LLMにリクエスト
        messages = [
            SystemMessage(content=COMPARISON_EVALUATION_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        logger.debug("LLM呼び出しを開始（比較評価）")
        response = llm.invoke(messages)
        comparison_text = response.content
        
        # 比較結果をパース
        comparison_result = _parse_comparison_result(comparison_text, len(plans))
        logger.info(f"回答比較評価完了: 最良計画ID={comparison_result.get('best_plan_id', -1)}")
        
        return comparison_result
    
    except Exception as e:
        logger.error(f"回答比較評価でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        return _generate_fallback_comparison(f"評価エラー: {str(e)}")


def _build_score_evaluation_prompt(
    plan: Dict[str, Any],
    user_requirements: Dict[str, Any]
) -> str:
    """スコア評価用のプロンプトを構築"""
    
    plan_text = plan.get("itinerary_markdown", "")
    budget_breakdown = plan.get("budget_breakdown", {})
    sources = plan.get("sources", [])
    cautions = plan.get("cautions", [])
    warnings = plan.get("warnings", [])
    
    requirements_text = f"""
目的地: {user_requirements.get('destination', '未指定')}
日数: {user_requirements.get('days', '未指定')}日
予算: {user_requirements.get('budget_total', '未指定')}円
テーマ: {', '.join(user_requirements.get('themes', []))}
スタイル: {user_requirements.get('style', '未指定')}
制約条件: {', '.join(user_requirements.get('constraints', []))}
"""
    
    prompt = f"""以下の旅行計画を評価してください。

## ユーザー要求条件
{requirements_text}

## 評価対象の旅行計画
{plan_text}

## 予算内訳
{json.dumps(budget_breakdown, ensure_ascii=False, indent=2) if budget_breakdown else "なし"}

## 参照リンク
{chr(10).join([f"- {s}" for s in sources]) if sources else "なし"}

## 注意点
{chr(10).join([f"- {c}" for c in cautions]) if cautions else "なし"}

## 警告
{chr(10).join([f"- {w}" for w in warnings]) if warnings else "なし"}

---

## 評価指示

以下の6つの観点で評価し、各観点について0-100点のスコアを付けてください。

1. **適切性（Appropriateness）**: ユーザーの要求条件（目的地、日数、予算、テーマ、スタイル、制約条件）への適合度
2. **実現可能性（Feasibility）**: 移動時間、営業時間、アクセス方法などの現実性
3. **情報の正確性（Accuracy）**: 出典の有無、最新性、信頼性
4. **構造の完全性（Completeness）**: テンプレートv2.0準拠（旅程→参照リンク→注意点→概算予算の順序）
5. **予算の妥当性（Budget Validity）**: 予算内訳の妥当性、予算オーバーの有無
6. **注意点の適切性（Warnings Adequacy）**: 注意点・警告の適切性、不足している注意点の有無

## 出力形式

以下のJSON形式で出力してください：

```json
{{
    "overall_score": 85.5,
    "scores": {{
        "appropriateness": 90,
        "feasibility": 85,
        "accuracy": 80,
        "completeness": 90,
        "budget_validity": 85,
        "warnings_adequacy": 80
    }},
    "feedback": "総合的な評価コメント",
    "strengths": ["強み1", "強み2", "強み3"],
    "improvements": ["改善点1", "改善点2", "改善点3"]
}}
```

上記の形式で、評価結果を出力してください。"""
    
    return prompt


def _build_comparison_evaluation_prompt(
    plans: List[Dict[str, Any]],
    user_requirements: Dict[str, Any]
) -> str:
    """比較評価用のプロンプトを構築"""
    
    requirements_text = f"""
目的地: {user_requirements.get('destination', '未指定')}
日数: {user_requirements.get('days', '未指定')}日
予算: {user_requirements.get('budget_total', '未指定')}円
テーマ: {', '.join(user_requirements.get('themes', []))}
スタイル: {user_requirements.get('style', '未指定')}
制約条件: {', '.join(user_requirements.get('constraints', []))}
"""
    
    plans_text = ""
    for i, plan in enumerate(plans):
        plan_text = plan.get("itinerary_markdown", "")
        budget_breakdown = plan.get("budget_breakdown", {})
        sources = plan.get("sources", [])
        cautions = plan.get("cautions", [])
        
        plans_text += f"""
## 計画 {i+1} (ID: {i})

### 旅程
{plan_text}

### 予算内訳
{json.dumps(budget_breakdown, ensure_ascii=False, indent=2) if budget_breakdown else "なし"}

### 参照リンク
{chr(10).join([f"- {s}" for s in sources]) if sources else "なし"}

### 注意点
{chr(10).join([f"- {c}" for c in cautions]) if cautions else "なし"}

---
"""
    
    prompt = f"""以下の5つの旅行計画を比較評価してください。

## ユーザー要求条件
{requirements_text}

{plans_text}

## 評価指示

以下の6つの観点で各計画を評価し、1位から5位まで順位付けしてください。

1. **適切性（Appropriateness）**: ユーザーの要求条件への適合度
2. **実現可能性（Feasibility）**: 移動時間、営業時間などの現実性
3. **情報の正確性（Accuracy）**: 出典の有無、最新性、信頼性
4. **構造の完全性（Completeness）**: テンプレートv2.0準拠
5. **予算の妥当性（Budget Validity）**: 予算内訳の妥当性
6. **注意点の適切性（Warnings Adequacy）**: 注意点・警告の適切性

## 出力形式

以下のJSON形式で出力してください：

```json
{{
    "rankings": [
        {{
            "plan_id": 0,
            "rank": 1,
            "score": 90.5,
            "reason": "順位の理由"
        }},
        {{
            "plan_id": 1,
            "rank": 2,
            "score": 85.0,
            "reason": "順位の理由"
        }},
        ...
    ],
    "best_plan_id": 0,
    "comparison_summary": "比較サマリー",
    "detailed_comparison": {{
        "appropriateness": {{
            "best": 0,
            "scores": [90, 85, 80, 75, 70]
        }},
        "feasibility": {{
            "best": 0,
            "scores": [85, 80, 75, 70, 65]
        }},
        ...
    }}
}}
```

上記の形式で、比較評価結果を出力してください。"""
    
    return prompt


def _parse_evaluation_result(evaluation_text: str) -> Dict[str, Any]:
    """評価結果をパース"""
    try:
        # JSON部分を抽出
        json_start = evaluation_text.find("{")
        json_end = evaluation_text.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning("JSONが見つかりませんでした")
            return _generate_fallback_evaluation("評価結果のパースに失敗しました")
        
        json_text = evaluation_text[json_start:json_end]
        result = json.loads(json_text)
        
        # 必須フィールドの検証
        if "overall_score" not in result:
            result["overall_score"] = 0.0
        if "scores" not in result:
            result["scores"] = {}
        if "feedback" not in result:
            result["feedback"] = "評価結果が取得できませんでした"
        if "strengths" not in result:
            result["strengths"] = []
        if "improvements" not in result:
            result["improvements"] = []
        
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"JSONパースエラー: {e}")
        return _generate_fallback_evaluation(f"JSONパースエラー: {str(e)}")
    except Exception as e:
        logger.error(f"評価結果のパースエラー: {e}")
        return _generate_fallback_evaluation(f"パースエラー: {str(e)}")


def _parse_comparison_result(comparison_text: str, num_plans: int) -> Dict[str, Any]:
    """比較結果をパース"""
    try:
        # JSON部分を抽出
        json_start = comparison_text.find("{")
        json_end = comparison_text.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning("JSONが見つかりませんでした")
            return _generate_fallback_comparison("比較結果のパースに失敗しました")
        
        json_text = comparison_text[json_start:json_end]
        result = json.loads(json_text)
        
        # 必須フィールドの検証
        if "rankings" not in result:
            result["rankings"] = []
        if "best_plan_id" not in result:
            result["best_plan_id"] = 0
        if "comparison_summary" not in result:
            result["comparison_summary"] = "比較結果が取得できませんでした"
        if "detailed_comparison" not in result:
            result["detailed_comparison"] = {}
        
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"JSONパースエラー: {e}")
        return _generate_fallback_comparison(f"JSONパースエラー: {str(e)}")
    except Exception as e:
        logger.error(f"比較結果のパースエラー: {e}")
        return _generate_fallback_comparison(f"パースエラー: {str(e)}")


def _generate_fallback_evaluation(error_message: str) -> Dict[str, Any]:
    """フォールバック評価結果を生成"""
    return {
        "overall_score": 0.0,
        "scores": {
            "appropriateness": 0.0,
            "feasibility": 0.0,
            "accuracy": 0.0,
            "completeness": 0.0,
            "budget_validity": 0.0,
            "warnings_adequacy": 0.0
        },
        "feedback": f"評価を実行できませんでした: {error_message}",
        "strengths": [],
        "improvements": []
    }


def _generate_fallback_comparison(error_message: str) -> Dict[str, Any]:
    """フォールバック比較結果を生成"""
    return {
        "rankings": [],
        "best_plan_id": -1,
        "comparison_summary": f"比較評価を実行できませんでした: {error_message}",
        "detailed_comparison": {}
    }


def evaluate_plan_qa_review(
    user_request: Dict[str, Any],
    generated_plan: Dict[str, Any],
    search_brief: List[Dict[str, Any]],
    sources: List[str]
) -> Dict[str, Any]:
    """
    QAレビューによる評価を実行（厳格なQAレビュアー）
    
    Args:
        user_request: ユーザー条件
            - destination: 目的地
            - days: 日数
            - budget_total: 予算
            - themes: テーマリスト
            - style: スタイル
            - constraints: 制約条件
        generated_plan: 生成された旅行プラン（PlanGenerateOutput形式）
        search_brief: 検索要約（Search Brief）リスト
        sources: 参照URL一覧
    
    Returns:
        QAレビュー結果の辞書
        {
            "scores": {
                "正確性": 1-5,
                "実現可能性": 1-5,
                "テーマ整合性": 1-5,
                "根拠の明示": 1-5,
                "予算妥当性": 1-5,
                "出力品質": 1-5
            },
            "total_30": 0-30,
            "total_100": 0-100,
            "good_points": ["良い点を最大3つ"],
            "issues": [
                {
                    "severity": "high|medium|low",
                    "problem": "問題点（具体的）",
                    "evidence": "どの部分が問題か",
                    "fix": "どう直せば良いか"
                }
            ],
            "must_fix_first": ["優先度が最も高い修正点を最大3つ"],
            "rewrite_suggestions": ["改善の方向性（最大3つ）"]
        }
    """
    try:
        logger.info("QAレビュー評価を開始")
        
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEYが設定されていません")
            return _generate_fallback_qa_review("APIキーが設定されていません")
        
        # LLMを初期化
        llm = ChatOpenAI(
            model_name=OPENAI_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.2  # QAレビューは厳格性が重要なので低め
        )
        
        # プロンプトを構築
        prompt = _build_qa_review_prompt(user_request, generated_plan, search_brief, sources)
        
        # LLMにリクエスト
        messages = [
            SystemMessage(content=QA_REVIEW_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        logger.debug("LLM呼び出しを開始（QAレビュー）")
        response = llm.invoke(messages)
        review_text = response.content
        
        # 評価結果をパース
        review_result = _parse_qa_review_result(review_text)
        logger.info(f"QAレビュー評価完了: 総合スコア={review_result.get('total_100', 0)}")
        
        return review_result
    
    except Exception as e:
        logger.error(f"QAレビュー評価でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        return _generate_fallback_qa_review(f"評価エラー: {str(e)}")


def _build_qa_review_prompt(
    user_request: Dict[str, Any],
    generated_plan: Dict[str, Any],
    search_brief: List[Dict[str, Any]],
    sources: List[str]
) -> str:
    """QAレビュー用のプロンプトを構築"""
    
    # ユーザー条件を整形
    user_request_text = f"""
目的地: {user_request.get('destination', '未指定')}
日数: {user_request.get('days', '未指定')}日
予算: {user_request.get('budget_total', '未指定')}円
テーマ: {', '.join(user_request.get('themes', []))}
スタイル: {user_request.get('style', '未指定')}
制約条件: {', '.join(user_request.get('constraints', []))}
"""
    
    # 生成された旅行プランを整形
    generated_plan_text = generated_plan.get("itinerary_markdown", "")
    budget_breakdown = generated_plan.get("budget_breakdown", {})
    cautions = generated_plan.get("cautions", [])
    warnings = generated_plan.get("warnings", [])
    
    # 検索要約を整形
    search_brief_text = ""
    if search_brief:
        for i, brief in enumerate(search_brief, 1):
            topic = brief.get('topic', '')
            summary = brief.get('summary', '')
            urls = brief.get('urls', [])
            confidence = brief.get('confidence', '')
            search_brief_text += f"""
### {i}. {topic}
要約: {summary}
確度: {confidence}
出典URL: {', '.join(urls) if urls else 'なし'}
"""
    else:
        search_brief_text = "検索要約がありません。"
    
    # 参照URL一覧
    sources_text = "\n".join([f"- {s}" for s in sources]) if sources else "参照URLがありません。"
    
    prompt = f"""# 評価対象

## 【ユーザー条件】
{user_request_text}

## 【生成された旅行プラン】
{generated_plan_text}

## 【予算内訳】
{json.dumps(budget_breakdown, ensure_ascii=False, indent=2) if budget_breakdown else "なし"}

## 【注意点】
{chr(10).join([f"- {c}" for c in cautions]) if cautions else "なし"}

## 【警告】
{chr(10).join([f"- {w}" for w in warnings]) if warnings else "なし"}

## 【データソース（検索要約 / Search Brief）】
{search_brief_text}

## 【参照URL一覧（あれば）】
{sources_text}

---

上記の情報を基に、厳格なQAレビューを実施してください。
データソースに根拠がない「最新」「確実」などの断言は減点してください。
営業時間/料金/予約要否/アクセス等の重要情報があるのにURL根拠がない場合は減点してください。
移動が過密、時間帯が矛盾、予算が明らかに超過など「実現不能」な点は大きく減点してください。
不確実な点を「要確認」と明記していれば加点してください。

JSONのみを出力してください。"""
    
    return prompt


def _parse_qa_review_result(review_text: str) -> Dict[str, Any]:
    """QAレビュー結果をパース"""
    try:
        # JSON部分を抽出
        json_start = review_text.find("{")
        json_end = review_text.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning("JSONが見つかりませんでした")
            return _generate_fallback_qa_review("評価結果のパースに失敗しました")
        
        json_text = review_text[json_start:json_end]
        result = json.loads(json_text)
        
        # 必須フィールドの検証とデフォルト値設定
        if "scores" not in result:
            result["scores"] = {
                "正確性": 3,
                "実現可能性": 3,
                "テーマ整合性": 3,
                "根拠の明示": 3,
                "予算妥当性": 3,
                "出力品質": 3
            }
        
        # total_30を計算（scoresの合計）
        if "total_30" not in result:
            scores = result.get("scores", {})
            result["total_30"] = sum(scores.values()) if isinstance(scores, dict) else 18
        
        # total_100を計算（30点満点を100点に換算）
        if "total_100" not in result:
            total_30 = result.get("total_30", 18)
            result["total_100"] = round((total_30 / 30) * 100, 1)
        
        # その他のフィールドのデフォルト値
        if "good_points" not in result:
            result["good_points"] = []
        if "issues" not in result:
            result["issues"] = []
        if "must_fix_first" not in result:
            result["must_fix_first"] = []
        if "rewrite_suggestions" not in result:
            result["rewrite_suggestions"] = []
        
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"JSONパースエラー: {e}")
        logger.debug(f"パース対象テキスト: {review_text[:500]}")
        return _generate_fallback_qa_review(f"JSONパースエラー: {str(e)}")
    except Exception as e:
        logger.error(f"QAレビュー結果のパースエラー: {e}")
        return _generate_fallback_qa_review(f"パースエラー: {str(e)}")


def _generate_fallback_qa_review(error_message: str) -> Dict[str, Any]:
    """フォールバックQAレビュー結果を生成"""
    return {
        "scores": {
            "正確性": 3,
            "実現可能性": 3,
            "テーマ整合性": 3,
            "根拠の明示": 3,
            "予算妥当性": 3,
            "出力品質": 3
        },
        "total_30": 18,
        "total_100": 60.0,
        "good_points": [],
        "issues": [
            {
                "severity": "high",
                "problem": f"評価を実行できませんでした: {error_message}",
                "evidence": "評価システムのエラー",
                "fix": "評価システムを再実行してください"
            }
        ],
        "must_fix_first": [f"評価エラーを解決: {error_message}"],
        "rewrite_suggestions": []
    }


def compare_two_plans(
    user_request: Dict[str, Any],
    answer_a: Dict[str, Any],
    answer_b: Dict[str, Any],
    search_brief: List[Dict[str, Any]],
    sources: List[str]
) -> Dict[str, Any]:
    """
    2つの旅行プランを比較評価する
    
    Args:
        user_request: ユーザー条件
            - destination: 目的地
            - days: 日数
            - budget_total: 予算
            - themes: テーマリスト
            - style: スタイル
            - constraints: 制約条件
        answer_a: 回答A（PlanGenerateOutput形式）
        answer_b: 回答B（PlanGenerateOutput形式）
        search_brief: 検索要約（Search Brief）リスト
        sources: 参照URL一覧
    
    Returns:
        比較結果の辞書
        {
            "winner": "A|B|tie",
            "reason_summary": "2〜4文で要点",
            "detailed_reasons": [
                {
                    "criterion": "正確性",
                    "better": "A|B|tie",
                    "why": "..."
                },
                ...
            ],
            "suggested_merge": "AとBの良いところを統合するならどうするか（短く）"
        }
    """
    try:
        logger.info("2つのプラン比較評価を開始")
        
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEYが設定されていません")
            return _generate_fallback_comparison_two("APIキーが設定されていません")
        
        # LLMを初期化
        llm = ChatOpenAI(
            model_name=OPENAI_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=0.2  # 比較評価は一貫性が重要なので低め
        )
        
        # プロンプトを構築
        prompt = _build_plan_comparison_prompt(user_request, answer_a, answer_b, search_brief, sources)
        
        # LLMにリクエスト
        messages = [
            SystemMessage(content=PLAN_COMPARISON_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        logger.debug("LLM呼び出しを開始（2つのプラン比較）")
        response = llm.invoke(messages)
        comparison_text = response.content
        
        # 比較結果をパース
        comparison_result = _parse_plan_comparison_result(comparison_text)
        logger.info(f"2つのプラン比較評価完了: 勝者={comparison_result.get('winner', 'unknown')}")
        
        return comparison_result
    
    except Exception as e:
        logger.error(f"2つのプラン比較評価でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        return _generate_fallback_comparison_two(f"評価エラー: {str(e)}")


def _build_plan_comparison_prompt(
    user_request: Dict[str, Any],
    answer_a: Dict[str, Any],
    answer_b: Dict[str, Any],
    search_brief: List[Dict[str, Any]],
    sources: List[str]
) -> str:
    """プラン比較用のプロンプトを構築"""
    
    # ユーザー条件を整形
    user_request_text = f"""
目的地: {user_request.get('destination', '未指定')}
日数: {user_request.get('days', '未指定')}日
予算: {user_request.get('budget_total', '未指定')}円
テーマ: {', '.join(user_request.get('themes', []))}
スタイル: {user_request.get('style', '未指定')}
制約条件: {', '.join(user_request.get('constraints', []))}
"""
    
    # 回答Aを整形
    answer_a_text = answer_a.get("itinerary_markdown", "")
    answer_a_budget = answer_a.get("budget_breakdown", {})
    answer_a_cautions = answer_a.get("cautions", [])
    answer_a_sources = answer_a.get("sources", [])
    answer_a_warnings = answer_a.get("warnings", [])
    
    # 回答Bを整形
    answer_b_text = answer_b.get("itinerary_markdown", "")
    answer_b_budget = answer_b.get("budget_breakdown", {})
    answer_b_cautions = answer_b.get("cautions", [])
    answer_b_sources = answer_b.get("sources", [])
    answer_b_warnings = answer_b.get("warnings", [])
    
    # 検索要約を整形
    search_brief_text = ""
    if search_brief:
        for i, brief in enumerate(search_brief, 1):
            topic = brief.get('topic', '')
            summary = brief.get('summary', '')
            urls = brief.get('urls', [])
            confidence = brief.get('confidence', '')
            search_brief_text += f"""
### {i}. {topic}
要約: {summary}
確度: {confidence}
出典URL: {', '.join(urls) if urls else 'なし'}
"""
    else:
        search_brief_text = "検索要約がありません。"
    
    # 参照URL一覧
    sources_text = "\n".join([f"- {s}" for s in sources]) if sources else "参照URLがありません。"
    
    prompt = f"""【ユーザー条件】
{user_request_text}

【データソース（検索要約 / URL）】
{search_brief_text}

【参照URL一覧】
{sources_text}

---

【回答A】

## 旅程
{answer_a_text}

## 予算内訳
{json.dumps(answer_a_budget, ensure_ascii=False, indent=2) if answer_a_budget else "なし"}

## 参照リンク
{chr(10).join([f"- {s}" for s in answer_a_sources]) if answer_a_sources else "なし"}

## 注意点
{chr(10).join([f"- {c}" for c in answer_a_cautions]) if answer_a_cautions else "なし"}

## 警告
{chr(10).join([f"- {w}" for w in answer_a_warnings]) if answer_a_warnings else "なし"}

---

【回答B】

## 旅程
{answer_b_text}

## 予算内訳
{json.dumps(answer_b_budget, ensure_ascii=False, indent=2) if answer_b_budget else "なし"}

## 参照リンク
{chr(10).join([f"- {s}" for s in answer_b_sources]) if answer_b_sources else "なし"}

## 注意点
{chr(10).join([f"- {c}" for c in answer_b_cautions]) if answer_b_cautions else "なし"}

## 警告
{chr(10).join([f"- {w}" for w in answer_b_warnings]) if answer_b_warnings else "なし"}

---

上記の情報を基に、回答Aと回答Bを比較評価してください。
評価は「根拠」「実現可能性」「正確性」を最重視し、文章の上手さだけで判断しないでください。

JSONのみを出力してください。"""
    
    return prompt


def _parse_plan_comparison_result(comparison_text: str) -> Dict[str, Any]:
    """プラン比較結果をパース"""
    try:
        # JSON部分を抽出
        json_start = comparison_text.find("{")
        json_end = comparison_text.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning("JSONが見つかりませんでした")
            return _generate_fallback_comparison_two("比較結果のパースに失敗しました")
        
        json_text = comparison_text[json_start:json_end]
        result = json.loads(json_text)
        
        # 必須フィールドの検証とデフォルト値設定
        if "winner" not in result:
            result["winner"] = "tie"
        elif result["winner"] not in ["A", "B", "tie"]:
            logger.warning(f"無効なwinner値: {result['winner']}。'tie'に設定します。")
            result["winner"] = "tie"
        
        if "reason_summary" not in result:
            result["reason_summary"] = "比較評価を実行できませんでした"
        
        if "detailed_reasons" not in result:
            result["detailed_reasons"] = []
        else:
            # detailed_reasonsの各要素を検証
            for reason in result["detailed_reasons"]:
                if "better" in reason and reason["better"] not in ["A", "B", "tie"]:
                    reason["better"] = "tie"
        
        if "suggested_merge" not in result:
            result["suggested_merge"] = ""
        
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"JSONパースエラー: {e}")
        logger.debug(f"パース対象テキスト: {comparison_text[:500]}")
        return _generate_fallback_comparison_two(f"JSONパースエラー: {str(e)}")
    except Exception as e:
        logger.error(f"プラン比較結果のパースエラー: {e}")
        return _generate_fallback_comparison_two(f"パースエラー: {str(e)}")


def _generate_fallback_comparison_two(error_message: str) -> Dict[str, Any]:
    """フォールバック比較結果を生成（2つのプラン比較用）"""
    return {
        "winner": "tie",
        "reason_summary": f"比較評価を実行できませんでした: {error_message}",
        "detailed_reasons": [
            {
                "criterion": "正確性",
                "better": "tie",
                "why": "評価エラーのため判定できませんでした"
            },
            {
                "criterion": "実現可能性",
                "better": "tie",
                "why": "評価エラーのため判定できませんでした"
            },
            {
                "criterion": "根拠の明示",
                "better": "tie",
                "why": "評価エラーのため判定できませんでした"
            },
            {
                "criterion": "テーマ整合性",
                "better": "tie",
                "why": "評価エラーのため判定できませんでした"
            },
            {
                "criterion": "予算妥当性",
                "better": "tie",
                "why": "評価エラーのため判定できませんでした"
            },
            {
                "criterion": "出力品質",
                "better": "tie",
                "why": "評価エラーのため判定できませんでした"
            }
        ],
        "suggested_merge": "評価エラーを解決してから再実行してください"
    }

