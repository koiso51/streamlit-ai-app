"""Proposal generator: uses Claude to create a structured proposal JSON.

Two-phase reasoning approach for deep challenge hypotheses:
  Phase 1 (Sonnet) — Extract a structured fact map of the company's specific
                     AI/ML projects, departments, and data activities.
  Phase 2 (Opus)   — Reason from those concrete facts to evidence-based,
                     business-specific challenge hypotheses and proposals.
"""

import json
import re

import anthropic

# ---------------------------------------------------------------------------
# System prompt — FASTLabel sales consultant persona
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """あなたはFASTLabel株式会社のエンタープライズ営業コンサルタントです。

【FASTLabelについて】
FASTLabelはAI開発に必要な「教師データ（トレーニングデータ）作成」を効率化するデータアノテーション・ラベリングプラットフォームです。

【主要サービス・機能】
- 高精度アノテーションツール（画像・動画・テキスト・音声・3D点群）
- AIアシスト機能による半自動ラベリングで作業効率最大80%改善
- 品質管理ワークフロー（レビュー・承認・QAプロセス）
- プロジェクト管理・進捗可視化ダッシュボード
- APIによるMLパイプライン連携
- セキュアな国内データ処理環境

【差別化ポイント】
- 国産プラットフォームによる高いセキュリティ・コンプライアンス対応
- 日本語UIと日本語サポート
- AIアシストで競合比3〜5倍の作業効率
- 導入から運用まで一貫したCSサポート
- 多様なデータ形式への対応（業界最多水準）"""

# ---------------------------------------------------------------------------
# Phase 1: Fact-map extraction prompt
# ---------------------------------------------------------------------------

_FACT_MAP_SCHEMA = """{
  "business_areas": [
    {
      "name": "事業領域名（例: 自動運転開発、製造ライン検査、医療画像診断など）",
      "department": "担当部門・組織名（具体的に）",
      "ai_project": "AIプロジェクト・製品・サービス名（具体的に）",
      "data_type": "必要なデータ種別（例: カメラ映像、CT画像、テキストログなど）",
      "annotation_need": "アノテーション・ラベリングが必要な理由・用途",
      "scale_hint": "規模感のヒント（求人数・投資額・対象拠点数など判明した情報）"
    }
  ],
  "overall_ai_maturity": "AI活用成熟度の評価（黎明期/拡大期/高度化期）",
  "key_bottleneck_area": "最もデータ課題が深刻と推測される事業領域（1つ）",
  "evidence_summary": "上記の根拠となった情報源・事実のサマリー"
}"""

_FACT_MAP_INSTRUCTIONS = """以下の企業調査情報を分析し、AIデータラベリングの観点から重要な「事実マップ」を作成してください。

【重要】情報が明示されていない場合は、業界知識と求人内容・IR・技術ブログから合理的に推論してください。
推論の場合は「〜と推測される」と明記してください。

以下のJSON形式のみで出力してください（マークダウンコードブロック不要）：
"""

# ---------------------------------------------------------------------------
# Phase 2: Deep hypothesis generation prompt
# ---------------------------------------------------------------------------

_OUTPUT_SCHEMA = """{
  "target_department": "想定部門・職種（例: AI推進本部、データサイエンスグループ、研究開発部門 など具体的に）",
  "target_persona": "キーパーソンの役職・ミッション（例: AIプロジェクトリーダー、CDO直下の推進担当など）",
  "company_overview": "企業・業界のAI活用状況サマリー（2-3文）",
  "challenges": [
    "【事業名】の【部門/工程】において、【具体的な課題】が発生しており、【ビジネスインパクト】が生じている可能性がある。（根拠: 〜）",
    "【事業名】の【部門/工程】において、【具体的な課題】が発生しており、【ビジネスインパクト】が生じている可能性がある。（根拠: 〜）",
    "【事業名】の【部門/工程】において、【具体的な課題】が発生しており、【ビジネスインパクト】が生じている可能性がある。（根拠: 〜）"
  ],
  "challenge_details": [
    {
      "title": "課題タイトル（事業名・部門名を含む短いタイトル）",
      "description": "課題の詳細（どの事業のどの工程で、なぜ課題が発生しているか。具体的なプロセスや技術的背景を含む）",
      "business_impact": "放置した場合のビジネスインパクト（競合比較・開発遅延・コスト増など定量的に）",
      "evidence": "この課題仮説の根拠（求人内容・IR・業界トレンド・類似事例等）"
    }
  ],
  "proposal_summary": "提案の一言サマリー（エレベーターピッチ）",
  "proposal_details": [
    {
      "service_name": "FASTLabelの具体的なサービス/機能名（汎用名ではなく実機能名で）",
      "challenge_link": "この提案が解決する課題のタイトル（challenge_detailsのtitleと一致させる）",
      "implementation_scenario": "このクライアントの具体的な部門・工程・業務フローにどう組み込むか（誰が・どの工程で・どのようにFASTLabelを使うか）",
      "before_after": "【導入前】現状の具体的な状態（数値・工程・課題）→【導入後】FASTLabel導入後の状態（数値・改善指標）",
      "why_fastlabel_here": "このクライアントの状況において他社SaaS・内製開発ではなくFASTLabelである理由（競合比較・自社開発コスト・セキュリティ・スピードなど文脈に合わせて）",
      "expected_effect": "期待効果（定量：工数削減率・精度改善・コスト削減額など）"
    }
  ],
  "roi_estimate": "ROI・期待効果の試算（工数削減率、期間、金額換算など具体的に）",
  "case_study": "類似業界・用途の導入事例サマリー（なければ空文字）",
  "next_steps": [
    "次のアクション1（具体的）",
    "次のアクション2"
  ]
}"""

_PROPOSAL_INSTRUCTIONS = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【A. 課題仮説の必須要件】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
以下の3層構造で各仮説を記述してください：

  層1（事実層）: 「〇〇社の△△事業において、□□というAIプロジェクトに取り組んでいる」
  層2（課題層）: 「そのプロジェクトの◇◇工程で、〜という理由により、××という課題が発生している」
  層3（影響層）: 「その結果、▲▲というビジネスインパクトが生じており、競合比で〜の遅れが生じている可能性がある」

【課題仮説 NG例】
  ✗「教師データ作成コストが高い」
  ✗「アノテーション品質にばらつきがある」

【課題仮説 OK例】
  ✓「自動運転開発事業のセンサーフュージョン開発チームにおいて、カメラ・LiDARの融合データアノテーションを外注ベンダー複数社に分散発注しているため、ラベリング基準の解釈齟齬が生じ、モデル学習の再実行コストが増大している可能性がある。（根拠: AI関連求人でLiDAR/カメラの記載、複数ベンダー管理経験を求める記載あり）」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【B. 提案内容（proposal_details）の必須要件】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
各提案は以下の4要素をすべて含めてください：

  要素1（導入シナリオ）: 「誰が・どの部門の・どの工程で・具体的にFASTLabelをどう使うか」を記述
  要素2（ビフォーアフター）: 「現状の具体的な数値・状態」→「FASTLabel導入後の具体的な数値・状態」を対比
  要素3（ここでFASTLabelである理由）: 他社SaaS・内製・外注継続との比較で、このクライアントの状況においてFASTLabelが最適な理由
  要素4（課題との紐付け）: challenge_detailsのどの課題を解決するかを明示

【提案内容 NG例（浅い）】
  ✗ service_name:「AIアシストアノテーション」
    value:「作業効率を80%改善します」
    differentiator:「国産プラットフォームで安心」
    expected_effect:「コスト削減」

【提案内容 OK例（深い）】
  ✓ service_name:「3D点群アノテーション＋品質管理ワークフロー」
    challenge_link:「自動運転センサーフュージョン開発のラベリング品質課題」
    implementation_scenario:「センサーフュージョン開発チーム（推定20名規模）が週次モデル学習サイクルで使用する
      LiDAR/カメラ融合データ（1バッチ5,000フレーム規模）のアノテーション工程に導入。
      現在3社に分散している外注ベンダーをFASTLabelのプロジェクト管理下に一元化し、
      同一UIでラベリング基準書・サンプルを共有、IAA（アノテーター間一致率）をリアルタイム監視する。」
    before_after:「【導入前】IAA 62%、外注3社への個別指示で品質担保に週3日のPM工数、
      モデル再学習サイクル8週間 →
      【導入後】IAA 95%以上（品質ゲート設定）、品質管理工数70%削減、
      モデル再学習サイクル3週間以内」
    why_fastlabel_here:「3D点群対応は国内SaaSではFASTLabel・Scale AI・Labelboxの3択。
      Scale AI/Labelboxは海外サーバー処理のため車載AI開発の機密データを社外に出せないという
      セキュリティ制約がある。内製ツール開発は初期6ヶ月・1,500万円以上の投資が必要で
      スピード要件を満たさない。FASTLabelは国内処理＋3D対応＋API連携の唯一の選択肢。」
    expected_effect:「アノテーション工数60%削減（月間300時間→120時間）、
      モデル開発サイクル62%短縮（8週間→3週間）、外注品質管理コスト年間1,200万円削減」

以下のJSON形式のみで出力してください（マークダウンコードブロック不要）：
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_proposal(
    company_name: str,
    company_info: str,
    fastlabel_context: str,
    api_key: str,
    include_cases: bool = True,
    include_roi: bool = True,
) -> dict:
    """
    Two-phase generation:
      Phase 1 — Build a structured fact map of the company's AI activities (Sonnet, fast).
      Phase 2 — Generate deep, evidence-based proposals from the fact map (Opus + thinking).
    """
    client = anthropic.Anthropic(api_key=api_key, max_retries=8)

    raw_info = company_info or f"企業名: {company_name}（調査情報なし。業界知識から推定してください）"

    # --- Phase 1: Extract structured fact map ---
    fact_map = _extract_fact_map(client, company_name, raw_info)

    # --- Phase 2: Generate deep proposal from facts ---
    return _generate_deep_proposal(
        client=client,
        company_name=company_name,
        raw_info=raw_info,
        fact_map=fact_map,
        fastlabel_context=fastlabel_context,
        include_cases=include_cases,
        include_roi=include_roi,
    )


# ---------------------------------------------------------------------------
# Phase 1 implementation
# ---------------------------------------------------------------------------

def _extract_fact_map(
    client: anthropic.Anthropic,
    company_name: str,
    company_info: str,
) -> dict:
    """
    Use Sonnet to extract a structured map of the company's AI projects and
    data activities. Returns a dict (falls back to empty dict on failure).
    """
    prompt = (
        f"対象企業: {company_name}\n\n"
        f"【企業調査情報】\n{company_info}\n\n"
        f"{_FACT_MAP_INSTRUCTIONS}{_FACT_MAP_SCHEMA}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=(
            "あなたは企業のAI活用状況を分析する専門家です。"
            "与えられた情報から、データアノテーションが必要な具体的な事業領域とAIプロジェクトを"
            "構造的に抽出・推論してください。"
        ),
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(response)
    try:
        return _parse_json(raw)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Phase 2 implementation
# ---------------------------------------------------------------------------

def _generate_deep_proposal(
    client: anthropic.Anthropic,
    company_name: str,
    raw_info: str,
    fact_map: dict,
    fastlabel_context: str,
    include_cases: bool,
    include_roi: bool,
) -> dict:
    """Use Opus with adaptive thinking to generate deep, specific proposals."""
    fl_section = (
        f"【FASTLabel社内資料（サービス詳細・事例）】\n{fastlabel_context}"
        if fastlabel_context
        else "【FASTLabel資料】資料が提供されていないため、サービス知識から提案を生成します。"
    )

    fact_map_text = (
        json.dumps(fact_map, ensure_ascii=False, indent=2)
        if fact_map
        else "（事実マップの抽出に失敗しました。企業調査情報から直接推論してください）"
    )

    roi_req = (
        "- roi_estimate: 具体的な数値（工数削減率・期間・金額換算）を含む試算"
        if include_roi else
        "- roi_estimate: 定性的な効果説明（数値試算は不要）"
    )
    case_req = (
        "- case_study: 類似業界・用途の具体的な導入事例"
        if include_cases else
        "- case_study: 空文字でよい"
    )

    user_prompt = f"""以下の情報を元に、{company_name}様向けのFASTLabel提案書を作成してください。

【企業調査情報（Web検索結果）】
{raw_info}

【AIプロジェクト事実マップ（Phase 1分析結果）】
{fact_map_text}

{fl_section}

【出力要件】
{roi_req}
{case_req}

{_PROPOSAL_INSTRUCTIONS}{_OUTPUT_SCHEMA}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=6000,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = _extract_text(response)
    return _parse_proposal_json(raw, company_name)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _extract_text(response) -> str:
    return "\n".join(
        block.text for block in response.content if block.type == "text"
    ).strip()


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        return json.loads(m.group())
    return json.loads(cleaned)


def _parse_proposal_json(raw: str, company_name: str) -> dict:
    """Try to parse JSON from raw text; return a fallback skeleton on failure."""
    try:
        return _parse_json(raw)
    except (json.JSONDecodeError, Exception):
        pass

    return {
        "target_department": "AI推進本部・データサイエンス部門",
        "target_persona": "AIプロジェクトリーダー",
        "company_overview": f"{company_name}のAI活用推進状況",
        "challenges": [
            "教師データ作成の品質・スピード・コストのバランスが取れていない",
            "AI開発サイクルがデータ準備工程でボトルネックになっている",
            "アノテーション作業の属人化・外注管理コストが増大している",
        ],
        "challenge_details": [
            {
                "title": "教師データ作成の非効率",
                "description": "手作業によるラベリングは時間・コストがかかり、品質のばらつきも大きい",
                "business_impact": "AI開発サイクルの長期化、競合他社へのスピード負け",
                "evidence": "業界一般的な課題として設定（企業固有情報の取得に失敗）",
            }
        ],
        "proposal_summary": "FASTLabelで教師データ作成を自動化・高品質化し、AI開発を加速する",
        "proposal_details": [
            {
                "service_name": "AIアシストアノテーション",
                "value": "半自動ラベリングで作業工数を最大80%削減",
                "differentiator": "国産プラットフォームによるセキュリティと日本語サポート",
                "expected_effect": "アノテーション工数50%削減・品質95%以上達成",
            }
        ],
        "roi_estimate": "月間1,000時間の工数削減、年間コスト3,000万円相当の削減効果を想定",
        "case_study": raw if raw else "",
        "next_steps": ["デモンストレーション実施（30分）", "POC設計・スコープ合意"],
    }
