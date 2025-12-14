"""
旅行計画エージェントのメインアプリケーション（MVP仕様）
Streamlit UI：入力→生成→再生成→編集
"""
import streamlit as st
from src.agent import run_agent
from src.tools.plan_editor import edit_itinerary
from src.schemas import PlanEditInput
from src.knowledge import get_knowledge_base
from src.logger import get_logger

logger = get_logger("app")

# セッション状態の初期化
if "current_plan" not in st.session_state:
    st.session_state.current_plan = None
if "last_output" not in st.session_state:
    st.session_state.last_output = None
if "memory_enabled" not in st.session_state:
    st.session_state.memory_enabled = True


def _handle_error(e: Exception, context: str, user_message: str = None) -> None:
    """
    共通のエラーハンドリング
    
    Args:
        e: 例外オブジェクト
        context: エラーが発生したコンテキスト（例: "旅程生成"）
        user_message: ユーザー向けのカスタムメッセージ（Noneの場合はデフォルトメッセージ）
    """
    logger.error(f"{context}でエラーが発生: {type(e).__name__}: {str(e)}", exc_info=True)
    st.error(f"❌ エラーが発生しました: {str(e)}")
    
    if user_message:
        st.info(user_message)
    else:
        st.info("💡 別の条件で再試行するか、しばらく時間をおいてから再度お試しください。")
    
    with st.expander("エラー詳細（開発者向け）"):
        st.exception(e)


def main():
    st.set_page_config(
        page_title="Travel Planner Agent",
        page_icon="✈️",
        layout="wide"
    )
    
    st.title("✈️ Travel Planner Agent")
    st.markdown("AIを活用した旅行計画作成アシスタント")
    
    # サイドバー：入力フォーム
    with st.sidebar:
        st.header("📝 旅行条件")
        
        # 必須項目
        destination = st.text_input("目的地 *", placeholder="例: 京都", value="")
        days = st.number_input("滞在日数 *", min_value=1, max_value=30, value=3)
        budget_total = st.number_input(
            "予算（円） *", 
            min_value=0, 
            value=50000, 
            step=1000,
            help="宿泊費・交通費・食事代・体験費を含む総予算を入力してください"
        )
        st.caption("💡 宿泊費、交通費、食事代、体験・入場料、その他を含む総予算です")
        
        # テーマ（複数選択）
        st.subheader("興味テーマ")
        theme_options = ["グルメ", "アート", "歴史", "自然", "温泉", "ショッピング", "体験", "夜景"]
        themes = st.multiselect("興味テーマを選択", theme_options, default=["グルメ"])
        
        # スタイル
        style_options = {
            "ゆったり": "relaxed",
            "標準": "normal",
            "充実": "packed"
        }
        style_descriptions = {
            "relaxed": "ゆったり（1日3-4枠）",
            "normal": "標準（1日4-5枠）",
            "packed": "充実（1日5-6枠）"
        }
        style_label = st.selectbox("旅行スタイル", list(style_options.keys()), index=1)
        style = style_options[style_label]
        st.caption(f"※ {style_descriptions[style]}")
        
        # 任意項目
        st.subheader("オプション")
        start_point = st.text_input("出発地点", placeholder="例: 東京", value="")
        mobility_options = {
            "公共交通機関": "public",
            "車": "car",
            "徒歩": "walk"
        }
        mobility_label = st.selectbox("移動手段", list(mobility_options.keys()), index=0)
        mobility = mobility_options[mobility_label]
        
        # やりたいことリスト
        constraints_text = st.text_area(
            "やりたいこと・希望事項", 
            placeholder="例: ベジタリアン対応のレストラン、雨天時も楽しめるプラン、予約必須のスポットは事前確認", 
            value="",
            help="旅行で実現したいことや希望事項を入力してください（1行に1つずつ）"
        )
        constraints = [c.strip() for c in constraints_text.split("\n") if c.strip()] if constraints_text else []
        
        # Memory ON/OFF
        st.divider()
        st.subheader("⚙️ 設定")
        memory_enabled = st.toggle("Memory ON/OFF", value=st.session_state.memory_enabled)
        st.session_state.memory_enabled = memory_enabled
        if memory_enabled:
            st.caption("✅ Memory有効：過去の会話履歴を参照します")
        else:
            st.caption("❌ Memory無効：毎回初回ユーザーとして対応します")
        
        # RAG（自前ナレッジ）管理
        st.divider()
        st.subheader("📚 マイナレッジ")
        with st.expander("お気に入り・メモ・過去旅程を管理"):
            knowledge_base = get_knowledge_base()
            
            # タブで機能を分ける
            tab1, tab2, tab3 = st.tabs(["お気に入り", "旅行メモ", "過去旅程"])
            
            with tab1:
                st.write("**お気に入りリスト**")
                # お気に入りの追加
                with st.form("add_favorite_form"):
                    fav_name = st.text_input("名前 *", key="fav_name")
                    fav_category = st.selectbox("カテゴリ", ["観光スポット", "レストラン", "ホテル", "ショップ", "その他"], key="fav_category")
                    fav_location = st.text_input("場所", key="fav_location")
                    fav_notes = st.text_area("メモ", key="fav_notes")
                    fav_url = st.text_input("URL", key="fav_url")
                    if st.form_submit_button("追加"):
                        if fav_name:
                            knowledge_base.add_favorite(fav_name, fav_category, fav_location, fav_notes, fav_url)
                            st.success(f"✅ {fav_name}をお気に入りに追加しました")
                            st.rerun()
                
                # お気に入りリストの表示
                favorites = knowledge_base.get_favorites()
                if favorites:
                    for fav in favorites:
                        with st.container():
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.write(f"**{fav.get('name')}** ({fav.get('category')})")
                                if fav.get('location'):
                                    st.caption(f"📍 {fav.get('location')}")
                                if fav.get('notes'):
                                    st.caption(f"📝 {fav.get('notes')}")
                            with col2:
                                if st.button("削除", key=f"del_fav_{fav.get('id')}"):
                                    knowledge_base.remove_favorite(fav.get('id'))
                                    st.rerun()
                            st.divider()
                else:
                    st.info("お気に入りがありません")
            
            with tab2:
                st.write("**旅行メモ**")
                # メモの追加
                with st.form("add_memo_form"):
                    memo_title = st.text_input("タイトル *", key="memo_title")
                    memo_content = st.text_area("内容 *", key="memo_content")
                    memo_tags = st.text_input("タグ（カンマ区切り）", key="memo_tags")
                    if st.form_submit_button("追加"):
                        if memo_title and memo_content:
                            tags = [t.strip() for t in memo_tags.split(",") if t.strip()] if memo_tags else []
                            knowledge_base.add_memo(memo_title, memo_content, tags)
                            st.success(f"✅ {memo_title}をメモに追加しました")
                            st.rerun()
                
                # メモリストの表示
                memos = knowledge_base.get_memos()
                if memos:
                    for memo in memos:
                        with st.container():
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.write(f"**{memo.get('title')}**")
                                st.caption(memo.get('content', '')[:200])
                                if memo.get('tags'):
                                    st.caption(f"🏷️ {', '.join(memo.get('tags', []))}")
                            with col2:
                                if st.button("削除", key=f"del_memo_{memo.get('id')}"):
                                    knowledge_base.remove_memo(memo.get('id'))
                                    st.rerun()
                            st.divider()
                else:
                    st.info("メモがありません")
            
            with tab3:
                st.write("**過去旅程**")
                # 最新データを再読み込み
                knowledge_base._load_itineraries()
                # 過去旅程の表示
                itineraries = knowledge_base.get_itineraries(limit=10)
                if itineraries:
                    for itin in itineraries:
                        with st.container():
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.write(f"**{itin.get('destination')} {itin.get('days')}日プラン**")
                                st.caption(f"作成日: {itin.get('created_at', '')[:10]}")
                                if itin.get('metadata'):
                                    meta = itin.get('metadata', {})
                                    if meta.get('themes'):
                                        st.caption(f"テーマ: {', '.join(meta.get('themes', []))}")
                            with col2:
                                if st.button("削除", key=f"del_itinerary_{itin.get('id')}"):
                                    knowledge_base.remove_itinerary(itin.get('id'))
                                    st.rerun()
                            st.divider()
                else:
                    st.info("過去旅程がありません（旅程を生成すると自動的に保存されます）")
    
    # メインコンテンツ
    col1, col2, col3 = st.columns(3)
    
    with col1:
        generate_btn = st.button("🚀 旅程を生成", type="primary", use_container_width=True)
    
    with col2:
        regenerate_btn = st.button("🔄 別案を生成（再生成）", use_container_width=True, 
                                   disabled=st.session_state.last_output is None)
    
    with col3:
        edit_btn = st.button("✏️ この旅程を修正", use_container_width=True,
                            disabled=st.session_state.current_plan is None)
    
    # 旅程生成
    if generate_btn:
        if not destination:
            st.error("⚠️ 目的地を入力してください")
        else:
            try:
                with st.spinner("旅行計画を作成中..."):
                    user_input = {
                        "destination": destination,
                        "days": days,
                        "budget_total": budget_total if budget_total > 0 else None,
                        "themes": themes,
                        "style": style,
                        "start_point": start_point if start_point else None,
                        "mobility": mobility,
                        "constraints": constraints
                    }
                    
                    output = run_agent(user_input, memory_enabled=memory_enabled)
                    st.session_state.last_output = output
                    st.session_state.current_plan = output.get("itinerary_markdown", "")
                    
                    # 過去旅程を再読み込み（最新データを表示するため）
                    knowledge_base = get_knowledge_base()
                    knowledge_base._load_itineraries()
                    
                    # エラーや警告がある場合は注意喚起
                    if output.get("warnings") or (output.get("sources") and len(output.get("sources", [])) == 0):
                        st.warning("⚠️ 一部の情報が取得できませんでした。注意点をご確認ください。")
                    else:
                        st.success("✅ 旅行計画が作成されました！")
                    
                    _display_plan_output(output)
            
            except Exception as e:
                _handle_error(e, "旅程生成")
    
    # 再生成
    elif regenerate_btn:
        if st.session_state.last_output is None:
            st.warning("⚠️ 最初に「旅程を生成」を実行してください")
        else:
            try:
                with st.spinner("別案の旅行計画を作成中..."):
                    # 前回の入力条件を再使用（テーマを少し変えるなど）
                    last_input = {
                        "destination": destination or "京都",
                        "days": days,
                        "budget_total": budget_total if budget_total > 0 else None,
                        "themes": themes,
                        "style": style,
                        "start_point": start_point if start_point else None,
                        "mobility": mobility,
                        "constraints": constraints
                    }
                    
                    output = run_agent(last_input, memory_enabled=memory_enabled)
                    st.session_state.last_output = output
                    st.session_state.current_plan = output.get("itinerary_markdown", "")
                    
                    # 過去旅程を再読み込み（最新データを表示するため）
                    knowledge_base = get_knowledge_base()
                    knowledge_base._load_itineraries()
                    
                    # エラーや警告がある場合は注意喚起
                    if output.get("warnings") or (output.get("sources") and len(output.get("sources", [])) == 0):
                        st.warning("⚠️ 一部の情報が取得できませんでした。注意点をご確認ください。")
                    else:
                        st.success("✅ 別案の旅行計画が作成されました！")
                    
                    _display_plan_output(output)
            
            except Exception as e:
                _handle_error(e, "再生成")
    
    # 編集
    elif edit_btn:
        if st.session_state.current_plan is None:
            st.warning("⚠️ 最初に「旅程を生成」を実行してください")
        else:
            st.divider()
            st.subheader("✏️ 旅程の修正")
            
            edit_request = st.text_area(
                "修正内容を入力してください",
                placeholder="例: Day1の昼食をフレンチに変更したい",
                height=100
            )
            
            if st.button("修正を適用", type="primary"):
                if not edit_request:
                    st.warning("⚠️ 修正内容を入力してください")
                else:
                    try:
                        with st.spinner("旅程を修正中..."):
                            edit_input = PlanEditInput(
                                current_plan=st.session_state.current_plan,
                                user_request=edit_request,
                                additional_search=False
                            )
                            
                            edit_output = edit_itinerary(edit_input)
                            
                            # 更新後の計画を保存
                            st.session_state.current_plan = edit_output.get("updated_plan", "")
                            st.session_state.last_output = {
                                "itinerary_markdown": edit_output.get("updated_plan", ""),
                                "budget_breakdown": {},
                                "cautions": edit_output.get("change_log", []),
                                "sources": edit_output.get("new_sources", []),
                                "warnings": []
                            }
                            
                            st.success("✅ 旅程が修正されました！")
                            
                            # 変更履歴を表示
                            if edit_output.get("change_log"):
                                st.info("📝 変更履歴:")
                                for change in edit_output["change_log"]:
                                    st.write(f"- {change}")
                            
                            _display_plan_output(st.session_state.last_output)
                    
                    except Exception as e:
                        _handle_error(e, "旅程編集", "💡 修正内容を変更するか、しばらく時間をおいてから再度お試しください。")
    
    # 既存の計画を表示
    if st.session_state.last_output and not (generate_btn or regenerate_btn or edit_btn):
        st.divider()
        st.subheader("📋 現在の旅行計画")
        _display_plan_output(st.session_state.last_output)


def _display_plan_output(output: dict):
    """
    旅行計画の出力を表示
    
    Args:
        output: PlanGenerateOutputスキーマに準拠した辞書
    
    注意: 例外が発生しても画面が落ちないようにtry-exceptで囲む
    """
    try:
        # outputがNoneの場合の処理
        if output is None:
            st.error("❌ 出力が取得できませんでした。")
            return
        # 1. 旅程（Markdown）
        itinerary_markdown = output.get("itinerary_markdown", "")
        if itinerary_markdown:
            st.markdown("---")
            st.markdown(itinerary_markdown)
        
        # 2. 参照リンク（sources）
        sources = output.get("sources", [])
        if sources:
            st.markdown("---")
            st.subheader("📚 参照リンク")
            for i, url in enumerate(sources, 1):
                st.markdown(f"{i}. [{url}]({url})")
        
        # 3. 注意点（cautions）
        cautions = output.get("cautions", [])
        if cautions:
            st.markdown("---")
            st.subheader("⚠️ 注意点・要確認事項")
            for caution in cautions:
                st.warning(caution)
        
        # 4. 予算表（budget_breakdown）
        budget_breakdown = output.get("budget_breakdown", {})
        if budget_breakdown:
            st.markdown("---")
            st.subheader("💰 概算予算")
            
            # テーブル形式で表示
            budget_data = []
            for key, value in budget_breakdown.items():
                if key != "total":
                    budget_data.append({
                        "項目": _translate_budget_key(key),
                        "金額": f"¥{value:,}"
                    })
            
            if budget_data:
                st.table(budget_data)
            
            # 合計を強調表示
            total = budget_breakdown.get("total", 0)
            if total > 0:
                st.metric("合計", f"¥{total:,}")
        
        # 5. 警告（warnings）
        warnings = output.get("warnings", [])
        if warnings:
            st.markdown("---")
            st.subheader("🚨 警告")
            for warning in warnings:
                st.error(f"⚠️ {warning}")
    
    except Exception as e:
        _handle_error(e, "表示", "💡 ページを再読み込みするか、別の条件で再試行してください。")


def _translate_budget_key(key: str) -> str:
    """予算項目のキーを日本語に変換"""
    translations = {
        "transportation": "交通費",
        "food": "食事代",
        "activities": "体験・入場料",
        "other": "その他"
    }
    return translations.get(key, key)


if __name__ == "__main__":
    main()
