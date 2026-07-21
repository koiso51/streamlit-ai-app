"""生成AI活用 提案書ジェネレーター — Streamlit アプリ

潜在顧客のWebサイトURLを入力するだけで、その企業の事業内容・課題に即した
生成AI活用のご提案書（PowerPoint）を自動生成します。
"""

import os

import streamlit as st

from utils.pptx_creator import create_proposal_pptx
from utils.proposal_generator import generate_proposal
from utils.rag import list_document_files, load_reference_documents
from utils.web_search import CompanyResearchError, research_company_from_url

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="生成AI活用 提案書ジェネレーター",
    page_icon="🤖",
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
    st.header("⚙️ 設定")

    api_key = st.text_input(
        "Anthropic API Key",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Anthropic API キーを入力してください（ANTHROPIC_API_KEY 環境変数でも設定可）",
    )

    st.divider()
    st.subheader("🏢 提案元（自社）情報")
    firm_name = st.text_input(
        "会社名（任意）",
        placeholder="例：〇〇コンサルティング株式会社",
        help="提案書の表紙・フッターに表示する自社名です。空欄でも生成できます。",
    )

    # Docker mount path takes priority; fall back to a local default.
    DOCKER_MOUNT = "/docs/reference"
    DEFAULT_FOLDER = os.environ.get(
        "REFERENCE_DOCS_PATH",
        DOCKER_MOUNT if os.path.exists(DOCKER_MOUNT) else "",
    )
    folder_path = st.text_input(
        "自社サービス資料・支援実績フォルダパス（任意）",
        value=DEFAULT_FOLDER,
        help="自社のサービス資料・過去の支援実績が入ったフォルダのフルパスを入力してください",
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
    include_roi = st.checkbox("投資規模・ROI試算スライドを含める", value=True)
    include_case_study = st.checkbox("類似支援実績スライドを含める", value=True)

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("🤖 生成AI活用 提案書ジェネレーター")
st.markdown(
    "潜在顧客の **WebサイトURL** を入力するだけで、**サイト調査 + Web検索 + Claude** による "
    "企業固有の生成AI活用提案書を自動生成します。"
)

col_input, col_info = st.columns([3, 2])

with col_input:
    website_url = st.text_input(
        "🌐 潜在顧客のWebサイトURL",
        placeholder="例：https://www.example.co.jp",
        help="コーポレートサイトのトップページURLを入力してください",
    )
    company_name_hint = st.text_input(
        "🏢 企業名（任意）",
        placeholder="正式名称が分かれば入力（未入力の場合はサイトから自動推定）",
    )

with col_info:
    st.markdown(
        """
        #### 生成フロー
        1. 🌐 **サイト調査** — 会社概要・事業内容ページ等を収集
        2. 🔍 **Web検索** — 業界動向・ニュースで補完
        3. 🤖 **Claude 検討** — 課題仮説とアプローチ案を生成
        4. 📊 **PowerPoint** — 提案書スライドを出力
        """
    )

generate_btn = st.button(
    "🚀 提案書を生成する",
    type="primary",
    disabled=not bool(website_url.strip()),
)

# ---------------------------------------------------------------------------
# Generation flow
# ---------------------------------------------------------------------------
if generate_btn:
    if not api_key:
        st.error("⚠️ Anthropic API Key が設定されていません。サイドバーで入力するか、環境変数 ANTHROPIC_API_KEY を設定してください。")
        st.stop()

    if not website_url.strip():
        st.error("潜在顧客のWebサイトURLを入力してください。")
        st.stop()

    progress = st.progress(0, text="準備中…")
    status = st.empty()

    try:
        # --- Step 1: Load reference documents (own firm materials) ---
        status.info("📚 自社の資料を読み込んでいます…")
        progress.progress(10, text="自社資料を読み込み中…")
        reference_context = load_reference_documents(folder_path)

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
                reference_context = (
                    (reference_context + "\n\n" if reference_context else "")
                    + "\n\n".join(extra_parts)
                )

        if reference_context:
            st.caption(f"✅ 自社資料読み込み完了（{len(reference_context):,} 文字）")

        # --- Step 2: Research the prospect's website ---
        status.info(f"🌐 {website_url} を調査しています…（数十秒かかる場合があります）")
        progress.progress(25, text="サイト調査中…")
        research = research_company_from_url(website_url, api_key, company_name_hint.strip())
        company_name = research.company_name

        status.info(f"🔍 {company_name} の業界動向・ニュースをWeb検索しています…")
        progress.progress(45, text="Web検索中…")

        # --- Step 3: Generate proposal ---
        status.info("✍️ 提案書の内容を Claude で生成しています…（1〜2 分かかる場合があります）")
        progress.progress(60, text="提案内容を生成中…")
        proposal = generate_proposal(
            company_name=company_name,
            research_site_text=research.site_text,
            research_web_summary=research.web_search_summary,
            reference_context=reference_context,
            api_key=api_key,
            firm_name=firm_name.strip(),
            include_roi=include_roi,
            include_case_study=include_case_study,
        )

        # --- Step 4: Build PowerPoint ---
        status.info("📊 PowerPoint スライドを作成しています…")
        progress.progress(85, text="PowerPoint を作成中…")
        pptx_bytes = create_proposal_pptx(
            proposal, company_name, firm_name.strip(), sources=research.sources
        )

        progress.progress(100, text="完了！")
        status.success(f"✅ **{company_name}** 様向け提案書の生成が完了しました！")

        # ---------------------------------------------------------------------------
        # Display summary
        # ---------------------------------------------------------------------------
        st.divider()
        st.subheader("📋 提案書サマリー")

        summary_col, dl_col = st.columns([3, 1])

        with summary_col:
            overview = proposal.get("company_overview", {}) or {}
            if overview.get("summary"):
                st.markdown(f"**企業概要:** {overview['summary']}")
            domain_scale = "　｜　".join(
                filter(None, [overview.get("business_domain", ""), overview.get("scale", "")])
            )
            if domain_scale:
                st.caption(domain_scale)

            segments = proposal.get("business_segments", [])
            if segments:
                st.markdown("**主要事業:**")
                for seg in segments:
                    st.markdown(f"- **{seg.get('name', '')}** — {seg.get('description', '')}")

            challenges = proposal.get("challenges", [])
            if challenges:
                st.markdown("**課題仮説:**")
                for c in challenges:
                    st.markdown(f"- **[{c.get('segment', '')}] {c.get('title', '')}** — {c.get('description', '')}")

            approaches = proposal.get("approaches", [])
            if approaches:
                with st.expander("生成AI活用アプローチ案 詳細を見る"):
                    for a in approaches:
                        st.markdown(
                            f"**{a.get('title', '')}**（対応課題: {a.get('related_challenge', '')}）  \n"
                            f"{a.get('description', '')}  \n"
                            f"*支援内容: {a.get('consulting_support', '')}*  \n"
                            f"期待効果: {a.get('expected_effect', '')}"
                        )
                        st.divider()

            phases = proposal.get("roadmap_phases", [])
            if phases:
                with st.expander("導入・計画の進め方"):
                    for p in phases:
                        st.markdown(
                            f"**{p.get('phase', '')}**（{p.get('duration', '')}） — "
                            f"{p.get('description', '')}  \n"
                            f"成果物: {p.get('deliverables', '')}"
                        )

            roi = proposal.get("roi_estimate", "")
            if roi and include_roi:
                with st.expander("想定投資規模・ROI試算"):
                    st.write(roi)

            case = proposal.get("case_study", "")
            if case and include_case_study:
                with st.expander("類似支援実績"):
                    st.write(case)

            qa_list = proposal.get("anticipated_qa", [])
            if qa_list:
                with st.expander("想定される論点・Q&A"):
                    for qa in qa_list:
                        st.markdown(f"**Q. {qa.get('question', '')}**  \nA. {qa.get('answer', '')}")
                        st.divider()

            next_steps = proposal.get("next_steps", [])
            if next_steps:
                st.markdown("**次のステップ:**")
                for i, step in enumerate(next_steps, 1):
                    st.markdown(f"{i}. {step}")

        with dl_col:
            st.download_button(
                label="📥 提案書をダウンロード\n（PowerPoint）",
                data=pptx_bytes,
                file_name=f"生成AI活用提案書_{company_name}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary",
            )

        if research.sources:
            with st.expander("🌐 調査した情報源"):
                for src in research.sources:
                    st.write(src)
        if research.web_search_summary:
            with st.expander("🔍 Web検索結果（参考情報）"):
                st.write(research.web_search_summary)

    except CompanyResearchError as exc:
        progress.empty()
        status.error(f"❌ {exc}")
    except Exception as exc:
        progress.empty()
        status.error(f"❌ エラーが発生しました: {exc}")
        with st.expander("詳細エラー情報"):
            st.exception(exc)
