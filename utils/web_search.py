"""Web search utility: uses Claude's server-side web_search tool to research a company."""

import anthropic


def search_company_info(company_name: str, api_key: str) -> str:
    """
    Run two targeted searches for *company_name* and return a combined summary:
    1. General overview (business, industry, DX strategy)
    2. AI/ML-specific details (projects, job postings, tech blog, IR statements)

    The two-query approach surfaces concrete AI project names and department
    names that are essential for generating specific challenge hypotheses.
    """
    # max_retries=8: SDK automatically retries 429/529/5xx with exponential backoff
    client = anthropic.Anthropic(api_key=api_key, max_retries=8)

    results: list[str] = []

    # -----------------------------------------------------------------------
    # Query 1: General company overview & DX strategy
    # -----------------------------------------------------------------------
    q1_prompt = f"""「{company_name}」について以下の観点で情報を収集し、日本語で詳しくまとめてください。

1. 企業概要（主要事業・業界・売上規模・従業員数）
2. 経営課題・DX推進方針（決算説明・中期経営計画・代表コメント等）
3. AI/機械学習の活用状況と公式発表内容
4. 競合他社との差別化課題・市場環境"""

    results.append(_run_search(client, q1_prompt, label="【企業概要・DX戦略】"))

    # -----------------------------------------------------------------------
    # Query 2: AI/ML specifics — job postings, tech blog, IR, projects
    # -----------------------------------------------------------------------
    q2_prompt = f"""「{company_name}」のAI・機械学習・データ活用に関する具体的な情報を収集してください。

以下を重点的に調べてください：
1. AI/MLエンジニア・データサイエンティストの求人票（どんなスキル・業務か）
2. 具体的なAIプロジェクト名・製品名・サービス名
3. 技術ブログ・開発者ブログの内容
4. IR資料・統合報告書に記載のデジタル投資・AI投資の内容
5. 画像認識・自然言語処理・音声・点群など利用しているデータ種別
6. データ収集・アノテーション・モデル学習に関する取り組み

収集した情報を具体的な事実として整理してください。"""

    results.append(_run_search(client, q2_prompt, label="【AI/MLプロジェクト詳細】"))

    return "\n\n".join(r for r in results if r)


def _run_search(client: anthropic.Anthropic, prompt: str, label: str) -> str:
    """Execute a single web-search request and return extracted text."""
    messages = [{"role": "user", "content": prompt}]
    MAX_CONTINUATIONS = 5

    for _ in range(MAX_CONTINUATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-6",  # lighter than opus; sufficient for web research
            max_tokens=4000,
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

    body = "\n".join(text_parts).strip()
    return f"{label}\n{body}" if body else ""
