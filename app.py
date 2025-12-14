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
if "show_edit_form" not in st.session_state:
    st.session_state.show_edit_form = False
if "edit_applied" not in st.session_state:
    st.session_state.edit_applied = False
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False


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
        layout="wide",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    
    # Streamlitのデフォルトメニューを非表示にする（CSS）
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    st.title("✈️ Travel Planner Agent")
    st.markdown("AIを活用した旅行計画作成アシスタント")
    
    # 日本語メニューをメイン画面に表示
    menu_col1, menu_col2, menu_col3 = st.columns([1, 1, 6])
    with menu_col1:
        if st.button("🔄 再読み込み", use_container_width=True, help="ページを再読み込みします"):
            st.rerun()
    with menu_col2:
        if st.button("⚙️ 設定", use_container_width=True, help="設定を開きます"):
            st.session_state.show_settings = not st.session_state.show_settings
    
    # 設定画面の表示
    if st.session_state.show_settings:
        st.divider()
        st.subheader("⚙️ 設定")
        
        with st.expander("📊 アプリケーション設定", expanded=True):
            st.write("**Memory機能**")
            st.caption("Memory機能を有効にすると、過去の会話履歴を参照してよりパーソナライズされた提案が可能になります。")
            st.caption(f"現在の状態: {'✅ 有効' if st.session_state.memory_enabled else '❌ 無効'}")
            st.caption("💡 サイドバーから変更できます")
        
        with st.expander("🔍 検索設定", expanded=True):
            from src.config import MAX_SEARCH_CALLS, MAX_ITERATIONS, TIMEOUT_SECONDS
            st.write("**検索回数上限**")
            st.caption(f"最大検索回数: {MAX_SEARCH_CALLS}回")
            st.caption("💡 検索結果が0件の場合、自動的にクエリを拡張して再試行します")
            
            st.write("**タイムアウト設定**")
            st.caption(f"タイムアウト時間: {TIMEOUT_SECONDS}秒")
            st.caption("💡 検索がタイムアウトした場合、エラーメッセージを表示します")
        
        with st.expander("💾 データ管理", expanded=True):
            st.write("**保存データ**")
            knowledge_base = get_knowledge_base()
            favorites_count = len(knowledge_base.get_favorites())
            memos_count = len(knowledge_base.get_memos())
            itineraries_count = len(knowledge_base.get_itineraries())
            
            st.caption(f"お気に入り: {favorites_count}件")
            st.caption(f"旅行メモ: {memos_count}件")
            st.caption(f"過去旅程: {itineraries_count}件")
            st.caption("💡 サイドバーの「📚 マイナレッジ」から管理できます")
        
        with st.expander("📝 ログ設定", expanded=True):
            st.write("**ログファイル**")
            st.caption("ログファイルは `logs/` ディレクトリに保存されます")
            st.caption("💡 エラーが発生した場合、ログファイルを確認してください")
            
            if st.button("ログディレクトリを開く", use_container_width=True):
                st.info("💡 ログファイルは `logs/travel_planner_YYYYMMDD.log` の形式で保存されます")
        
        with st.expander("ℹ️ アプリケーション情報", expanded=False):
            st.write("**バージョン情報**")
            st.caption("Travel Planner Agent v1.0")
            st.caption("AIを活用した旅行計画作成アシスタント")
            
            st.write("**技術スタック**")
            st.caption("• Streamlit: Webアプリケーションフレームワーク")
            st.caption("• OpenAI GPT-4: LLMによる旅程生成")
            st.caption("• SerpAPI: Web検索による最新情報取得")
            st.caption("• LangChain: LLM統合フレームワーク")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("設定を閉じる", use_container_width=True):
                st.session_state.show_settings = False
                st.rerun()
        with col2:
            if st.button("ページを再読み込み", use_container_width=True):
                st.rerun()
        
        st.divider()
    
    st.divider()
    
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
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.write(f"**{fav.get('name')}** ({fav.get('category')})")
                                if fav.get('location'):
                                    st.caption(f"📍 {fav.get('location')}")
                                if fav.get('notes'):
                                    st.caption(f"📝 {fav.get('notes')[:100]}{'...' if len(fav.get('notes', '')) > 100 else ''}")
                            with col2:
                                if st.button("詳細", key=f"view_fav_{fav.get('id')}"):
                                    # お気に入りの詳細をメイン画面に表示
                                    detail_text = f"## 📌 {fav.get('name')}\n\n"
                                    detail_text += f"**カテゴリ:** {fav.get('category')}\n\n"
                                    if fav.get('location'):
                                        detail_text += f"**場所:** {fav.get('location')}\n\n"
                                    if fav.get('notes'):
                                        detail_text += f"**メモ:**\n{fav.get('notes')}\n\n"
                                    if fav.get('url'):
                                        detail_text += f"**リンク:** [{fav.get('url')}]({fav.get('url')})\n\n"

                                    st.session_state.current_plan = detail_text
                                    st.session_state.last_output = {
                                        "itinerary_markdown": detail_text,
                                        "budget_breakdown": {},
                                        "cautions": [],
                                        "sources": [],
                                        "warnings": []
                                    }
                                    st.rerun()
                            with col3:
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
                    memo_content = st.text_area("内容 *", key="memo_content", height=150)
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
                        memo_id = memo.get('id')
                        memo_title = memo.get('title', '')
                        memo_content = memo.get('content', '')
                        memo_tags = memo.get('tags', [])
                        memo_created = memo.get('created_at', '')
                        memo_updated = memo.get('updated_at', '')
                        
                        # メモの表示
                        with st.expander(f"📝 {memo_title}", expanded=False):
                            # タグの表示
                            if memo_tags:
                                tag_str = " ".join([f"`{tag}`" for tag in memo_tags])
                                st.markdown(f"**タグ:** {tag_str}")
                            
                            # 内容の表示
                            st.markdown("**内容:**")
                            st.text_area("", value=memo_content, height=150, key=f"memo_content_display_{memo_id}", disabled=True)
                            
                            # 日付情報
                            if memo_created:
                                st.caption(f"作成日: {memo_created[:10] if len(memo_created) >= 10 else memo_created}")
                            if memo_updated and memo_updated != memo_created:
                                st.caption(f"更新日: {memo_updated[:10] if len(memo_updated) >= 10 else memo_updated}")
                            
                            # 編集フォーム
                            edit_key = f"edit_memo_{memo_id}"
                            if edit_key not in st.session_state:
                                st.session_state[edit_key] = False
                            
                            if st.button("✏️ 編集", key=f"edit_btn_{memo_id}"):
                                st.session_state[edit_key] = True
                            
                            if st.session_state[edit_key]:
                                with st.form(f"edit_memo_form_{memo_id}"):
                                    edit_title = st.text_input("タイトル *", value=memo_title, key=f"edit_title_{memo_id}")
                                    edit_content = st.text_area("内容 *", value=memo_content, height=150, key=f"edit_content_{memo_id}")
                                    edit_tags_str = st.text_input("タグ（カンマ区切り）", value=", ".join(memo_tags), key=f"edit_tags_{memo_id}")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.form_submit_button("保存", type="primary", use_container_width=True):
                                            if edit_title and edit_content:
                                                edit_tags = [t.strip() for t in edit_tags_str.split(",") if t.strip()] if edit_tags_str else []
                                                knowledge_base.update_memo(memo_id, edit_title, edit_content, edit_tags)
                                                st.success(f"✅ {edit_title}を更新しました")
                                                st.session_state[edit_key] = False
                                                st.rerun()
                                    with col2:
                                        if st.form_submit_button("キャンセル", use_container_width=True):
                                            st.session_state[edit_key] = False
                                            st.rerun()
                        
                        # 削除ボタン
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col3:
                            if st.button("削除", key=f"del_memo_{memo_id}"):
                                knowledge_base.remove_memo(memo_id)
                                st.success(f"✅ {memo_title}を削除しました")
                                st.rerun()
                        st.divider()
                else:
                    st.info("旅行メモがありません")
            
            with tab3:
                st.write("**過去旅程**")
                # 最新データを再読み込み
                knowledge_base._load_itineraries()
                # 過去旅程の表示
                itineraries = knowledge_base.get_itineraries(limit=10)
                if itineraries:
                    for itin in itineraries:
                        with st.container():
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.write(f"**{itin.get('destination')} {itin.get('days')}日プラン**")
                                st.caption(f"作成日: {itin.get('created_at', '')[:10]}")
                                if itin.get('metadata'):
                                    meta = itin.get('metadata', {})
                                    if meta.get('themes'):
                                        st.caption(f"テーマ: {', '.join(meta.get('themes', []))}")
                            with col2:
                                if st.button("表示", key=f"view_itinerary_{itin.get('id')}"):
                                    # 過去旅程をメイン画面に表示
                                    itinerary_markdown = itin.get('itinerary_markdown', '')
                                    st.session_state.current_plan = itinerary_markdown
                                    st.session_state.last_output = {
                                        "itinerary_markdown": itinerary_markdown,
                                        "budget_breakdown": itin.get('metadata', {}).get('budget_breakdown', {}),
                                        "cautions": [],
                                        "sources": [],
                                        "warnings": []
                                    }
                                    st.rerun()
                            with col3:
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
                            disabled=st.session_state.current_plan is None or st.session_state.show_edit_form)
    
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
                    
                    # 編集フォームを閉じる
                    st.session_state.show_edit_form = False
                    st.session_state.edit_applied = False
                    
                    # エラーや警告がある場合は注意喚起
                    if output.get("warnings") or (output.get("sources") and len(output.get("sources", [])) == 0):
                        st.warning("⚠️ 一部の情報が取得できませんでした。注意点をご確認ください。")
                    else:
                        st.success("✅ 旅行計画が作成されました！")
                    
                    st.divider()
                    st.subheader("📋 生成された旅行計画")
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
                    
                    # 編集フォームを閉じる
                    st.session_state.show_edit_form = False
                    st.session_state.edit_applied = False
                    
                    # エラーや警告がある場合は注意喚起
                    if output.get("warnings") or (output.get("sources") and len(output.get("sources", [])) == 0):
                        st.warning("⚠️ 一部の情報が取得できませんでした。注意点をご確認ください。")
                    else:
                        st.success("✅ 別案の旅行計画が作成されました！")
                    
                    st.divider()
                    st.subheader("📋 再生成された旅行計画")
                    _display_plan_output(output)
            
            except Exception as e:
                _handle_error(e, "再生成")
    
    # 編集ボタンが押された場合
    if edit_btn:
        if st.session_state.current_plan is None:
            st.warning("⚠️ 最初に「旅程を生成」を実行してください")
        else:
            # 編集ボタンが押されたら編集フォームを表示
            st.session_state.show_edit_form = True
            st.session_state.edit_applied = False
    
    # 編集フォームの表示
    if st.session_state.show_edit_form and st.session_state.current_plan:
        st.divider()
        st.subheader("✏️ 旅程の修正")
        
        edit_request = st.text_area(
            "修正内容を入力してください",
            placeholder="例: Day1の昼食をフレンチに変更したい",
            height=100,
            key="edit_request_input"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            apply_edit_btn = st.button("修正を適用", type="primary", use_container_width=True, key="apply_edit_btn")
        
        with col2:
            cancel_edit_btn = st.button("キャンセル", use_container_width=True, key="cancel_edit_btn")
        
        # 修正を適用
        if apply_edit_btn:
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
                        updated_plan = edit_output.get("updated_plan", "")
                        if updated_plan:
                            st.session_state.current_plan = updated_plan
                            st.session_state.last_output = {
                                "itinerary_markdown": updated_plan,
                                "budget_breakdown": st.session_state.last_output.get("budget_breakdown", {}) if st.session_state.last_output else {},
                                "cautions": edit_output.get("change_log", []) + (st.session_state.last_output.get("cautions", []) if st.session_state.last_output else []),
                                "sources": edit_output.get("new_sources", []) + (st.session_state.last_output.get("sources", []) if st.session_state.last_output else []),
                                "warnings": st.session_state.last_output.get("warnings", []) if st.session_state.last_output else []
                            }
                            
                            # 編集フォームを閉じる
                            st.session_state.show_edit_form = False
                            st.session_state.edit_applied = True
                            
                            st.success("✅ 旅程が修正されました！")
                            
                            # 変更履歴を表示
                            if edit_output.get("change_log"):
                                st.info("📝 変更履歴:")
                                for change in edit_output["change_log"]:
                                    st.write(f"- {change}")
                            
                            # 修正後の旅程を表示
                            st.divider()
                            st.subheader("📋 修正後の旅行計画")
                            _display_plan_output(st.session_state.last_output)
                        else:
                            st.error("❌ 旅程の修正に失敗しました。修正内容を確認してください。")
                
                except Exception as e:
                    _handle_error(e, "旅程編集", "💡 修正内容を変更するか、しばらく時間をおいてから再度お試しください。")
        
        # キャンセル
        if cancel_edit_btn:
            st.session_state.show_edit_form = False
            st.session_state.edit_applied = False
            st.rerun()
    
    # 既存の計画を表示（編集フォームが表示されていない場合）
    if st.session_state.last_output and not st.session_state.show_edit_form:
        if not generate_btn and not regenerate_btn:
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
