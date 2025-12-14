# LLM as a Judge評価システム 使用ガイド

## 概要

LLM as a Judgeによる評価システムは、旅行計画を6つの観点から客観的に評価します。

## 機能

### 1. スコアによる評価

単一の旅行計画を評価し、6つの観点でスコアを付けます。

### 2. 回答比較による評価

5つの異なる旅行計画を比較し、最良の計画を選定します。

## 評価観点（6つ）

1. **適切性（Appropriateness）**: ユーザーの要求条件への適合度
2. **実現可能性（Feasibility）**: 移動時間、営業時間などの現実性
3. **情報の正確性（Accuracy）**: 出典の有無、最新性、信頼性
4. **構造の完全性（Completeness）**: テンプレートv2.0準拠
5. **予算の妥当性（Budget Validity）**: 予算内訳の妥当性
6. **注意点の適切性（Warnings Adequacy）**: 注意点・警告の適切性

## 使用方法

### スコア評価の例

```python
from src.evaluator import evaluate_plan_score
from src.agent import run_agent

# 旅行計画を生成
user_input = {
    "destination": "京都",
    "days": 3,
    "budget_total": 50000,
    "themes": ["グルメ", "歴史"],
    "style": "normal",
    "constraints": []
}

plan = run_agent(user_input, memory_enabled=True)

# スコア評価を実行
evaluation = evaluate_plan_score(plan, user_input)

print(f"総合スコア: {evaluation['overall_score']}")
print(f"適切性: {evaluation['scores']['appropriateness']}")
print(f"実現可能性: {evaluation['scores']['feasibility']}")
print(f"情報の正確性: {evaluation['scores']['accuracy']}")
print(f"構造の完全性: {evaluation['scores']['completeness']}")
print(f"予算の妥当性: {evaluation['scores']['budget_validity']}")
print(f"注意点の適切性: {evaluation['scores']['warnings_adequacy']}")
print(f"\nフィードバック: {evaluation['feedback']}")
print(f"\n強み: {evaluation['strengths']}")
print(f"改善点: {evaluation['improvements']}")
```

### 回答比較評価の例

```python
from src.evaluator import evaluate_plan_comparison
from src.agent import run_agent

# 5つの異なる旅行計画を生成
user_input = {
    "destination": "京都",
    "days": 3,
    "budget_total": 50000,
    "themes": ["グルメ", "歴史"],
    "style": "normal",
    "constraints": []
}

plans = []
for i in range(5):
    # 異なる条件で計画を生成（例: テーマを変える）
    input_variant = user_input.copy()
    input_variant["themes"] = [["グルメ", "歴史"], ["アート", "自然"], ["温泉", "夜景"], ["ショッピング", "体験"], ["歴史", "文化"]][i]
    plan = run_agent(input_variant, memory_enabled=True)
    plans.append(plan)

# 比較評価を実行
comparison = evaluate_plan_comparison(plans, user_input)

print(f"最良の計画ID: {comparison['best_plan_id']}")
print(f"\n順位:")
for ranking in comparison['rankings']:
    print(f"  {ranking['rank']}位: 計画{ranking['plan_id']+1} (スコア: {ranking['score']})")
    print(f"    理由: {ranking['reason']}")

print(f"\n比較サマリー: {comparison['comparison_summary']}")
```

## 評価結果の形式

### スコア評価結果

```python
{
    "overall_score": 85.5,  # 総合スコア（0-100）
    "scores": {
        "appropriateness": 90,      # 適切性
        "feasibility": 85,          # 実現可能性
        "accuracy": 80,             # 情報の正確性
        "completeness": 90,         # 構造の完全性
        "budget_validity": 85,      # 予算の妥当性
        "warnings_adequacy": 80     # 注意点の適切性
    },
    "feedback": "総合的な評価コメント",
    "strengths": ["強み1", "強み2", "強み3"],
    "improvements": ["改善点1", "改善点2", "改善点3"]
}
```

### 比較評価結果

```python
{
    "rankings": [
        {
            "plan_id": 0,
            "rank": 1,
            "score": 90.5,
            "reason": "順位の理由"
        },
        {
            "plan_id": 1,
            "rank": 2,
            "score": 85.0,
            "reason": "順位の理由"
        },
        # ... 5つまで
    ],
    "best_plan_id": 0,
    "comparison_summary": "比較サマリー",
    "detailed_comparison": {
        "appropriateness": {
            "best": 0,
            "scores": [90, 85, 80, 75, 70]
        },
        # ... 他の観点も同様
    }
}
```

## 注意事項

- 評価にはOpenAI APIキーが必要です
- 評価はLLMを使用するため、APIコストが発生します
- 評価結果はJSON形式で返されますが、パースに失敗した場合はフォールバック結果が返されます
