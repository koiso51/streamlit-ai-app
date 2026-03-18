"""Proposal generator: uses Claude to create a structured proposal JSON."""

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
- 多様なデータ形式への対応（業界最多水準）

【提案書作成の原則】
1. 課題仮説は「そのクライアントにとって本当に重要な経営課題・事業課題」であること（表面的な課題ではなく深層の課題）
2. 提案内容は課題を「深いレベルで解決」できること（単なる機能説明ではなく課題解決ストーリー）
3. FASTLabelならではの差別化要素を明確にすること
4. 想定部門を具体的に特定し、そのステークホルダーの言語で語ること"""

# ---------------------------------------------------------------------------
# Output schema description (few-shot style JSON)
# ---------------------------------------------------------------------------

_OUTPUT_SCHEMA = """{
  "target_department": "想定部門・職種（例: AI推進本部、データサイエンスグループ、研究開発部門 など具体的に）",
  "target_persona": "キーパーソンの役職・ミッション（例: AIプロジェクトリーダー、CDO直下の推進担当など）",
  "company_overview": "企業・業界のAI活用状況サマリー（2-3文）",
  "challenges": [
    "課題仮説1：深層の経営課題レベルで記述",
    "課題仮説2：データ/AI開発プロセスの課題",
    "課題仮説3：スピード・品質・コストのトレードオフ課題"
  ],
  "challenge_details": [
    {
      "title": "課題タイトル（短く）",
      "description": "課題の詳細（なぜ重要か、現状どうなっているか）",
      "business_impact": "放置した場合のビジネスインパクト"
    }
  ],
  "proposal_summary": "提案の一言サマリー（エレベーターピッチ）",
  "proposal_details": [
    {
      "service_name": "FASTLabelの提供サービス/機能名",
      "value": "提供価値（課題との接続を明確に）",
      "differentiator": "FASTLabelならではの差別化理由",
      "expected_effect": "期待効果（できれば数値）"
    }
  ],
  "roi_estimate": "ROI・期待効果の試算（工数削減率、期間、金額換算など具体的に）",
  "case_study": "類似業界・用途の導入事例サマリー（なければ空文字）",
  "next_steps": [
    "次のアクション1（具体的）",
    "次のアクション2"
  ]
}"""


def generate_proposal(
    company_name: str,
    company_info: str,
    fastlabel_context: str,
    api_key: str,
    include_cases: bool = True,
    include_roi: bool = True,
) -> dict:
    """
    Call Claude to generate a structured proposal for *company_name*.

    Returns a dict matching the schema in _OUTPUT_SCHEMA.
    Falls back to a skeleton dict if JSON parsing fails.
    """
    # max_retries=5: SDK automatically retries 429/5xx with exponential backoff
    client = anthropic.Anthropic(api_key=api_key, max_retries=5)

    # Build FASTLabel context section
    fl_section = (
        f"【FASTLabel社内資料（サービス詳細・事例）】\n{fastlabel_context}"
        if fastlabel_context
        else "【FASTLabel資料】資料が提供されていないため、サービス知識から提案を生成します。"
    )

    # Conditional sections
    roi_instruction = (
        "- roi_estimate: 具体的な数値（工数削減率・期間・金額換算）を含む試算"
        if include_roi
        else "- roi_estimate: 定性的な効果説明（数値試算は不要）"
    )
    case_instruction = (
        "- case_study: 類似業界・用途の具体的な導入事例"
        if include_cases
        else "- case_study: 空文字でよい"
    )

    user_prompt = f"""以下の情報を元に、{company_name}様向けのFASTLabel提案書コンテンツを作成してください。

【クライアント企業調査情報】
{company_info if company_info else f"企業名: {company_name}（検索情報なし。業界知識から推定してください）"}

{fl_section}

【出力要件】
{roi_instruction}
{case_instruction}

以下のJSON形式のみで出力してください（マークダウンコードブロック不要）：
{_OUTPUT_SCHEMA}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=5000,
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
    # Strip markdown fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    # Find the first { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Last resort: try to parse the whole string
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback skeleton so the app never crashes
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
