"""Proposal generator: uses Claude to create a structured proposal JSON.

The proposal targets a prospective client's *executives* and is built to
withstand a first-meeting discussion: challenge hypotheses must be grounded
in facts gathered about that specific company (not generic boilerplate),
and generative-AI approaches must map 1:1 onto those challenges.
"""

import json
import re

import anthropic

# ---------------------------------------------------------------------------
# System prompt — generic generative-AI strategy consultant persona
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """あなたは経営コンサルティングファームに所属する、生成AI活用戦略を専門とするシニアコンサルタントです。

【あなたの立場】
特定の自社製品・SaaSを売り込むのではなく、クライアント企業の事業内容・経営課題を深く理解した上で、その企業に最適な生成AI活用のアプローチと導入計画を設計し、コンサルティングとして伴走支援することを提案します。

【提案書作成の原則】
1. 「事実 → 示唆 → 提案」の順で思考すること。まず収集した事実（企業サイト・ニュース・IR情報など）を根拠として押さえ、そこから論理的に導かれる示唆（課題仮説）を立て、最後にその課題に対応する生成AI活用アプローチを提案する、という一貫したロジックを崩さないこと。
2. 課題仮説は一般論ではなく、収集した事実に基づく、その企業・事業セグメント固有のものであること。「業務効率化」「DX推進」のような抽象的な言葉だけで終わらせず、具体的な業務プロセス名・部門名・想定指標まで踏み込むこと。
3. 各課題仮説には、根拠となった具体的な事実（evidence）を明記すること。事実が乏しい場合でも、業界動向等の合理的な推測であることが分かる書き方にする。
4. 提案する生成AIアプローチは、課題仮説と1対1で明確に対応させ、かつコンサルティングファームとして実際に提供可能な支援内容（現状診断、PoC設計・伴走、内製化支援、人材育成など）と結び付けること。
5. 経営者が読んだときに「自社のことを事前に深く調べている」と感じられるよう、固有名詞（事業拠点・製品名・サービス名・直近のニュースなど）を積極的に本文に盛り込むこと。
6. 出力は一般的な生成AI活用資料ではなく、初回の経営会議・役員ディスカッションで通用する品質であること。想定される反論・質問（コスト、セキュリティ、既存業務への影響など）にも備えること。"""

# ---------------------------------------------------------------------------
# Output schema description (few-shot style JSON)
# ---------------------------------------------------------------------------

_OUTPUT_SCHEMA = """{
  "company_overview": {
    "summary": "企業概要のサマリー（2-3文、事実ベース）",
    "business_domain": "事業ドメイン・業界",
    "scale": "分かる範囲での規模感（従業員数・売上規模・拠点数など）",
    "recent_topics": "直近のニュース・IR・注力テーマなど（固有名詞を含める）"
  },
  "business_segments": [
    {
      "name": "事業セグメント名",
      "description": "その事業の概要（1-2文）"
    }
  ],
  "challenges": [
    {
      "segment": "対応する事業セグメント名（business_segmentsのnameと一致させる）",
      "title": "課題タイトル（短く）",
      "description": "課題の詳細。なぜ重要か、現状どうなっているか。抽象論ではなく具体的な業務・部門に踏み込むこと",
      "evidence": "根拠となった収集事実（サイト記載内容・ニュース等、具体的に）",
      "business_impact": "放置した場合のビジネスインパクト"
    }
  ],
  "ai_landscape_summary": "なぜ『今』『この企業』にとって生成AI活用が有効かの説明（2-3文）",
  "approaches": [
    {
      "related_challenge": "対応するchallenges[].titleと一致させる",
      "title": "生成AI活用アプローチ名",
      "description": "具体的な取り組み内容・提供価値",
      "consulting_support": "コンサルティングとして提供する支援内容（現状診断/PoC設計・伴走/内製化支援/人材育成など）",
      "expected_effect": "期待効果（可能なら定量的に）"
    }
  ],
  "roadmap_phases": [
    {
      "phase": "フェーズ名（例: Phase1 現状診断・課題特定）",
      "duration": "想定期間（例: 1〜1.5ヶ月）",
      "description": "このフェーズで行うこと",
      "deliverables": "このフェーズの成果物・アウトプット"
    }
  ],
  "roi_estimate": "投資規模感・ROI試算（工数削減率、期間、金額換算など具体的に）",
  "case_study": "自社の類似支援実績サマリー（資料が提供されていれば具体的に、なければ空文字）",
  "anticipated_qa": [
    {
      "question": "初回議論で経営者から出そうな質問（コスト・セキュリティ・既存業務への影響など）",
      "answer": "回答の想定"
    }
  ],
  "next_steps": [
    "次のアクション1（具体的）",
    "次のアクション2"
  ],
  "target_persona_notes": "経営者との議論で意識すべきポイント（関心領域・懸念点など、1-2文）"
}"""


def generate_proposal(
    company_name: str,
    research_site_text: str,
    research_web_summary: str,
    reference_context: str,
    api_key: str,
    firm_name: str = "",
    include_roi: bool = True,
    include_case_study: bool = True,
) -> dict:
    """
    Call Claude to generate a structured, company-specific proposal for
    *company_name*, grounded in the research gathered from their website
    (*research_site_text*) and supplementary web search (*research_web_summary*).

    Returns a dict matching the schema in _OUTPUT_SCHEMA.
    Falls back to a skeleton dict if JSON parsing fails.
    """
    client = anthropic.Anthropic(api_key=api_key)

    reference_section = (
        f"【自社の支援実績・サービス資料】\n{reference_context}"
        if reference_context
        else "【自社の支援実績・サービス資料】資料が提供されていないため、一般的なコンサルティング支援の知見から提案を生成します。"
    )

    roi_instruction = (
        "- roi_estimate: 具体的な数値（工数削減率・期間・金額換算）を含む試算"
        if include_roi
        else "- roi_estimate: 定性的な効果説明（数値試算は不要）"
    )
    case_instruction = (
        "- case_study: 自社資料に類似実績があれば具体的に、なければ業界一般的な成功パターンを簡潔に"
        if include_case_study
        else "- case_study: 空文字でよい"
    )

    firm_label = firm_name.strip() or "当コンサルティングファーム"

    user_prompt = f"""以下の情報を元に、{company_name}様（経営者向け）の生成AI活用ご提案書コンテンツを作成してください。提案主体は「{firm_label}」です。

【クライアント企業サイトからの収集情報】
{research_site_text if research_site_text else "（サイトからの情報取得なし）"}

【Web検索による補足情報（業界動向・ニュース等）】
{research_web_summary if research_web_summary else "（補足情報なし。業界一般知識から補ってください）"}

{reference_section}

【出力要件】
{roi_instruction}
{case_instruction}
- challenges と approaches は必ず related_challenge / title の対応関係が一致すること
- anticipated_qa は3〜4件、経営者目線で厳しめの質問を想定すること

以下のJSON形式のみで出力してください（マークダウンコードブロック不要）：
{_OUTPUT_SCHEMA}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=6000,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract text content (skip thinking blocks)
    text_parts: list[str] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)

    raw = "\n".join(text_parts).strip()

    return _parse_proposal_json(raw, company_name)


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

def _parse_proposal_json(raw: str, company_name: str) -> dict:
    """Try to extract a JSON object from *raw*, returning a fallback on failure."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback skeleton so the app never crashes
    return {
        "company_overview": {
            "summary": f"{company_name}の事業概要（自動収集情報からの生成に失敗したため簡易表示です）",
            "business_domain": "—",
            "scale": "—",
            "recent_topics": "—",
        },
        "business_segments": [
            {"name": "主要事業", "description": "収集情報から詳細を特定できませんでした"}
        ],
        "challenges": [
            {
                "segment": "主要事業",
                "title": "情報収集の再実行が必要です",
                "description": "AIからの応答をJSONとして解析できませんでした。もう一度生成をお試しください。",
                "evidence": raw[:500] if raw else "",
                "business_impact": "—",
            }
        ],
        "ai_landscape_summary": "—",
        "approaches": [
            {
                "related_challenge": "情報収集の再実行が必要です",
                "title": "—",
                "description": "—",
                "consulting_support": "—",
                "expected_effect": "—",
            }
        ],
        "roadmap_phases": [
            {
                "phase": "Phase1 現状診断",
                "duration": "1ヶ月程度",
                "description": "詳細ヒアリングと課題整理",
                "deliverables": "現状診断レポート",
            }
        ],
        "roi_estimate": "—",
        "case_study": "",
        "anticipated_qa": [],
        "next_steps": ["再生成を実行", "詳細ヒアリングの日程調整"],
        "target_persona_notes": "—",
    }
