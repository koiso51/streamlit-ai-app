"""FASTLabel 提案書作成ツール — Streamlit アプリ"""

import os

import streamlit as st

from utils.pptx_creator import create_proposal_pptx
from utils.proposal_generator import generate_proposal
from utils.rag import list_document_files, load_fastlabel_documents
from utils.web_search import search_company_info

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FASTLabel 提案書作成ツール",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — minimal polish
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stButton > button { width: 100%; }
    .block-container { padding-top: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://fastlabel.ai/favicon.ico",
        width=32,
    ) if False else None  # skip if no network; keep layout clean

    st.header("⚙️ 設定")

    _raw_key = st.text_input(
        "Anthropic API Key",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Anthropic API キーを入力してください（ANTHROPIC_API_KEY 環境変数でも設定可）",
    )
    api_key = _raw_key.strip()  # 前後のスペース・改行を除去

    if api_key and not api_key.startswith("sk-ant-"):
        st.warning("⚠️ API キーは `sk-ant-` で始まる形式が正しいです。https://console.anthropic.com/ で確認してください。")
    elif not api_key:
        st.info("💡 API キーが未入力です。https://console.anthropic.com/ で取得できます。")

    # Docker mount path takes priority; fall back to original Windows path
    DOCKER_MOUNT = "/docs/fastlabel"
    DEFAULT_FOLDER = (
        DOCKER_MOUNT if os.path.exists(DOCKER_MOUNT)
        else r"C:\Users\oisok\OneDrive\Desktop\Fastlabel"
    )
    folder_path = st.text_input(
        "FASTLabel 資料フォルダパス",
        value=DEFAULT_FOLDER,
        help="FASTLabel のサービス資料・事例が入ったフォルダのフルパスを入力してください",
    )

    st.divider()
    st.subheader("📂 資料の読み込み状況")

    doc_files = list_document_files(folder_path)
    if doc_files:
        st.success(f"✅ {len(doc_files)} 件の資料を検出しました")
        with st.expander("ファイル一覧を見る"):
            for f in doc_files:
                st.caption(f"📄 {f.name}")
    elif folder_path and os.path.exists(folder_path):
        st.warning("対応ファイル（PDF / DOCX / PPTX / TXT）が見つかりません")
    else:
        st.info("フォルダパスを設定してください\n（資料なしでも提案書は生成できます）")

    st.divider()
    st.subheader("📤 資料をアップロード（任意）")
    uploaded_files = st.file_uploader(
        "フォルダが使えない場合はここからアップロード",
        type=["pdf", "docx", "pptx", "txt"],
        accept_multiple_files=True,
        help="PDF / DOCX / PPTX / TXT に対応しています",
    )

    st.divider()
    st.subheader("🎛️ 出力オプション")
    include_roi = st.checkbox("ROI 試算スライドを含める", value=True)
    include_cases = st.checkbox("導入事例スライドを含める", value=True)

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("📊 FASTLabel 提案書作成ツール")
st.markdown(
    "クライアント企業名を入力するだけで、**Web 検索 + 社内資料 RAG + Claude** による提案書を自動生成します。"
)

col_input, col_info = st.columns([3, 2])

with col_input:
    company_name = st.text_input(
        "🏢 クライアント企業名",
        placeholder="例：トヨタ自動車、ソフトバンク、楽天グループ …",
        help="提案書を作成したいクライアント企業の正式名称を入力してください",
    )

with col_info:
    st.markdown(
        """
        #### 生成フロー
        1. 🔍 **Web 検索** — 企業の課題・事業概況を調査
        2. 📚 **RAG** — FASTLabel 社内資料を参照
        3. 🤖 **Claude 検討** — 課題仮説と提案内容を生成
        4. 📊 **PowerPoint** — 提案書スライドを出力
        """
    )

_btn_disabled = not bool(company_name) or not bool(api_key)
_btn_help = (
    "企業名と Anthropic API Key の両方を入力してください"
    if _btn_disabled else None
)
generate_btn = st.button(
    "🚀 提案書を生成する",
    type="primary",
    disabled=_btn_disabled,
    help=_btn_help,
)

# ---------------------------------------------------------------------------
# Generation flow
# ---------------------------------------------------------------------------
if generate_btn:
    if not api_key:
        st.error("⚠️ Anthropic API Key が設定されていません。サイドバーで入力するか、環境変数 ANTHROPIC_API_KEY を設定してください。")
        st.stop()

    if not company_name.strip():
        st.error("企業名を入力してください。")
        st.stop()

    company_name = company_name.strip()
    progress = st.progress(0, text="準備中…")
    status = st.empty()

    try:
        # --- Step 1: Load RAG documents ---
        status.info("📚 FASTLabel 社内資料を読み込んでいます…")
        progress.progress(10, text="社内資料を読み込み中…")
        fastlabel_context = load_fastlabel_documents(folder_path)

        # Also ingest any directly uploaded files
        if uploaded_files:
            import tempfile, pathlib
            extra_parts: list[str] = []
            for uf in uploaded_files:
                suffix = pathlib.Path(uf.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uf.read())
                    tmp_path = pathlib.Path(tmp.name)
                from utils.rag import _extract_text
                text = _extract_text(tmp_path)
                if text:
                    extra_parts.append(f"=== {uf.name} ===\n{text.strip()}")
                tmp_path.unlink(missing_ok=True)
            if extra_parts:
                fastlabel_context = (
                    (fastlabel_context + "\n\n" if fastlabel_context else "")
                    + "\n\n".join(extra_parts)
                )

        if fastlabel_context:
            st.caption(f"✅ 資料読み込み完了（{len(fastlabel_context):,} 文字）")

        # --- Step 2: Web search ---
        status.info(f"🔍 {company_name} の情報を Web 検索しています…（数十秒かかる場合があります）")
        progress.progress(25, text="Web 検索中…")
        company_info = search_company_info(company_name, api_key)

        # --- Step 3: Generate proposal ---
        status.info("✍️ 提案書の内容を Claude で生成しています…（1〜2 分かかる場合があります）")
        progress.progress(55, text="提案内容を生成中…")
        proposal = generate_proposal(
            company_name=company_name,
            company_info=company_info,
            fastlabel_context=fastlabel_context,
            api_key=api_key,
            include_cases=include_cases,
            include_roi=include_roi,
        )

        # --- Step 4: Build PowerPoint ---
        status.info("📊 PowerPoint スライドを作成しています…")
        progress.progress(85, text="PowerPoint を作成中…")
        pptx_bytes = create_proposal_pptx(proposal, company_name)

        progress.progress(100, text="完了！")
        status.success(f"✅ **{company_name}** 様向け提案書の生成が完了しました！")

        # ---------------------------------------------------------------------------
        # Display summary
        # ---------------------------------------------------------------------------
        st.divider()
        st.subheader("📋 提案書サマリー")

        summary_col, dl_col = st.columns([3, 1])

        with summary_col:
            dept = proposal.get("target_department", "—")
            persona = proposal.get("target_persona", "—")
            st.markdown(f"**想定部門:** {dept}　｜　**キーパーソン:** {persona}")

            challenges = proposal.get("challenges", [])
            if challenges:
                st.markdown("**課題仮説:**")
                for c in challenges:
                    st.markdown(f"- {c}")

            summary = proposal.get("proposal_summary", "")
            if summary:
                st.info(f"💡 **提案概要:** {summary}")

            details: list[dict] = proposal.get("proposal_details", [])
            if details:
                with st.expander("提案内容 詳細を見る"):
                    for d in details:
                        st.markdown(
                            f"**{d.get('service_name', '')}**  \n"
                            f"{d.get('value', '')}  \n"
                            f"*差別化: {d.get('differentiator', '')}*  \n"
                            f"期待効果: {d.get('expected_effect', '')}"
                        )
                        st.divider()

            roi = proposal.get("roi_estimate", "")
            if roi and include_roi:
                with st.expander("ROI 試算"):
                    st.write(roi)

            case = proposal.get("case_study", "")
            if case and include_cases:
                with st.expander("導入事例"):
                    st.write(case)

            next_steps = proposal.get("next_steps", [])
            if next_steps:
                st.markdown("**次のステップ:**")
                for i, step in enumerate(next_steps, 1):
                    st.markdown(f"{i}. {step}")

        with dl_col:
            st.download_button(
                label="📥 提案書をダウンロード\n（PowerPoint）",
                data=pptx_bytes,
                file_name=f"FASTLabel_提案書_{company_name}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary",
            )

        # Show web search result
        if company_info:
            with st.expander("🔍 Web 検索結果（参考情報）"):
                st.write(company_info)

    except Exception as exc:
        progress.empty()
        err_str = str(exc)
        if "401" in err_str or "authentication_error" in err_str or "invalid x-api-key" in err_str:
            status.error(
                "❌ **APIキー認証エラー（401）**\n\n"
                "サイドバーの「Anthropic API Key」欄を確認してください。\n"
                "- キーは `sk-ant-` で始まります\n"
                "- https://console.anthropic.com/ でキーを確認・再発行できます\n"
                "- コピー時にスペースが入っていないか確認してください"
            )
        elif "429" in err_str or "rate_limit" in err_str:
            status.error("❌ **APIレート制限エラー（429）** — しばらく待ってから再試行してください。")
        else:
            status.error(f"❌ エラーが発生しました: {exc}")
        with st.expander("詳細エラー情報"):
            st.exception(exc)
