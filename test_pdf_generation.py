#!/usr/bin/env python3
"""
PDF生成の簡易テストコード

使用方法:
    python test_pdf_generation.py

生成されるファイル:
    test_output.pdf - テスト用のPDFファイル
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.export import generate_pdf, get_japanese_font_name, _register_japanese_fonts
from src.logger import get_logger

logger = get_logger("test_pdf")


def test_pdf_generation():
    """PDF生成のテスト"""
    print("=" * 60)
    print("PDF生成テスト")
    print("=" * 60)
    
    # 日本語フォントの登録を確認
    print("\n1. 日本語フォントの登録確認...")
    font_name = _register_japanese_fonts()
    if font_name:
        print(f"   ✅ フォント登録成功: {font_name}")
    else:
        print("   ⚠️  フォント登録に失敗しました。日本語が正しく表示されない可能性があります。")
    
    # テスト用のMarkdownコンテンツ
    test_markdown = """
# 京都府京都市左京区 銀閣寺町 3日間の旅行プラン

## 前提・仮定

- 出発地点: 東京
- 移動手段: 公共交通機関
- 旅行スタイル: 標準

## Day 1: 歴史と文化

### 🌅 朝（9:00-12:00）

- **銀閣寺（慈照寺）**を訪問
  - 住所: 〒606-8402 京都府京都市左京区銀閣寺町2
  - 拝観料: 500円
  - アクセス: 市バス「銀閣寺道」下車、徒歩10分

### 🍽️ 昼（12:00-14:00）

- **哲学の道**沿いのレストランでランチ
  - ベジタリアン対応メニューあり

### 🌆 夕（14:00-18:00）

- **南禅寺**を訪問
  - 住所: 〒606-8435 京都府京都市左京区南禅寺福地町
  - 拝観料: 500円

### 🌙 夜（18:00-21:00）

- 祇園エリアで夕食
  - 京料理を楽しむ

## Day 2: グルメと体験

### 🌅 朝（9:00-12:00）

- **清水寺**を訪問
  - 住所: 〒605-0862 京都府京都市東山区清水1丁目294

### 🍽️ 昼（12:00-14:00）

- 清水寺周辺でランチ
  - 京野菜を使った料理

## 📚 参照リンク

1. https://www.shokoku-ji.jp/
2. https://www.nanzenji.or.jp/

## ⚠️ 注意点・要確認事項

- 各寺院の営業時間を事前に確認してください
- 混雑時は入場制限がある場合があります

## 💰 概算予算

| 項目 | 金額 |
|------|------|
| 交通費 | ¥15,000 |
| 食事代 | ¥20,000 |
| 体験・入場料 | ¥5,000 |
| その他 | ¥10,000 |
| **合計** | **¥50,000** |
"""
    
    print("\n2. PDF生成中...")
    try:
        output_path = project_root / "test_output.pdf"
        pdf_buffer = generate_pdf(
            itinerary_markdown=test_markdown,
            destination="京都府京都市左京区 銀閣寺町",
            days=3,
            output_path=str(output_path)
        )
        
        print(f"   ✅ PDF生成成功: {output_path}")
        print(f"   📄 ファイルサイズ: {output_path.stat().st_size:,} bytes")
        
        # フォント情報を表示
        print(f"\n3. 使用フォント: {font_name or 'Helvetica (日本語非対応)'}")
        
        print("\n" + "=" * 60)
        print("✅ テスト完了")
        print("=" * 60)
        print(f"\n生成されたPDFを確認してください: {output_path}")
        print("\n確認ポイント:")
        print("  - 日本語文字（ひらがな、カタカナ、漢字）が正しく表示されているか")
        print("  - 「■」や「□」のような文字化けがないか")
        print("  - テーブルが正しく表示されているか")
        print("  - 見出しやリストが正しく表示されているか")
        
        return True
        
    except Exception as e:
        print(f"   ❌ PDF生成エラー: {str(e)}")
        logger.error(f"PDF生成テストでエラー: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_pdf_generation()
    sys.exit(0 if success else 1)
