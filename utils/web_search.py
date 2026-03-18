"""Web search utility: uses Claude's server-side web_search tool to research a company."""

import anthropic


def search_company_info(company_name: str, api_key: str) -> str:
    """
    Search the web for *company_name* and return a structured Japanese summary
    covering business overview, industry challenges, and AI/data usage.

    Uses Claude's built-in ``web_search_20260209`` server-side tool, which runs
    entirely on Anthropic's infrastructure — no extra API key is required.
    """
    # max_retries=5: SDK automatically retries 429/5xx with exponential backoff
    client = anthropic.Anthropic(api_key=api_key, max_retries=5)

    prompt = f"""「{company_name}」について、AIデータラベリングの提案書作成に必要な情報を収集してください。

以下の観点から情報を検索・整理してください：
1. 企業概要（事業内容・業界・従業員規模・売上規模）
2. 現在の経営課題・事業課題（公式発表・ニュース・IR情報より）
3. DX推進状況・AI活用の現状と方針
4. 機械学習・コンピュータビジョン・NLP等の取り組み
5. データ活用や自動化に関する投資・プロジェクト
6. 競合他社との差別化課題

収集した情報を日本語で詳細にまとめてください。情報が不明な場合は、業界一般的な課題を補足してください。"""

    messages = [{"role": "user", "content": prompt}]

    # Server-side web search: Claude handles the search loop internally.
    # We may receive pause_turn if the server loop hits its iteration cap;
    # in that case we re-send to let Claude continue.
    MAX_CONTINUATIONS = 5
    for _ in range(MAX_CONTINUATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-6",  # lighter than opus; sufficient for web research
            max_tokens=4000,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )

        if response.stop_reason == "pause_turn":
            # Append the assistant turn and let Claude continue
            messages.append({"role": "assistant", "content": response.content})
            continue

        # end_turn or tool_use → collect text and return
        break

    text_parts: list[str] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)

    return "\n".join(text_parts).strip()
