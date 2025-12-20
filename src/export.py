"""
旅程のエクスポート機能（PDF/ICS/地図リンク生成）
"""
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path
from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        CIDFONT_AVAILABLE = True
    except ImportError:
        CIDFONT_AVAILABLE = False
    import platform
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    CIDFONT_AVAILABLE = False

try:
    from icalendar import Calendar, Event
    ICALENDAR_AVAILABLE = True
except ImportError:
    ICALENDAR_AVAILABLE = False

from src.logger import get_logger

logger = get_logger("export")


def _register_japanese_fonts():
    """
    日本語フォントを登録
    優先順位:
    1. 同梱フォント（fonts/NotoSansJP-Regular.ttf）
    2. CIDFont（HeiseiKakuGo-W5）フォールバック
    3. システムフォント（macOS/Linux/Windows）
    
    Returns:
        登録されたフォント名（"NotoSansJP" または "HeiseiKakuGo-W5" など）
    """
    if not REPORTLAB_AVAILABLE:
        return None
    
    # フォント名の定数
    FONT_NAME_NOTO = "NotoSansJP"
    FONT_NAME_CID = "HeiseiKakuGo-W5"
    
    try:
        # 1. 同梱フォントを優先的に試す（fonts/NotoSansJP-Regular.ttf）
        font_path = Path(__file__).parent.parent / "fonts" / "NotoSansJP-Regular.ttf"
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont(FONT_NAME_NOTO, str(font_path)))
                logger.info(f"✅ 同梱フォントを登録しました: {font_path}")
                return FONT_NAME_NOTO
            except Exception as e:
                logger.warning(f"同梱フォントの登録に失敗: {font_path}, {str(e)}")
        else:
            logger.warning(f"同梱フォントが見つかりません: {font_path}")
        
        # 2. CIDFontフォールバック（HeiseiKakuGo-W5）
        if CIDFONT_AVAILABLE:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME_CID))
                logger.info(f"✅ CIDFontを登録しました: {FONT_NAME_CID}")
                return FONT_NAME_CID
            except Exception as e:
                logger.warning(f"CIDFontの登録に失敗: {str(e)}")
        
        # 3. システムフォントを試す（フォールバック）
        system = platform.system()
        font_name = None
        
        if system == "Darwin":
            # macOS: ヒラギノ角ゴシック
            font_paths = [
                "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
                "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
            ]
            for font_path in font_paths:
                if Path(font_path).exists():
                    try:
                        pdfmetrics.registerFont(TTFont("JapaneseFont", font_path))
                        font_name = "JapaneseFont"
                        logger.info(f"✅ システムフォントを登録しました: {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"システムフォント登録に失敗: {font_path}, {str(e)}")
                        continue
        
        elif system == "Linux":
            # Linux: Noto Sans CJK
            font_paths = [
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ]
            for font_path in font_paths:
                if Path(font_path).exists():
                    try:
                        pdfmetrics.registerFont(TTFont("JapaneseFont", font_path))
                        font_name = "JapaneseFont"
                        logger.info(f"✅ システムフォントを登録しました: {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"システムフォント登録に失敗: {font_path}, {str(e)}")
                        continue
        
        elif system == "Windows":
            # Windows: MS Gothic/MS Mincho
            font_paths = [
                "C:/Windows/Fonts/msgothic.ttc",
                "C:/Windows/Fonts/msmincho.ttc",
            ]
            for font_path in font_paths:
                if Path(font_path).exists():
                    try:
                        pdfmetrics.registerFont(TTFont("JapaneseFont", font_path))
                        font_name = "JapaneseFont"
                        logger.info(f"✅ システムフォントを登録しました: {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"システムフォント登録に失敗: {font_path}, {str(e)}")
                        continue
        
        if font_name:
            return font_name
        
        # すべて失敗した場合
        logger.error("❌ 日本語フォントの登録に失敗しました。日本語が正しく表示されない可能性があります。")
        return None
    
    except Exception as e:
        logger.error(f"フォント登録でエラーが発生: {str(e)}", exc_info=True)
        return None


def get_japanese_font_name() -> Optional[str]:
    """
    利用可能な日本語フォント名を返す
    
    Returns:
        フォント名（"NotoSansJP", "HeiseiKakuGo-W5", "JapaneseFont" など）
        フォントが登録されていない場合はNone
    """
    # 既に登録されているか確認
    registered_fonts = pdfmetrics.getRegisteredFontNames()
    
    # 優先順位で確認
    if "NotoSansJP" in registered_fonts:
        return "NotoSansJP"
    elif "HeiseiKakuGo-W5" in registered_fonts:
        return "HeiseiKakuGo-W5"
    elif "JapaneseFont" in registered_fonts:
        return "JapaneseFont"
    
    # 未登録の場合は登録を試みる
    return _register_japanese_fonts()


def _process_markdown_text(text: str) -> str:
    """
    MarkdownテキストをreportlabのParagraphで使用できるHTML形式に変換
    
    Args:
        text: Markdownテキスト
    
    Returns:
        HTML形式のテキスト（reportlabのParagraphで使用可能）
    """
    if not text:
        return ""
    
    # **太字**を<b>タグに変換
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    
    # *斜体*を<i>タグに変換（太字と競合しないように）
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
    
    # URLリンクを処理（[text](url) -> text (url)）
    def replace_link(match):
        try:
            link_text = match.group(1) if match.lastindex >= 1 else ''
            link_url = match.group(2) if match.lastindex >= 2 else ''
            if link_url:
                return f'{link_text} (<link href="{link_url}" color="blue"><u>{link_url}</u></link>)'
            return link_text
        except (IndexError, AttributeError):
            return match.group(0)
    
    try:
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', replace_link, text)
    except (re.error, IndexError):
        # 正規表現エラーの場合は、単純にリンク記号を除去
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # 絵文字や特殊文字はそのまま保持
    # 日本語フォントが登録されていれば表示可能
    return text


def _add_table_to_story(story: List, table_rows: List[List[str]], normal_style, japanese_font: Optional[str] = None):
    """
    テーブルをstoryに追加
    
    Args:
        story: reportlabのstoryリスト
        table_rows: テーブルの行データ（各要素はセルのリスト）
        normal_style: 通常のスタイル
        japanese_font: 日本語フォント名（オプション）
    """
    if not table_rows:
        return
    
    try:
        # テーブルデータを準備（Markdownを処理）
        table_data = []
        for row in table_rows:
            processed_row = []
            for cell in row:
                processed_cell = _process_markdown_text(cell)
                processed_row.append(processed_cell)
            table_data.append(processed_row)
        
        # テーブルを作成
        table = Table(table_data)
        
        # フォント名を設定
        table_font = japanese_font if japanese_font else 'Helvetica'
        table_font_bold = japanese_font if japanese_font else 'Helvetica-Bold'
        
        # テーブルスタイルを設定
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # ヘッダー行の背景
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # ヘッダー行のテキスト色
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 左揃え
            ('FONTNAME', (0, 0), (-1, 0), table_font_bold),  # ヘッダー行のフォント
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # ヘッダー行のフォントサイズ
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # ヘッダー行の下パディング
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # データ行の背景
            ('FONTNAME', (0, 1), (-1, -1), table_font),  # データ行のフォント
            ('FONTSIZE', (0, 1), (-1, -1), 9),  # データ行のフォントサイズ
            ('GRID', (0, 0), (-1, -1), 1, colors.black),  # グリッド線
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # 上揃え
        ])
        
        table.setStyle(table_style)
        story.append(table)
        story.append(Spacer(1, 12))
    except Exception as e:
        # テーブル生成に失敗した場合は、テキストとして表示
        logger.warning(f"テーブル生成に失敗: {str(e)}")
        for row in table_rows:
            row_text = " | ".join(row)
            processed_text = _process_markdown_text(row_text)
            story.append(Paragraph(processed_text, normal_style))
            story.append(Spacer(1, 4))


def _build_pdf_title(
    user_title: Optional[str] = None,
    favorite_name: Optional[str] = None,
    spot_name: Optional[str] = None,
    address: Optional[str] = None
) -> str:
    """
    PDFタイトルを決定する（優先順位に従って）
    
    Args:
        user_title: ユーザー入力のタイトル
        favorite_name: お気に入り名
        spot_name: スポット名
        address: 住所（フォールバック）
    
    Returns:
        決定されたタイトル文字列
    """
    # 優先順位1: ユーザー入力のタイトルまたはお気に入り名
    if user_title and user_title.strip():
        return user_title.strip()
    if favorite_name and favorite_name.strip():
        return favorite_name.strip()
    
    # 優先順位2: スポット名
    if spot_name and spot_name.strip():
        return spot_name.strip()
    
    # 優先順位3: 住所（フォールバック）
    if address and address.strip():
        return address.strip()
    
    # すべて空の場合はデフォルト
    return "旅行プラン"


def _sanitize_filename(filename: str) -> str:
    """
    ファイル名に使用できない文字を除去・置換
    
    Args:
        filename: 元のファイル名
    
    Returns:
        サニタイズされたファイル名
    """
    # Windowsで使用できない文字: / \ : * ? " < > |
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # 連続するアンダースコアを1つに
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    
    # 先頭・末尾のアンダースコアを除去
    sanitized = sanitized.strip('_')
    
    return sanitized


def generate_pdf(
    itinerary_markdown: str,
    destination: str,
    days: int,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    favorite_name: Optional[str] = None,
    spot_name: Optional[str] = None,
    address: Optional[str] = None
) -> BytesIO:
    """
    PDF形式で旅程をエクスポート
    
    Args:
        itinerary_markdown: 旅程（Markdown形式）
        destination: 目的地（フォールバック用）
        days: 旅行日数
        output_path: 出力パス（Noneの場合はBytesIOを返す）
        title: ユーザー入力のタイトル（優先順位1）
        favorite_name: お気に入り名（優先順位1）
        spot_name: スポット名（優先順位2）
        address: 住所（優先順位3、本文の「場所」欄にも表示）
    
    Returns:
        BytesIOオブジェクト（output_pathがNoneの場合）またはNone
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("reportlabがインストールされていません")
        raise ImportError("reportlabがインストールされていません。pip install reportlabでインストールしてください。")
    
    try:
        logger.info(f"PDF生成を開始: destination={destination}, days={days}")
        
        # BytesIOまたはファイルに出力
        if output_path:
            buffer = open(output_path, 'wb')
        else:
            buffer = BytesIO()
        
        # PDFドキュメントを作成
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # 日本語フォントを登録
        japanese_font = _register_japanese_fonts()
        if not japanese_font:
            # 登録に失敗した場合は再試行
            japanese_font = get_japanese_font_name()
        
        # スタイルを定義
        styles = getSampleStyleSheet()
        
        # フォント名を設定（日本語フォントが登録されている場合）
        # 日本語フォントがない場合は警告を出してHelveticaを使用
        font_name = japanese_font if japanese_font else 'Helvetica'
        if not japanese_font:
            logger.warning("⚠️ 日本語フォントが登録されていません。日本語が正しく表示されない可能性があります。")
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor='#1f4788',
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=font_name
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor='#2c3e50',
            spaceAfter=8,
            spaceBefore=12,
            fontName=font_name
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=font_name
        )
        
        # コンテンツを構築
        story = []
        
        # タイトルを決定（優先順位に従って）
        pdf_title = _build_pdf_title(
            user_title=title,
            favorite_name=favorite_name,
            spot_name=spot_name,
            address=address if not title and not favorite_name and not spot_name else None
        )
        
        # タイトルを表示
        story.append(Paragraph(pdf_title, title_style))
        story.append(Spacer(1, 12))
        
        # 住所がある場合は「場所」欄に表示（タイトルと住所が異なる場合のみ）
        if address and address.strip() and address.strip() != pdf_title:
            location_text = f"**場所:** {address.strip()}"
            story.append(Paragraph(_process_markdown_text(location_text), normal_style))
            story.append(Spacer(1, 8))
        
        # 作成日
        created_date = datetime.now().strftime("%Y年%m月%d日")
        story.append(Paragraph(f"作成日: {created_date}", normal_style))
        story.append(Spacer(1, 12))
        
        # MarkdownをパースしてPDFに変換
        # より詳細なパースロジックで内容を確実に含める
        lines = itinerary_markdown.split('\n')
        
        # テーブル処理用の変数
        table_rows = []
        in_table = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 空行はスキップ（区切りとして使用）
            if not line_stripped:
                if in_table and table_rows:
                    # テーブルを出力
                    _add_table_to_story(story, table_rows, normal_style, japanese_font)
                    table_rows = []
                    in_table = False
                story.append(Spacer(1, 6))
                continue
            
            # テーブル行（| で始まる）
            if line_stripped.startswith('|') and '|' in line_stripped[1:]:
                in_table = True
                # テーブルの区切り行（| --- |）をスキップ
                if re.match(r'^\|[\s\-:]+\|', line_stripped):
                    continue
                # テーブル行をパース
                cells = [cell.strip() for cell in line_stripped.split('|')[1:-1]]
                if cells:
                    table_rows.append(cells)
                continue
            else:
                # テーブルが終了した場合、テーブルを出力
                if in_table and table_rows:
                    _add_table_to_story(story, table_rows, normal_style, japanese_font)
                    table_rows = []
                    in_table = False
            
            # 見出し（# で始まる）
            if line_stripped.startswith('#'):
                level = len(line_stripped) - len(line_stripped.lstrip('#'))
                heading_text = line_stripped.lstrip('#').strip()
                if heading_text:
                    # 見出し内の太字やリンクを処理
                    heading_text = _process_markdown_text(heading_text)
                    if level == 1:
                        story.append(Paragraph(heading_text, title_style))
                    else:
                        story.append(Paragraph(heading_text, heading_style))
                    story.append(Spacer(1, 8))
            
            # リスト項目（- または * で始まる、または数字.で始まる）
            elif re.match(r'^[\-\*]\s+', line_stripped) or re.match(r'^\d+\.\s+', line_stripped):
                # リスト記号を除去
                list_text = re.sub(r'^[\-\*]\s+', '', line_stripped)
                list_text = re.sub(r'^\d+\.\s+', '', list_text)
                if list_text:
                    # Markdownを処理（太字、リンクなど）
                    list_text = _process_markdown_text(list_text)
                    story.append(Paragraph(f"• {list_text}", normal_style))
                    story.append(Spacer(1, 4))
            
            # 通常のテキスト
            else:
                # Markdownを処理（太字、リンクなど）
                text = _process_markdown_text(line_stripped)
                if text.strip():
                    story.append(Paragraph(text, normal_style))
                    story.append(Spacer(1, 4))
        
        # 最後にテーブルが残っている場合
        if in_table and table_rows:
            _add_table_to_story(story, table_rows, normal_style, japanese_font)
        
        # 地図リンクセクションを追加
        story.append(Spacer(1, 12))
        story.append(PageBreak())
        story.append(Paragraph("🗺️ 地図リンク", heading_style))
        story.append(Spacer(1, 8))
        
        # 地図リンクを生成
        try:
            map_links = generate_map_links(itinerary_markdown, destination)
            if map_links:
                for link in map_links[:20]:  # 最大20件まで
                    location = link.get('location', link.get('name', ''))
                    url = link.get('url', '')
                    if location and url:
                        # 地図リンクをPDFに追加
                        link_text = f"📍 {location}"
                        link_para = Paragraph(
                            f'{link_text} - <link href="{url}" color="blue"><u>{url}</u></link>',
                            normal_style
                        )
                        story.append(link_para)
                        story.append(Spacer(1, 4))
            else:
                # 目的地の地図リンクのみ追加
                destination_url = build_google_maps_url(destination)
                link_para = Paragraph(
                    f'📍 {destination} - <link href="{destination_url}" color="blue"><u>{destination_url}</u></link>',
                    normal_style
                )
                story.append(link_para)
        except Exception as e:
            logger.warning(f"PDFへの地図リンク追加でエラー: {str(e)}")
            # エラー時でも目的地のリンクは追加
            try:
                destination_url = build_google_maps_url(destination)
                link_para = Paragraph(
                    f'📍 {destination} - <link href="{destination_url}" color="blue"><u>{destination_url}</u></link>',
                    normal_style
                )
                story.append(link_para)
            except:
                pass
        
        # PDFを生成
        doc.build(story)
        
        if output_path:
            buffer.close()
            logger.info(f"PDFを保存しました: {output_path}")
            return None
        else:
            buffer.seek(0)
            logger.info("PDFを生成しました（BytesIO）")
            return buffer
    
    except Exception as e:
        logger.error(f"PDF生成でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


def build_google_maps_url(destination: str) -> str:
    """
    Google Maps検索URLを生成
    
    Args:
        destination: 目的地
    
    Returns:
        Google Maps検索URL
    """
    from urllib.parse import quote
    encoded_destination = quote(destination)
    return f"https://www.google.com/maps/search/?api=1&query={encoded_destination}"


def generate_ics(
    itinerary_markdown: str,
    destination: str,
    days: int,
    start_date: Optional[datetime] = None,
    title: Optional[str] = None,
    output_path: Optional[str] = None
) -> BytesIO:
    """
    ICS（カレンダー）形式で旅程をエクスポート
    
    Args:
        itinerary_markdown: 旅程（Markdown形式）
        destination: 目的地
        days: 旅行日数
        start_date: 開始日（Noneの場合は今日から）
        output_path: 出力パス（Noneの場合はBytesIOを返す）
    
    Returns:
        BytesIOオブジェクト（output_pathがNoneの場合）またはNone
    """
    if not ICALENDAR_AVAILABLE:
        logger.error("icalendarがインストールされていません")
        raise ImportError("icalendarがインストールされていません。pip install icalendarでインストールしてください。")
    
    try:
        logger.info(f"ICS生成を開始: destination={destination}, days={days}")
        
        # カレンダーを作成
        cal = Calendar()
        cal.add('prodid', '-//Travel Planner Agent//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        
        # 開始日を設定
        if not start_date:
            start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # タイトルを決定
        event_title = title if title else destination
        
        # 開始日をdate型に変換（時刻を除去）
        if isinstance(start_date, datetime):
            start_date_only = start_date.date()
        else:
            start_date_only = start_date
        
        # Markdownから日別計画を抽出
        day_plans = _parse_day_plans_from_markdown(itinerary_markdown)
        
        # 日別計画がない場合は、全体を1つの終日イベントとして作成
        if not day_plans:
            event = Event()
            event.add('summary', f"{event_title} {days}日間の旅行")
            
            # Markdownからテキストのみを抽出
            description = itinerary_markdown
            try:
                description = re.sub(r'#+\s*', '', description)
                description = re.sub(r'\*\*([^*]+)\*\*', r'\1', description)
                def replace_link_safe(match):
                    return match.group(1) if match.lastindex >= 1 else ''
                description = re.sub(r'\[([^\]]+)\]\([^\)]+\)', replace_link_safe, description)
                description = re.sub(r'^[-*]\s*', '', description, flags=re.MULTILINE)
            except (re.error, IndexError):
                description = description.replace('**', '').replace('#', '').replace('-', '').replace('*', '')
                description = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', description)
            description = description.strip()[:1000]
            
            event.add('description', description if description else f"{destination} {days}日間の旅行プラン")
            
            # 終日イベント（All-day）: VALUE=DATE形式
            from icalendar import vDate
            event_start_date = start_date_only
            event_end_date = start_date_only + timedelta(days=days)
            
            event.add('dtstart', vDate(event_start_date))
            event.add('dtend', vDate(event_end_date))
            event.add('location', destination)
            
            import uuid
            event_uid = f"travel-plan-{uuid.uuid4().hex[:8]}@travel-planner-agent"
            event.add('uid', event_uid)
            event.add('dtstamp', datetime.now(timezone.utc))
            event.add('created', datetime.now(timezone.utc))
            cal.add_component(event)
        else:
            # 日別計画がある場合は、各日を終日イベントとして作成
            for day_num in range(1, days + 1):
                # 各日のイベントを作成（終日イベント）
                event = Event()
                
                # SUMMARY: タイトル - Day{n}
                event.add('summary', f"{event_title} - Day{day_num}")
                
                # 説明文を作成（Markdownからテキストのみを抽出）
                description = ""
                if day_num <= len(day_plans):
                    day_plan = day_plans[day_num - 1]
                    description = day_plan.get('content', '')
                    # Markdown記号を除去（安全に処理）
                    try:
                        description = re.sub(r'#+\s*', '', description)
                        description = re.sub(r'\*\*([^*]+)\*\*', r'\1', description)
                        def replace_link_safe(match):
                            return match.group(1) if match.lastindex >= 1 else ''
                        description = re.sub(r'\[([^\]]+)\]\([^\)]+\)', replace_link_safe, description)
                        description = re.sub(r'^[-*]\s*', '', description, flags=re.MULTILINE)
                    except (re.error, IndexError):
                        description = description.replace('**', '').replace('#', '').replace('-', '').replace('*', '')
                        description = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', description)
                    description = description.strip()
                
                # 地図リンクを追加
                try:
                    day_map_links = generate_map_links(description, destination)
                    if day_map_links:
                        map_links_text = "\n\n地図リンク:\n"
                        for link in day_map_links[:5]:  # 最大5件まで
                            location = link.get('location', link.get('name', ''))
                            url = link.get('url', '')
                            if location and url:
                                map_links_text += f"- {location}: {url}\n"
                        description += map_links_text
                except Exception as e:
                    logger.warning(f"ICSへの地図リンク追加でエラー: {str(e)}")
                
                if description:
                    event.add('description', description[:2000])  # 説明文の上限を2000文字に拡張
                else:
                    event.add('description', f"{destination} {day_num}日目の旅程")
                
                # 終日イベント（All-day）: VALUE=DATE形式
                # DTSTART: 開始日（start_date_only + (day_num - 1)）
                event_start_date = start_date_only + timedelta(days=day_num - 1)
                # DTEND: 終了日（開始日の翌日。終日イベントは翌日がDTEND）
                event_end_date = event_start_date + timedelta(days=1)
                
                # VALUE=DATE形式で設定（icalendarライブラリのvDateを使用）
                from icalendar import vDate
                event.add('dtstart', vDate(event_start_date))
                event.add('dtend', vDate(event_end_date))
                
                event.add('location', destination)
                
                # UID: ユニークなID（UUID風）
                import uuid
                event_uid = f"travel-plan-day{day_num}-{uuid.uuid4().hex[:8]}@travel-planner-agent"
                event.add('uid', event_uid)
                
                # DTSTAMP: 現在時刻（UTC）
                event.add('dtstamp', datetime.now(timezone.utc))
                event.add('created', datetime.now(timezone.utc))
                
                cal.add_component(event)
        
        # ICSファイルを生成
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(cal.to_ical())
            logger.info(f"ICSを保存しました: {output_path}")
            return None
        else:
            buffer = BytesIO()
            buffer.write(cal.to_ical())
            buffer.seek(0)
            logger.info("ICSを生成しました（BytesIO）")
            return buffer
    
    except Exception as e:
        logger.error(f"ICS生成でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


def generate_map_links(itinerary_markdown: str, destination: str) -> List[Dict[str, str]]:
    """
    地図リンクを生成（Google Maps）
    場所情報（📍 アクセス）のみを抽出して表示
    
    Args:
        itinerary_markdown: 旅程（Markdown形式）
        destination: 目的地
    
    Returns:
        地図リンクのリスト（場所情報のみ）
        [
            {"name": "場所名", "location": "場所", "url": "Google Maps URL"},
            ...
        ]
    """
    try:
        logger.info(f"地図リンク生成を開始: destination={destination}")
        
        from urllib.parse import quote
        map_links = []
        extracted_locations = set()  # 場所情報のセット（重複排除）
        
        # 目的地の地図リンク
        destination_encoded = quote(destination)
        destination_url = f"https://www.google.com/maps/search/?api=1&query={destination_encoded}"
        map_links.append({
            "name": destination,
            "location": destination,
            "url": destination_url,
            "type": "destination"
        })
        extracted_locations.add(destination)
        
        # Markdownから場所情報（📍 アクセス）のみを抽出
        lines = itinerary_markdown.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # 📍 アクセス: の行から場所情報を抽出
            if '📍' in line_stripped and 'アクセス' in line_stripped:
                # パターン1: 📍 アクセス: [場所情報]
                location_match = re.search(r'📍\s*アクセス[：:]\s*(.+?)(?:\n|$)', line_stripped)
                if location_match:
                    location = location_match.group(1).strip()
                    # URLを除去
                    location = re.sub(r'https?://[^\s]+', '', location)
                    # 括弧内を除去
                    location = re.sub(r'[（(].*?[）)]', '', location)
                    # 最初の場所のみを取得（、や，で区切られている場合）
                    location = location.split('、')[0].split('，')[0].split(',')[0].strip()
                    # 不要な文字を除去
                    location = re.sub(r'[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '', location)
                    if location and len(location) > 1 and location not in extracted_locations:
                        extracted_locations.add(location)
                else:
                    # パターン2: 📍 [場所情報]
                    location_match = re.search(r'📍\s*(.+?)(?:\n|$)', line_stripped)
                    if location_match:
                        location = location_match.group(1).strip()
                        # 「アクセス」という文字列を除去
                        location = location.replace('アクセス', '').replace(':', '').replace('：', '').strip()
                        # URLを除去
                        location = re.sub(r'https?://[^\s]+', '', location)
                        # 括弧内を除去
                        location = re.sub(r'[（(].*?[）)]', '', location)
                        # 最初の場所のみを取得
                        location = location.split('、')[0].split('，')[0].split(',')[0].strip()
                        # 不要な文字を除去
                        location = re.sub(r'[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '', location)
                        if location and len(location) > 1 and location not in extracted_locations:
                            extracted_locations.add(location)
        
        # 場所情報から地図リンクを生成
        for location in sorted(extracted_locations):
            if location == destination:
                continue  # 目的地は既に追加済み
            
            # 場所情報で検索
            query = f"{destination} {location}"
            query_encoded = quote(query)
            url = f"https://www.google.com/maps/search/?api=1&query={query_encoded}"
            map_links.append({
                "name": location,
                "location": location,
                "url": url,
                "type": "location"
            })
        
        logger.info(f"地図リンクを生成しました: {len(map_links)}件（場所情報のみ）")
        return map_links
    
    except Exception as e:
        logger.error(f"地図リンク生成でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
        return []


def _parse_day_plans_from_markdown(markdown: str) -> List[Dict[str, str]]:
    """
    Markdownから日別計画を抽出
    
    Args:
        markdown: Markdown形式の旅程
    
    Returns:
        日別計画のリスト
    """
    day_plans = []
    lines = markdown.split('\n')
    
    current_day = None
    current_content = []
    
    for line in lines:
        # Day X の見出しを検出
        day_match = re.match(r'#+\s*Day\s*(\d+)', line, re.IGNORECASE)
        if day_match:
            if current_day is not None:
                day_plans.append({
                    "day": current_day,
                    "content": '\n'.join(current_content)
                })
            current_day = int(day_match.group(1))
            current_content = []
        elif current_day is not None:
            current_content.append(line)
    
    # 最後の日を追加
    if current_day is not None:
        day_plans.append({
            "day": current_day,
            "content": '\n'.join(current_content)
        })
    
    return day_plans




