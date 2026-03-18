"""PowerPoint creator: builds a professional FASTLabel proposal deck."""

import datetime
from io import BytesIO

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

# ---------------------------------------------------------------------------
# Brand colors
# ---------------------------------------------------------------------------
_NAVY = RGBColor(0x0F, 0x2B, 0x5C)      # FASTLabel dark navy
_BLUE = RGBColor(0x1D, 0x6F, 0xD8)      # FASTLabel blue
_CYAN = RGBColor(0x00, 0xB8, 0xD4)      # Accent cyan
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_LIGHT_GRAY = RGBColor(0xF4, 0xF6, 0xF9)
_DARK_GRAY = RGBColor(0x1F, 0x29, 0x37)
_MID_GRAY = RGBColor(0x6B, 0x74, 0x80)
_ORANGE = RGBColor(0xF5, 0x7C, 0x00)   # Highlight / warning accent

# Slide dimensions (widescreen 13.33 × 7.5 in)
_W = Inches(13.33)
_H = Inches(7.5)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def create_proposal_pptx(proposal: dict, company_name: str) -> bytes:
    """Return the PPTX file as bytes."""
    prs = Presentation()
    prs.slide_width = _W
    prs.slide_height = _H

    today = datetime.date.today().strftime("%Y年%m月%d日")

    _slide_title(prs, company_name, today)
    _slide_agenda(prs)
    _slide_company_overview(prs, company_name, proposal)
    _slide_challenges(prs, company_name, proposal)
    _slide_challenge_details(prs, proposal)
    _slide_proposal_overview(prs, proposal)
    _slide_proposal_details(prs, proposal)
    if proposal.get("roi_estimate"):
        _slide_roi(prs, proposal)
    if proposal.get("case_study"):
        _slide_case_study(prs, proposal)
    _slide_next_steps(prs, company_name, proposal, today)

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def _slide_title(prs: Presentation, company_name: str, today: str) -> None:
    slide = _blank_slide(prs)

    # Full-bleed navy background
    _fill_rect(slide, 0, 0, _W, _H, _NAVY)

    # Decorative cyan accent bar (left edge)
    _fill_rect(slide, 0, 0, Inches(0.12), _H, _CYAN)

    # Top-right logo placeholder
    _add_text(
        slide,
        "FASTLabel",
        Inches(10.5), Inches(0.3), Inches(2.5), Inches(0.5),
        font_size=16, bold=True, color=_CYAN, align=PP_ALIGN.RIGHT,
    )

    # Main title block
    _add_text(
        slide,
        f"{company_name} 様",
        Inches(0.7), Inches(1.8), Inches(12), Inches(0.9),
        font_size=28, bold=False, color=RGBColor(0xB0, 0xC4, 0xDE),
    )
    _add_text(
        slide,
        "AIデータラベリング活用\nご提案書",
        Inches(0.7), Inches(2.6), Inches(12), Inches(2.0),
        font_size=44, bold=True, color=_WHITE,
    )

    # Divider
    _fill_rect(slide, Inches(0.7), Inches(4.7), Inches(5), Inches(0.04), _CYAN)

    # Subtitle / date
    _add_text(
        slide,
        f"FASTLabel株式会社　　{today}",
        Inches(0.7), Inches(4.9), Inches(10), Inches(0.5),
        font_size=14, color=RGBColor(0xB0, 0xC4, 0xDE),
    )
    _add_text(
        slide,
        "Confidential — 社外秘",
        Inches(0.7), Inches(5.5), Inches(10), Inches(0.4),
        font_size=11, color=_MID_GRAY,
    )


def _slide_agenda(prs: Presentation) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "本日のアジェンダ")

    items = [
        ("01", "企業概要・AI活用現状の整理"),
        ("02", "課題仮説"),
        ("03", "FASTLabel提案内容"),
        ("04", "期待効果・ROI"),
        ("05", "導入事例"),
        ("06", "次のステップ"),
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

        # Number badge
        _fill_rect(slide, x, y, Inches(0.55), Inches(0.6), _BLUE)
        _add_text(slide, num, x, y, Inches(0.55), Inches(0.6),
                  font_size=13, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)

        # Label
        _add_text(slide, label, x + Inches(0.65), y, col_w - Inches(0.7), Inches(0.6),
                  font_size=14, color=_DARK_GRAY)


def _slide_company_overview(prs: Presentation, company_name: str, proposal: dict) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, f"{company_name} 様　企業概要・AI活用現状")

    overview = proposal.get("company_overview", "")
    dept = proposal.get("target_department", "")
    persona = proposal.get("target_persona", "")

    # Overview box
    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(12.3), Inches(2.0), _LIGHT_GRAY)
    _add_text(slide, "■ 企業概要・AI活用状況",
              Inches(0.7), Inches(1.65), Inches(12), Inches(0.4),
              font_size=12, bold=True, color=_BLUE)
    _add_text(slide, overview,
              Inches(0.7), Inches(2.05), Inches(12), Inches(1.4),
              font_size=13, color=_DARK_GRAY)

    # Target info
    _add_text(slide, "■ 想定アプローチ先",
              Inches(0.5), Inches(3.75), Inches(12), Inches(0.4),
              font_size=12, bold=True, color=_BLUE)

    card_data = [("想定部門", dept), ("キーパーソン", persona)]
    for idx, (label, value) in enumerate(card_data):
        x = Inches(0.5) + idx * Inches(6.2)
        _fill_rect(slide, x, Inches(4.2), Inches(6.0), Inches(1.0), _LIGHT_GRAY)
        _fill_rect(slide, x, Inches(4.2), Inches(6.0), Inches(0.3), _NAVY)
        _add_text(slide, label, x, Inches(4.2), Inches(6.0), Inches(0.3),
                  font_size=10, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        _add_text(slide, value, x + Inches(0.15), Inches(4.55),
                  Inches(5.7), Inches(0.6),
                  font_size=13, color=_DARK_GRAY)


def _slide_challenges(prs: Presentation, company_name: str, proposal: dict) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, f"{company_name} 様　課題仮説")

    challenges: list[str] = proposal.get("challenges", [])

    # Intro label
    _add_text(slide, "以下の課題仮説を前提に、FASTLabelの活用価値をご提案します",
              Inches(0.5), Inches(1.55), Inches(12.3), Inches(0.35),
              font_size=12, color=_MID_GRAY)

    card_w = Inches(3.8)
    card_h = Inches(3.8)
    gap = Inches(0.35)
    start_x = Inches(0.45)
    start_y = Inches(1.95)

    for i, challenge in enumerate(challenges[:3]):
        x = start_x + i * (card_w + gap)
        # Card background
        _fill_rect(slide, x, start_y, card_w, card_h, _LIGHT_GRAY)
        # Top accent
        _fill_rect(slide, x, start_y, card_w, Inches(0.06), _BLUE)
        # Number
        _fill_rect(slide, x + Inches(0.2), start_y + Inches(0.2),
                   Inches(0.55), Inches(0.55), _NAVY)
        _add_text(slide, f"0{i+1}", x + Inches(0.2), start_y + Inches(0.2),
                  Inches(0.55), Inches(0.55),
                  font_size=14, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        # Challenge text
        _add_text(slide, challenge,
                  x + Inches(0.2), start_y + Inches(0.9),
                  card_w - Inches(0.4), card_h - Inches(1.1),
                  font_size=13, color=_DARK_GRAY)


def _slide_challenge_details(prs: Presentation, proposal: dict) -> None:
    details: list[dict] = proposal.get("challenge_details", [])
    if not details:
        return

    slide = _blank_slide(prs)
    _slide_header(slide, "課題仮説　詳細")

    row_h = Inches(1.55)
    start_y = Inches(1.55)

    for i, d in enumerate(details[:3]):
        y = start_y + i * row_h
        # Left accent bar
        _fill_rect(slide, Inches(0.4), y + Inches(0.15),
                   Inches(0.06), Inches(1.2), _CYAN)
        # Title
        _add_text(slide, d.get("title", ""),
                  Inches(0.6), y + Inches(0.1),
                  Inches(12), Inches(0.4),
                  font_size=14, bold=True, color=_NAVY)
        # Description
        _add_text(slide, d.get("description", ""),
                  Inches(0.6), y + Inches(0.5),
                  Inches(8.5), Inches(0.55),
                  font_size=12, color=_DARK_GRAY)
        # Impact badge
        impact = d.get("business_impact", "")
        if impact:
            _fill_rect(slide, Inches(9.3), y + Inches(0.4),
                       Inches(3.6), Inches(0.7), RGBColor(0xFF, 0xF3, 0xE0))
            _fill_rect(slide, Inches(9.3), y + Inches(0.4),
                       Inches(1.1), Inches(0.7), _ORANGE)
            _add_text(slide, "影響", Inches(9.3), y + Inches(0.4),
                      Inches(1.1), Inches(0.7),
                      font_size=10, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
            _add_text(slide, impact,
                      Inches(10.5), y + Inches(0.4),
                      Inches(2.3), Inches(0.7),
                      font_size=10, color=_DARK_GRAY)

        # Separator line
        _fill_rect(slide, Inches(0.4), y + row_h - Inches(0.05),
                   Inches(12.5), Inches(0.01), RGBColor(0xD0, 0xD7, 0xE3))


def _slide_proposal_overview(prs: Presentation, proposal: dict) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "FASTLabel 提案概要")

    summary = proposal.get("proposal_summary", "")

    # Hero summary box
    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(12.3), Inches(1.3), _NAVY)
    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(0.08), Inches(1.3), _CYAN)
    _add_text(slide, summary,
              Inches(0.8), Inches(1.65), Inches(11.8), Inches(1.1),
              font_size=18, bold=True, color=_WHITE)

    # Three value pillars
    pillars = [
        ("⚡ スピード", "AI開発サイクルを短縮\nデータ準備のボトルネック解消"),
        ("✅ 品質", "高精度アノテーションで\nモデル性能を最大化"),
        ("💰 コスト", "工数削減・外注費削減で\nROI最大化"),
    ]
    card_w = Inches(3.8)
    gap = Inches(0.35)
    start_x = Inches(0.45)
    for i, (icon_label, desc) in enumerate(pillars):
        x = start_x + i * (card_w + gap)
        _fill_rect(slide, x, Inches(3.1), card_w, Inches(2.8), _LIGHT_GRAY)
        _fill_rect(slide, x, Inches(3.1), card_w, Inches(0.55), _BLUE)
        _add_text(slide, icon_label, x, Inches(3.1), card_w, Inches(0.55),
                  font_size=14, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        _add_text(slide, desc, x + Inches(0.2), Inches(3.75),
                  card_w - Inches(0.4), Inches(2.0),
                  font_size=13, color=_DARK_GRAY)


def _slide_proposal_details(prs: Presentation, proposal: dict) -> None:
    details: list[dict] = proposal.get("proposal_details", [])
    if not details:
        return

    slide = _blank_slide(prs)
    _slide_header(slide, "提案内容　詳細")

    row_h = Inches(1.65)
    col_headers = ["提供サービス / 機能", "提供価値", "差別化ポイント", "期待効果"]
    col_ws = [Inches(2.3), Inches(3.2), Inches(3.4), Inches(3.0)]
    col_xs = [Inches(0.3)]
    for w in col_ws[:-1]:
        col_xs.append(col_xs[-1] + w + Inches(0.1))

    header_y = Inches(1.5)
    # Header row
    for j, (label, w, x) in enumerate(zip(col_headers, col_ws, col_xs)):
        _fill_rect(slide, x, header_y, w, Inches(0.45), _NAVY)
        _add_text(slide, label, x, header_y, w, Inches(0.45),
                  font_size=10, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)

    start_y = header_y + Inches(0.45)
    for i, d in enumerate(details[:3]):
        y = start_y + i * row_h
        bg = _LIGHT_GRAY if i % 2 == 0 else _WHITE
        for j, (key, w, x) in enumerate(
            zip(["service_name", "value", "differentiator", "expected_effect"],
                col_ws, col_xs)
        ):
            _fill_rect(slide, x, y, w, row_h - Inches(0.05), bg)
            # Left accent for first column
            if j == 0:
                _fill_rect(slide, x, y, Inches(0.05), row_h - Inches(0.05), _CYAN)
            _add_text(slide, d.get(key, ""),
                      x + Inches(0.1), y + Inches(0.1),
                      w - Inches(0.15), row_h - Inches(0.2),
                      font_size=11, color=_DARK_GRAY)


def _slide_roi(prs: Presentation, proposal: dict) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "期待効果・ROI試算")

    roi_text = proposal.get("roi_estimate", "")

    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(12.3), Inches(2.5), _NAVY)
    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(0.1), Inches(2.5), _CYAN)
    _add_text(slide, "ROI・期待効果",
              Inches(0.8), Inches(1.65), Inches(12), Inches(0.35),
              font_size=11, color=_CYAN)
    _add_text(slide, roi_text,
              Inches(0.8), Inches(2.05), Inches(11.8), Inches(1.8),
              font_size=14, color=_WHITE)

    # Disclaimer
    _add_text(slide, "※ 上記は概算値です。詳細はヒアリング後にカスタマイズいたします。",
              Inches(0.5), Inches(4.2), Inches(12.3), Inches(0.4),
              font_size=10, color=_MID_GRAY)


def _slide_case_study(prs: Presentation, proposal: dict) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "導入事例")

    case = proposal.get("case_study", "")

    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(12.3), Inches(4.5), _LIGHT_GRAY)
    _fill_rect(slide, Inches(0.5), Inches(1.55), Inches(0.1), Inches(4.5), _BLUE)
    _add_text(slide, case,
              Inches(0.8), Inches(1.7), Inches(11.8), Inches(4.2),
              font_size=13, color=_DARK_GRAY)


def _slide_next_steps(
    prs: Presentation, company_name: str, proposal: dict, today: str
) -> None:
    slide = _blank_slide(prs)
    _slide_header(slide, "次のステップ")

    steps: list[str] = proposal.get("next_steps", [])

    # Steps
    for i, step in enumerate(steps[:4]):
        y = Inches(1.6) + i * Inches(1.1)
        _fill_rect(slide, Inches(0.5), y, Inches(0.7), Inches(0.7), _NAVY)
        _add_text(slide, str(i + 1), Inches(0.5), y, Inches(0.7), Inches(0.7),
                  font_size=20, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
        _fill_rect(slide, Inches(1.3), y, Inches(11.5), Inches(0.7), _LIGHT_GRAY)
        _add_text(slide, step, Inches(1.5), y, Inches(11.1), Inches(0.7),
                  font_size=14, color=_DARK_GRAY)

    # Footer
    _fill_rect(slide, 0, _H - Inches(0.8), _W, Inches(0.8), _NAVY)
    _add_text(
        slide,
        f"FASTLabel株式会社　　{company_name} 様向け提案書　　{today}",
        Inches(0.5), _H - Inches(0.7), Inches(12.3), Inches(0.6),
        font_size=10, color=_WHITE,
    )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _blank_slide(prs: Presentation):
    layout = prs.slide_layouts[6]  # blank
    return prs.slides.add_slide(layout)


def _slide_header(slide, title: str) -> None:
    """Add a consistent header bar with title to a content slide."""
    # Background strip
    _fill_rect(slide, 0, 0, _W, Inches(1.3), _NAVY)
    # Bottom accent line
    _fill_rect(slide, 0, Inches(1.3), _W, Inches(0.05), _CYAN)
    # FASTLabel logo
    _add_text(slide, "FASTLabel", Inches(10.5), Inches(0.05),
              Inches(2.5), Inches(0.45),
              font_size=13, bold=True, color=_CYAN, align=PP_ALIGN.RIGHT)
    # Title text
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
    shape.line.fill.background()  # no border


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
        # Fallback to generic Japanese-compatible font
        if not run.font.name:
            run.font.name = "MS PGothic"
