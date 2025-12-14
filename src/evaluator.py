"""
LLM as a Judgeによる評価モジュール
スコア評価と回答比較評価を実装
"""
import json
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.prompts import EVALUATION_PROMPT, COMPARISON_EVALUATION_PROMPT
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
