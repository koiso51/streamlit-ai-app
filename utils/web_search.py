"""Web search utility: uses Claude's server-side web_search tool to research a company."""

import anthropic

# Max output tokens per search call (sufficient for concise factual summaries)
_MAX_TOKENS = 2500
# Max pause_turn continuations (web search rarely needs more than 2-3 rounds)
_MAX_CONTINUATIONS = 3


def search_company_info(company_name: str, api_key: str) -> str:
    """
    Run a single targeted search for *company_name* covering both company
    overview/DX strategy and AI/ML specifics in one API call.

    The model is instructed to perform multiple web searches internally
    (overview first, then AI/ML details), keeping the same quality as the
    previous two-call approach at roughly half the API cost.
    """
    client = anthropic.Anthropic(api_key=api_key, max_retries=8)

    combined_prompt = f"""「{company_name}」について以下の2つのテーマで情報収集し、それぞれ日本語で整理してください。
必要に応じてWeb検索を複数回実施してください。

【テーマA: 企業概要・DX戦略】
1. 企業概要（主要事業・業界・売上規模・従業員数）
2. 経営課題・DX推進方針（決算説明・中期経営計画・代表コメント等）
3. AI/機械学習の活用状況と公式発表内容
4. 競合他社との差別化課題・市場環境

【テーマB: AI/MLプロジェクト詳細】
1. AI/MLエンジニア・データサイエンティストの求人票（どんなスキル・業務か）
2. 具体的なAIプロジェクト名・製品名・サービス名
3. 技術ブログ・開発者ブログの内容
4. IR資料に記載のデジタル投資・AI投資の内容
5. 利用しているデータ種別（画像・自然言語・音声・点群など）
6. データ収集・アノテーション・モデル学習に関する取り組み

各テーマを「【企業概要・DX戦略】」「【AI/MLプロジェクト詳細】」の見出しで区切って出力してください。"""

    return _run_search(client, combined_prompt)


def _run_search(client: anthropic.Anthropic, prompt: str) -> str:
    """Execute a web-search request (with continuations) and return extracted text."""
    messages = [{"role": "user", "content": prompt}]

    for _ in range(_MAX_CONTINUATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=_MAX_TOKENS,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        break

    text_parts: list[str] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)

    return "\n".join(text_parts).strip()
