"""PowerPoint creator: builds an executive-ready generative-AI proposal deck."""

import datetime
from io import BytesIO

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

# ---------------------------------------------------------------------------
# Brand colors
# ---------------------------------------------------------------------------
_NAVY = RGBColor(0x0F, 0x2B, 0x5C)
_BLUE = RGBColor(0x1D, 0x6F, 0xD8)
_CYAN = RGBColor(0x00, 0xB8, 0xD4)
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_LIGHT_GRAY = RGBColor(0xF4, 0xF6, 0xF9)
_DARK_GRAY = RGBColor(0x1F, 0x29, 0x37)
_MID_GRAY = RGBColor(0x6B, 0x74, 0x80)
_ORANGE = RGBColor(0xF5, 0x7C, 0x00)

# Slide dimensions (widescreen 13.33 × 7.5 in)
_W = Inches(13.33)
_H = Inches(7.5)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def create_proposal_pptx(
    proposal: dict,
    company_name: str,
    firm_name: str = "",
    sources: list[str] | None = None,
) -> bytes:
    """Return the PPTX file as bytes."""
    prs = Presentation()
    prs.slide_width = _W
    prs.slide_height = _H

    today = datetime.date.today().strftime("%Y年%m月%d日")

    _slide_title(prs, company_name, firm_name, today)
    _slide_agenda(prs, firm_name)
    _slide_company_overview(prs, company_name, proposal, firm_name)
    _slide_business_segments(prs, proposal, firm_name)
    _slide_challenges(prs, company_name, proposal, firm_name)
    _slide_challenge_details(prs, proposal, firm_name)
    _slide_ai_landscape(prs, company_name, proposal, firm_name)
    _slide_approaches(prs, proposal, firm_name)
    _slide_approach_details(prs, proposal, firm_name)
    _slide_roadmap(prs, proposal, firm_name)
    if proposal.get("roi_estimate"):
        _slide_roi(prs, proposal, firm_name)
    if proposal.get("case_study"):
        _slide_case_study(prs, proposal, firm_name)
    if proposal.get("anticipated_qa"):
        _slide_qa(prs, proposal, firm_name)
    _slide_next_steps(prs, company_name, proposal, firm_name, today)
    if sources:
        _slide_sources(prs, sources, firm_name)

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def _slide_title(prs: Presentation, company_name: str, firm_name: str, today: str) -> None:
    slide = _blank_slide(prs)

    _fill_rect(slide, 0, 0, _W, _H, _NAVY)
    _fill_rect(slide, 0, 0, Inches(0.12), _H, _CYAN)

    if firm_name:
        _add_text(
            slide, firm_name,
            Inches(9.0), Inches(0.3), Inches(4.0), Inches(0.5),
            font_size=16, bold=True, color=_CYAN, align=PP_ALIGN.RIGHT,
        )

    _add_text(
        slide,
        f"{company_name} 様",
        Inches(0.7), Inches(1.8), Inches(12), Inches(0.9),
        font_size=28, bold=False, color=RGBColor(0xB0, 0xC4, 0xDE),
    )
    _add_text(
        slide,
        "生成AI活用\nご提案書",
        Inches(0.7), Inches(2.6), Inches(12), Inches(2.0),
        font_size=44, bold=True, color=_WHITE,
    )

    _fill_rect(slide, Inches(0.7), Inches(4.7), Inches(5), Inches(0.04), _CYAN)

    subtitle = f"{firm_name}　　{today}" if firm_name else today
    _add_text(
        slide, subtitle,
        Inches(0.7), Inches(4.9), Inches(10), Inches(0.5),
        font_size=14, color=RGBColor(0xB0, 0xC4, 0xDE),
    )
    _add_text(
        slide, "Confidential — 社外秘",
        Inches(0.7), Inches(5.5), Inches(10), Inches(0.4),
        font_size=11, color=_MID_GRAY,
    )


def _slide_agenda(prs: Presentation, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "本日のアジェンダ", firm_name)

    items = [
        ("01", "企業概要・主要事業の整理"),
        ("02", "主要事業における課題仮説"),
        ("03", "生成AI活用アプローチ案"),
        ("04", "導入・計画の進め方"),
        ("05", "想定投資規模・ROI"),
        ("06", "想定される論点・Q&A"),
        ("07", "次のステップ"),
    ]

    cols = 2
    col_w = Inches(5.8)
    col_gap = Inches(0.6)
    start_x = Inches(0.8)
    start_y = Inches(1.7)
    row_h = Inches(0.85)

    for i, (num, label) in enumerate(items):
        row, col = divmod(i, cols)
        x = start_x + col * (col_w + col_gap)
        y = start_y + row * row_h

        _fill_rect(slide, x, y, Inches(0.55), Inches(0.6), _BLUE)
        _add_text(slide, num, x, y, Inches(0.55), Inches(0.6),
                  font_size=13, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        _add_text(slide, label, x + Inches(0.65), y, col_w - Inches(0.7), Inches(0.6),
                  font_size=14, color=_DARK_GRAY)


def _slide_company_overview(prs: Presentation, company_name: str, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, f"{company_name} 様　企業概要", firm_name)

    overview: dict = proposal.get("company_overview", {}) or {}
    summary = overview.get("summary", "")

    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(12.3), Inches(1.7), _LIGHT_GRAY)
    _add_text(slide, "■ 企業概要サマリー",
              Inches(0.7), Inches(1.65), Inches(12), Inches(0.4),
              font_size=12, bold=True, color=_BLUE)
    _add_text(slide, summary,
              Inches(0.7), Inches(2.05), Inches(12), Inches(1.1),
              font_size=13, color=_DARK_GRAY)

    cards = [
        ("事業ドメイン", overview.get("business_domain", "")),
        ("規模感", overview.get("scale", "")),
    ]
    for idx, (label, value) in enumerate(cards):
        x = Inches(0.5) + idx * Inches(6.2)
        _fill_rect(slide, x, Inches(3.5), Inches(6.0), Inches(1.1), _LIGHT_GRAY)
        _fill_rect(slide, x, Inches(3.5), Inches(6.0), Inches(0.3), _NAVY)
        _add_text(slide, label, x, Inches(3.5), Inches(6.0), Inches(0.3),
                  font_size=10, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        _add_text(slide, value, x + Inches(0.15), Inches(3.85),
                  Inches(5.7), Inches(0.7),
                  font_size=12, color=_DARK_GRAY)

    _add_text(slide, "■ 直近のトピック",
              Inches(0.5), Inches(4.85), Inches(12), Inches(0.4),
              font_size=12, bold=True, color=_BLUE)
    _fill_rect(slide, Inches(0.5), Inches(5.25), Inches(12.3), Inches(1.5), _LIGHT_GRAY)
    _fill_rect(slide, Inches(0.5), Inches(5.25), Inches(0.08), Inches(1.5), _CYAN)
    _add_text(slide, overview.get("recent_topics", ""),
              Inches(0.8), Inches(5.35), Inches(11.8), Inches(1.3),
              font_size=12, color=_DARK_GRAY)


def _slide_business_segments(prs: Presentation, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "主要事業", firm_name)

    segments: list[dict] = proposal.get("business_segments", [])
    if not segments:
        return

    row_h = Inches(1.55) if len(segments) <= 3 else Inches(1.1)
    start_y = Inches(1.6)

    for i, seg in enumerate(segments[:4]):
        y = start_y + i * row_h
        _fill_rect(slide, Inches(0.4), y + Inches(0.1),
                   Inches(0.06), row_h - Inches(0.25), _BLUE)
        _add_text(slide, seg.get("name", ""),
                  Inches(0.6), y, Inches(3.2), Inches(0.5),
                  font_size=15, bold=True, color=_NAVY)
        _add_text(slide, seg.get("description", ""),
                  Inches(3.9), y, Inches(8.9), row_h - Inches(0.2),
                  font_size=13, color=_DARK_GRAY)
        _fill_rect(slide, Inches(0.4), y + row_h - Inches(0.1),
                   Inches(12.5), Inches(0.01), RGBColor(0xD0, 0xD7, 0xE3))


def _slide_challenges(prs: Presentation, company_name: str, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, f"{company_name} 様　主要事業における課題仮説", firm_name)

    challenges: list[dict] = proposal.get("challenges", [])

    _add_text(slide, "収集した事実をもとに、以下の課題仮説を前提としてご提案します",
              Inches(0.5), Inches(1.55), Inches(12.3), Inches(0.35),
              font_size=12, color=_MID_GRAY)

    card_w = Inches(3.8)
    card_h = Inches(3.9)
    gap = Inches(0.35)
    start_x = Inches(0.45)
    start_y = Inches(1.95)

    for i, c in enumerate(challenges[:3]):
        x = start_x + i * (card_w + gap)
        _fill_rect(slide, x, start_y, card_w, card_h, _LIGHT_GRAY)
        _fill_rect(slide, x, start_y, card_w, Inches(0.06), _BLUE)
        _fill_rect(slide, x + Inches(0.2), start_y + Inches(0.2),
                   Inches(0.55), Inches(0.55), _NAVY)
        _add_text(slide, f"0{i+1}", x + Inches(0.2), start_y + Inches(0.2),
                  Inches(0.55), Inches(0.55),
                  font_size=14, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)

        segment = c.get("segment", "")
        if segment:
            _add_text(slide, segment, x + Inches(0.85), start_y + Inches(0.3),
                      card_w - Inches(1.0), Inches(0.35),
                      font_size=10, color=_BLUE)

        _add_text(slide, c.get("title", ""),
                  x + Inches(0.2), start_y + Inches(0.9),
                  card_w - Inches(0.4), Inches(0.6),
                  font_size=14, bold=True, color=_NAVY)
        _add_text(slide, c.get("description", ""),
                  x + Inches(0.2), start_y + Inches(1.55),
                  card_w - Inches(0.4), card_h - Inches(1.75),
                  font_size=11, color=_DARK_GRAY)


def _slide_challenge_details(prs: Presentation, proposal: dict, firm_name: str) -> None:
    challenges: list[dict] = proposal.get("challenges", [])
    if not challenges:
        return

    slide = _blank_slide(prs)
    _slide_header(slide, "課題仮説　根拠と影響", firm_name)

    row_h = Inches(1.65)
    start_y = Inches(1.55)

    for i, c in enumerate(challenges[:3]):
        y = start_y + i * row_h
        _fill_rect(slide, Inches(0.4), y + Inches(0.15),
                   Inches(0.06), Inches(1.35), _CYAN)
        _add_text(slide, c.get("title", ""),
                  Inches(0.6), y + Inches(0.1),
                  Inches(12), Inches(0.4),
                  font_size=13, bold=True, color=_NAVY)
        _add_text(slide, f"根拠: {c.get('evidence', '')}",
                  Inches(0.6), y + Inches(0.5),
                  Inches(8.5), Inches(0.7),
                  font_size=11, color=_DARK_GRAY)

        impact = c.get("business_impact", "")
        if impact:
            _fill_rect(slide, Inches(9.3), y + Inches(0.4),
                       Inches(3.6), Inches(0.9), RGBColor(0xFF, 0xF3, 0xE0))
            _fill_rect(slide, Inches(9.3), y + Inches(0.4),
                       Inches(1.1), Inches(0.9), _ORANGE)
            _add_text(slide, "影響", Inches(9.3), y + Inches(0.4),
                      Inches(1.1), Inches(0.9),
                      font_size=10, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
            _add_text(slide, impact,
                      Inches(10.5), y + Inches(0.4),
                      Inches(2.3), Inches(0.9),
                      font_size=10, color=_DARK_GRAY)

        _fill_rect(slide, Inches(0.4), y + row_h - Inches(0.05),
                   Inches(12.5), Inches(0.01), RGBColor(0xD0, 0xD7, 0xE3))


def _slide_ai_landscape(prs: Presentation, company_name: str, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "生成AI活用の全体観", firm_name)

    text = proposal.get("ai_landscape_summary", "")

    _fill_rect(slide, Inches(0.5), Inches(2.2), Inches(12.3), Inches(2.5), _NAVY)
    _fill_rect(slide, Inches(0.5), Inches(2.2), Inches(0.1), Inches(2.5), _CYAN)
    _add_text(slide, f"なぜ『今』『{company_name}様』にとって有効か",
              Inches(0.8), Inches(2.35), Inches(11.8), Inches(0.4),
              font_size=13, color=_CYAN)
    _add_text(slide, text,
              Inches(0.8), Inches(2.85), Inches(11.8), Inches(1.7),
              font_size=15, color=_WHITE)


def _slide_approaches(prs: Presentation, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "生成AI活用アプローチ案", firm_name)

    approaches: list[dict] = proposal.get("approaches", [])

    card_w = Inches(3.8)
    card_h = Inches(4.3)
    gap = Inches(0.35)
    start_x = Inches(0.45)
    start_y = Inches(1.65)

    for i, a in enumerate(approaches[:3]):
        x = start_x + i * (card_w + gap)
        _fill_rect(slide, x, start_y, card_w, card_h, _LIGHT_GRAY)
        _fill_rect(slide, x, start_y, card_w, Inches(0.55), _BLUE)
        _add_text(slide, a.get("title", ""), x, start_y, card_w, Inches(0.55),
                  font_size=13, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)

        related = a.get("related_challenge", "")
        if related:
            _add_text(slide, f"対応する課題: {related}",
                      x + Inches(0.2), start_y + Inches(0.65),
                      card_w - Inches(0.4), Inches(0.5),
                      font_size=10, color=_MID_GRAY)

        _add_text(slide, a.get("description", ""),
                  x + Inches(0.2), start_y + Inches(1.2),
                  card_w - Inches(0.4), Inches(3.0),
                  font_size=12, color=_DARK_GRAY)


def _slide_approach_details(prs: Presentation, proposal: dict, firm_name: str) -> None:
    approaches: list[dict] = proposal.get("approaches", [])
    if not approaches:
        return

    slide = _blank_slide(prs)
    _slide_header(slide, "アプローチ詳細　支援内容・期待効果", firm_name)

    col_headers = ["アプローチ", "支援内容", "期待効果"]
    col_ws = [Inches(3.2), Inches(5.3), Inches(3.4)]
    col_xs = [Inches(0.3)]
    for w in col_ws[:-1]:
        col_xs.append(col_xs[-1] + w + Inches(0.1))

    header_y = Inches(1.5)
    for label, w, x in zip(col_headers, col_ws, col_xs):
        _fill_rect(slide, x, header_y, w, Inches(0.45), _NAVY)
        _add_text(slide, label, x, header_y, w, Inches(0.45),
                  font_size=10, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)

    row_h = Inches(1.65)
    start_y = header_y + Inches(0.45)
    for i, a in enumerate(approaches[:3]):
        y = start_y + i * row_h
        bg = _LIGHT_GRAY if i % 2 == 0 else _WHITE
        for j, (key, w, x) in enumerate(
            zip(["title", "consulting_support", "expected_effect"], col_ws, col_xs)
        ):
            _fill_rect(slide, x, y, w, row_h - Inches(0.05), bg)
            if j == 0:
                _fill_rect(slide, x, y, Inches(0.05), row_h - Inches(0.05), _CYAN)
            _add_text(slide, a.get(key, ""),
                      x + Inches(0.1), y + Inches(0.1),
                      w - Inches(0.15), row_h - Inches(0.2),
                      font_size=11, color=_DARK_GRAY)


def _slide_roadmap(prs: Presentation, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "導入・計画の進め方", firm_name)

    phases: list[dict] = proposal.get("roadmap_phases", [])
    if not phases:
        return

    n = min(len(phases), 4)
    col_w = Inches(12.3) / n if n else Inches(12.3)
    gap = Inches(0.2)
    usable_w = (Inches(12.3) - gap * (n - 1)) / n if n > 1 else Inches(12.3)
    start_x = Inches(0.5)
    y = Inches(1.7)
    card_h = Inches(4.6)

    for i, p in enumerate(phases[:4]):
        x = start_x + i * (usable_w + gap)
        _fill_rect(slide, x, y, usable_w, card_h, _LIGHT_GRAY)
        _fill_rect(slide, x, y, usable_w, Inches(0.55), _NAVY)
        _add_text(slide, p.get("phase", ""), x + Inches(0.1), y, usable_w - Inches(0.2), Inches(0.55),
                  font_size=12, bold=True, color=_WHITE)
        _add_text(slide, p.get("duration", ""), x + Inches(0.15), y + Inches(0.65),
                  usable_w - Inches(0.3), Inches(0.35),
                  font_size=10, bold=True, color=_BLUE)
        _add_text(slide, p.get("description", ""), x + Inches(0.15), y + Inches(1.05),
                  usable_w - Inches(0.3), Inches(2.0),
                  font_size=11, color=_DARK_GRAY)
        _fill_rect(slide, x + Inches(0.15), y + Inches(3.15),
                   usable_w - Inches(0.3), Inches(0.01), RGBColor(0xD0, 0xD7, 0xE3))
        _add_text(slide, "成果物", x + Inches(0.15), y + Inches(3.3),
                  usable_w - Inches(0.3), Inches(0.3),
                  font_size=10, bold=True, color=_BLUE)
        _add_text(slide, p.get("deliverables", ""), x + Inches(0.15), y + Inches(3.65),
                  usable_w - Inches(0.3), Inches(0.9),
                  font_size=10, color=_DARK_GRAY)

        if i < n - 1:
            _add_text(slide, "→", x + usable_w - Inches(0.05), y + Inches(2.0),
                      gap + Inches(0.3), Inches(0.5),
                      font_size=18, bold=True, color=_CYAN, align=PP_ALIGN.CENTER)


def _slide_roi(prs: Presentation, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "想定投資規模・ROI試算", firm_name)

    roi_text = proposal.get("roi_estimate", "")

    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(12.3), Inches(2.5), _NAVY)
    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(0.1), Inches(2.5), _CYAN)
    _add_text(slide, "ROI・期待効果",
              Inches(0.8), Inches(1.65), Inches(12), Inches(0.35),
              font_size=11, color=_CYAN)
    _add_text(slide, roi_text,
              Inches(0.8), Inches(2.05), Inches(11.8), Inches(1.8),
              font_size=14, color=_WHITE)

    _add_text(slide, "※ 上記は概算値です。詳細はヒアリング後にカスタマイズいたします。",
              Inches(0.5), Inches(4.2), Inches(12.3), Inches(0.4),
              font_size=10, color=_MID_GRAY)


def _slide_case_study(prs: Presentation, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "類似支援実績", firm_name)

    case = proposal.get("case_study", "")

    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(12.3), Inches(4.5), _LIGHT_GRAY)
    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(0.1), Inches(4.5), _BLUE)
    _add_text(slide, case,
              Inches(0.8), Inches(1.7), Inches(11.8), Inches(4.2),
              font_size=13, color=_DARK_GRAY)


def _slide_qa(prs: Presentation, proposal: dict, firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "想定される論点・Q&A", firm_name)

    qa_list: list[dict] = proposal.get("anticipated_qa", [])
    row_h = Inches(1.3)
    start_y = Inches(1.55)

    for i, qa in enumerate(qa_list[:4]):
        y = start_y + i * row_h
        _fill_rect(slide, Inches(0.4), y, Inches(0.6), Inches(0.6), _NAVY)
        _add_text(slide, "Q", Inches(0.4), y, Inches(0.6), Inches(0.6),
                  font_size=16, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        _add_text(slide, qa.get("question", ""),
                  Inches(1.15), y, Inches(11.6), Inches(0.5),
                  font_size=12, bold=True, color=_NAVY)

        _fill_rect(slide, Inches(0.4), y + Inches(0.55), Inches(0.6), Inches(0.6), _CYAN)
        _add_text(slide, "A", Inches(0.4), y + Inches(0.55), Inches(0.6), Inches(0.6),
                  font_size=16, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        _add_text(slide, qa.get("answer", ""),
                  Inches(1.15), y + Inches(0.55), Inches(11.6), Inches(0.65),
                  font_size=11, color=_DARK_GRAY)


def _slide_next_steps(
    prs: Presentation, company_name: str, proposal: dict, firm_name: str, today: str
) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "次のステップ", firm_name)

    steps: list[str] = proposal.get("next_steps", [])

    for i, step in enumerate(steps[:4]):
        y = Inches(1.6) + i * Inches(1.1)
        _fill_rect(slide, Inches(0.5), y, Inches(0.7), Inches(0.7), _NAVY)
        _add_text(slide, str(i + 1), Inches(0.5), y, Inches(0.7), Inches(0.7),
                  font_size=20, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        _fill_rect(slide, Inches(1.3), y, Inches(11.5), Inches(0.7), _LIGHT_GRAY)
        _add_text(slide, step, Inches(1.5), y, Inches(11.1), Inches(0.7),
                  font_size=14, color=_DARK_GRAY)

    _fill_rect(slide, 0, _H - Inches(0.8), _W, Inches(0.8), _NAVY)
    footer = f"{firm_name}　　" if firm_name else ""
    _add_text(
        slide,
        f"{footer}{company_name} 様向け提案書　　{today}",
        Inches(0.5), _H - Inches(0.7), Inches(12.3), Inches(0.6),
        font_size=10, color=_WHITE,
    )


def _slide_sources(prs: Presentation, sources: list[str], firm_name: str) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "Appendix：リサーチ根拠・出典", firm_name)

    _add_text(slide, "本提案書は、以下の情報源を調査した上で作成しています。",
              Inches(0.5), Inches(1.55), Inches(12.3), Inches(0.4),
              font_size=12, color=_MID_GRAY)

    y = Inches(2.1)
    for src in sources[:10]:
        _add_text(slide, f"・{src}", Inches(0.7), y, Inches(11.9), Inches(0.4),
                  font_size=11, color=_DARK_GRAY)
        y += Inches(0.42)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _blank_slide(prs: Presentation):
    layout = prs.slide_layouts[6]  # blank
    return prs.slides.add_slide(layout)


def _slide_header(slide, title: str, firm_name: str = "") -> None:
    """Add a consistent header bar with title to a content slide."""
    _fill_rect(slide, 0, 0, _W, Inches(1.3), _NAVY)
    _fill_rect(slide, 0, Inches(1.3), _W, Inches(0.05), _CYAN)
    if firm_name:
        _add_text(slide, firm_name, Inches(9.0), Inches(0.05),
                  Inches(4.0), Inches(0.45),
                  font_size=13, bold=True, color=_CYAN, align=PP_ALIGN.RIGHT)
    _add_text(slide, title, Inches(0.45), Inches(0.25),
              Inches(9.5), Inches(0.8),
              font_size=22, bold=True, color=_WHITE)


def _fill_rect(slide, left: Emu, top: Emu, width: Emu, height: Emu,
               color: RGBColor) -> None:
    """Add a solid-filled rectangle shape."""
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height,
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _add_text(
    slide,
    text: str,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
    *,
    font_size: int = 12,
    bold: bool = False,
    color: RGBColor = _DARK_GRAY,
    align: PP_ALIGN = PP_ALIGN.LEFT,
) -> None:
    """Add a text box with consistent styling."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    txBox.line.fill.background()
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, line in enumerate(text.split("\n")):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.alignment = align
        run = p.runs[0] if p.runs else p.add_run()
        run.text = line
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = "Hiragino Sans" if bold else "Hiragino Kaku Gothic ProN"
        if not run.font.name:
            run.font.name = "MS PGothic"
