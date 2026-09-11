import os
from pathlib import Path
from typing import Union, List, Dict, Any

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

from app.infrastructure.pptx.styles import (
    DARK_BG,
    LIGHT_BG,
    SLATE_400,
    SLATE_500,
)
from app.infrastructure.pptx.charts import add_pie_chart


class PptxWriter:
    """
    Infrastructure writer responsible for generating PowerPoint
    dashboard presentations.

    This class is responsible only for visual presentation generation.
    Business calculations and aggregations remain in DashboardService.
    """

    # -----------------------------------------------------------------------
    # SHARED SECTION HEADER
    # -----------------------------------------------------------------------

    def _add_section_header(
        self,
        slide,
        title_text: str,
        subtitle_text: str,
    ):
        header_box = slide.shapes.add_textbox(
            Inches(0.8),
            Inches(0.4),
            Inches(11.73),
            Inches(1.1),
        )

        tf = header_box.text_frame
        tf.word_wrap = True

        p_title = tf.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = DARK_BG
        p_title.font.name = "Arial"

        p_sub = tf.add_paragraph()
        p_sub.text = subtitle_text
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = SLATE_500
        p_sub.font.name = "Arial"

    # -----------------------------------------------------------------------
    # KPI SLIDE
    # -----------------------------------------------------------------------

    def _add_kpi_slide(
        self,
        prs,
        blank_layout,
        title_text: str,
        subtitle_text: str,
        kpis_data: List[Dict[str, Any]],
    ):
        slide = prs.slides.add_slide(blank_layout)

        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = LIGHT_BG

        self._add_section_header(
            slide,
            title_text,
            subtitle_text,
        )

        labels = [
            "Réclamations reçues",
            "Réclamations clôturées",
            "En cours chez AP",
            "Taux de clôture dysfonctionnement",
        ]

        # -------------------------------------------------------------------
        # 2 x 2 KPI GRID
        # -------------------------------------------------------------------

        card_width = Inches(4.65)
        card_height = Inches(1.95)

        horizontal_gap = Inches(0.45)
        vertical_gap = Inches(0.40)

        total_width = (
            2 * card_width
            + horizontal_gap
        )

        grid_left = (
            Inches(13.333)
            - total_width
        ) / 2

        first_row_top = Inches(1.90)

        second_row_top = (
            first_row_top
            + card_height
            + vertical_gap
        )

        card_positions = [
            (
                grid_left,
                first_row_top,
            ),
            (
                grid_left
                + card_width
                + horizontal_gap,
                first_row_top,
            ),
            (
                grid_left,
                second_row_top,
            ),
            (
                grid_left
                + card_width
                + horizontal_gap,
                second_row_top,
            ),
        ]

        for idx, kpi in enumerate(kpis_data):
            left, card_top = card_positions[idx]

            # ---------------------------------------------------------------
            # CARD
            # ---------------------------------------------------------------

            shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                left,
                card_top,
                card_width,
                card_height,
            )

            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(
                255,
                255,
                255,
            )

            shape.line.color.rgb = RGBColor(
                226,
                232,
                240,
            )

            shape.line.width = Pt(1)

            # ---------------------------------------------------------------
            # TEXT CONTAINER
            # ---------------------------------------------------------------

            tx_box = slide.shapes.add_textbox(
                left,
                card_top,
                card_width,
                card_height,
            )

            tf_card = tx_box.text_frame
            tf_card.clear()
            tf_card.word_wrap = True

            # Center the complete text block vertically.
            tf_card.vertical_anchor = MSO_ANCHOR.MIDDLE

            tf_card.margin_left = 0
            tf_card.margin_right = 0
            tf_card.margin_top = 0
            tf_card.margin_bottom = 0

            # ---------------------------------------------------------------
            # LABEL
            # ---------------------------------------------------------------

            p_lbl = tf_card.paragraphs[0]

            p_lbl.text = (
                labels[idx]
                if idx < len(labels)
                else kpi.get("label", "")
            )

            p_lbl.alignment = PP_ALIGN.CENTER
            p_lbl.font.size = Pt(11)
            p_lbl.font.bold = True
            p_lbl.font.color.rgb = SLATE_500
            p_lbl.font.name = "Arial"

            p_lbl.space_before = Pt(0)
            p_lbl.space_after = Pt(0)

            # ---------------------------------------------------------------
            # VALUE
            # ---------------------------------------------------------------

            p_val = tf_card.add_paragraph()

            p_val.text = kpi["value"]
            p_val.alignment = PP_ALIGN.CENTER
            p_val.font.size = Pt(38)
            p_val.font.bold = True
            p_val.font.color.rgb = kpi["color"]
            p_val.font.name = "Arial"

            p_val.space_before = Pt(4)
            p_val.space_after = Pt(0)

            # ---------------------------------------------------------------
            # SUPPORTING TEXT — CARD 1 ONLY
            # ---------------------------------------------------------------

            if idx == 0:
                p_note = tf_card.add_paragraph()

                p_note.text = (
                    "Sans compter les réclamations financières"
                )

                p_note.alignment = PP_ALIGN.CENTER
                p_note.font.size = Pt(8.5)
                p_note.font.italic = True
                p_note.font.color.rgb = SLATE_500
                p_note.font.name = "Arial"

                p_note.space_before = Pt(4)
                p_note.space_after = Pt(0)

        return slide

    # -----------------------------------------------------------------------
    # CHART SLIDES
    # -----------------------------------------------------------------------

    def _add_charts_slide(
        self,
        prs,
        blank_layout,
        title_text: str,
        subtitle_text: str,
        charts: List[tuple],
    ):
        slide = prs.slides.add_slide(blank_layout)

        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = LIGHT_BG

        self._add_section_header(
            slide,
            title_text,
            subtitle_text,
        )

        n = len(charts)

        margin_in = 0.8
        slide_width_in = 13.333

        usable_width_in = (
            slide_width_in
            - (2 * margin_in)
        )

        top = Inches(1.72)
        chart_height = Inches(4.85)

        # -------------------------------------------------------------------
        # SPECIAL LAYOUT — SLIDE 3 ONLY
        # -------------------------------------------------------------------
        #
        # Only the Dysfonctionnement slide with 3 charts uses:
        #
        #   [ small ] [        large        ] [        large        ]
        #
        # The first card is shifted to the left and made smaller.
        # Charts 2 and 3 receive the freed width.
        #
        # -------------------------------------------------------------------

        is_dysfonctionnement_three_chart_slide = (
            n == 3
            and "Dysfonctionnement" in title_text
        )

        if is_dysfonctionnement_three_chart_slide:
            gap_in = 0.25

            first_left_in = 0.35
            first_width_in = 2.70

            other_width_in = 4.70

            lefts = [
                first_left_in,
                3.30,
                8.25,
            ]

            widths = [
                first_width_in,
                other_width_in,
                other_width_in,
            ]

        # -------------------------------------------------------------------
        # STANDARD TWO-CHART LAYOUT
        # -------------------------------------------------------------------

        elif n == 2:
            gap_in = 0.40

            chart_width_in = (
                usable_width_in
                - gap_in
            ) / 2.0

            widths = [
                chart_width_in,
                chart_width_in,
            ]

            lefts = [
                margin_in,
                margin_in
                + chart_width_in
                + gap_in,
            ]

        # -------------------------------------------------------------------
        # STANDARD THREE-CHART LAYOUT
        # -------------------------------------------------------------------
        #
        # Used by the Financial slide.
        #
        #   [ normal ] [ normal ] [ normal ]
        #
        # -------------------------------------------------------------------

        elif n == 3:
            gap_in = 0.30

            chart_width_in = (
                usable_width_in
                - (2 * gap_in)
            ) / 3.0

            widths = [
                chart_width_in,
                chart_width_in,
                chart_width_in,
            ]

            lefts = [
                margin_in,
                margin_in
                + chart_width_in
                + gap_in,
                margin_in
                + 2 * (
                    chart_width_in
                    + gap_in
                ),
            ]

        # -------------------------------------------------------------------
        # GENERIC FALLBACK
        # -------------------------------------------------------------------

        else:
            gap_in = 0.30

            chart_width_in = (
                usable_width_in
                - ((n - 1) * gap_in)
            ) / n

            widths = [
                chart_width_in
                for _ in range(n)
            ]

            lefts = [
                margin_in
                + i * (
                    chart_width_in
                    + gap_in
                )
                for i in range(n)
            ]

        # -------------------------------------------------------------------
        # RENDER
        # -------------------------------------------------------------------

        for i, (
            chart_title,
            data_dict,
        ) in enumerate(charts):

            left = Inches(lefts[i])
            width = Inches(widths[i])

            add_pie_chart(
                slide,
                chart_title,
                data_dict,
                left,
                top,
                width,
                chart_height,
            )

        return slide

    # -----------------------------------------------------------------------
    # COMPLETE PRESENTATION
    # -----------------------------------------------------------------------

    def build_dashboard_presentation(
        self,
        filiale_safe: str,
        filiale_raw: str,
        start_date: str,
        end_date: str,
        kpis_dys: List[Dict[str, Any]],
        g1_dys: dict,
        g2_dys: dict,
        g3_dys: dict,
        zoom_app_dys: dict,
        zoom_filiale_dys: dict,
        fg1_fin: dict,
        fg2_fin: dict,
        fg3_fin: dict,
        output_path: Union[str, Path],
    ) -> str:

        prs = Presentation()

        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        blank_layout = prs.slide_layouts[6]

        periode_txt = (
            f"Période du {start_date} au {end_date}"
        )

        # ===================================================================
        # SLIDE 1 — COVER
        # ===================================================================

        slide1 = prs.slides.add_slide(blank_layout)

        asset_bg = os.path.join(
            os.path.dirname(__file__),
            "assets",
            "title_bg.jpg",
        )

        if os.path.exists(asset_bg):
            slide1.shapes.add_picture(
                asset_bg,
                0,
                0,
                Inches(13.333),
                Inches(7.5),
            )
        else:
            slide1.background.fill.solid()
            slide1.background.fill.fore_color.rgb = DARK_BG

        # -------------------------------------------------------------------
        # WHITE INFORMATION CARD
        # -------------------------------------------------------------------

        card1 = slide1.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(8.5),
            Inches(1.2),
            Inches(4.2),
            Inches(5.0),
        )

        card1.fill.solid()
        card1.fill.fore_color.rgb = RGBColor(
            255,
            255,
            255,
        )

        card1.line.color.rgb = RGBColor(
            226,
            232,
            240,
        )

        card1.line.width = Pt(1)

        # -------------------------------------------------------------------
        # CENTERED COVER CONTENT
        # -------------------------------------------------------------------

        tb1 = slide1.shapes.add_textbox(
            Inches(8.65),
            Inches(1.55),
            Inches(3.9),
            Inches(3.85),
        )

        tf1 = tb1.text_frame
        tf1.clear()
        tf1.word_wrap = True

        tf1.vertical_anchor = MSO_ANCHOR.MIDDLE

        tf1.margin_left = 0
        tf1.margin_right = 0
        tf1.margin_top = 0
        tf1.margin_bottom = 0

        # -------------------------------------------------------------------
        # TITLE
        # -------------------------------------------------------------------

        p_t1 = tf1.paragraphs[0]

        p_t1.text = (
            "Tableau de bord des réclamations"
        )

        p_t1.alignment = PP_ALIGN.LEFT
        p_t1.font.size = Pt(22)
        p_t1.font.bold = True
        p_t1.font.color.rgb = DARK_BG
        p_t1.font.name = "Arial"

        p_t1.space_before = Pt(0)
        p_t1.space_after = Pt(0)

        # -------------------------------------------------------------------
        # FILIALE
        # -------------------------------------------------------------------

        p_t2 = tf1.add_paragraph()

        p_t2.text = filiale_raw.upper()
        p_t2.alignment = PP_ALIGN.LEFT
        p_t2.font.size = Pt(36)
        p_t2.font.bold = True
        p_t2.font.color.rgb = RGBColor(
            14,
            116,
            144,
        )
        p_t2.font.name = "Arial"

        p_t2.space_before = Pt(10)
        p_t2.space_after = Pt(0)

        # -------------------------------------------------------------------
        # PERIOD
        # -------------------------------------------------------------------

        p_t3 = tf1.add_paragraph()

        p_t3.text = periode_txt
        p_t3.alignment = PP_ALIGN.LEFT
        p_t3.font.size = Pt(13)
        p_t3.font.bold = False
        p_t3.font.color.rgb = SLATE_500
        p_t3.font.name = "Arial"

        p_t3.space_before = Pt(14)
        p_t3.space_after = Pt(0)

        # -------------------------------------------------------------------
        # DIVIDER
        # -------------------------------------------------------------------

        line1 = slide1.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(8.8),
            Inches(4.8),
            Inches(3.6),
            Inches(0.02),
        )

        line1.fill.solid()
        line1.fill.fore_color.rgb = RGBColor(
            203,
            213,
            225,
        )

        line1.line.fill.background()

        # -------------------------------------------------------------------
        # BOTTOM BANNER
        # -------------------------------------------------------------------

        bbar = slide1.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0),
            Inches(7.0),
            Inches(13.333),
            Inches(0.5),
        )

        bbar.fill.solid()
        bbar.fill.fore_color.rgb = DARK_BG
        bbar.line.fill.background()

        # ===================================================================
        # SLIDE 2 — KPI
        # ===================================================================

        self._add_kpi_slide(
            prs,
            blank_layout,
            "Réclamations Dysfonctionnement — Indicateurs",
            f"Filiale : {filiale_raw} | {periode_txt}",
            kpis_dys,
        )

        # ===================================================================
        # DYNAMIC FILIALE NAME
        # ===================================================================

        g1_dys_formatted = {}

        for key, value in g1_dys.items():
            key_upper = str(key).upper()

            if key_upper in (
                "FILIALE",
                "FILIALES",
            ):
                key_name = filiale_raw.upper()
            else:
                key_name = key

            g1_dys_formatted[key_name] = value

        # ===================================================================
        # SLIDE 3 — DYSFUNCTION
        # ===================================================================

        self._add_charts_slide(
            prs,
            blank_layout,
            "Réclamations Dysfonctionnement — Répartitions",
            f"Filiale : {filiale_raw} | {periode_txt}",
            [
                (
                    "Répartition de l'encours des réclamations",
                    g1_dys_formatted,
                ),
                (
                    "Répartition des réclamations clôturées par nature",
                    g3_dys,
                ),
                (
                    "Répartition des réclamations reçues par nature",
                    g2_dys,
                ),
            ],
        )

        # ===================================================================
        # SLIDE 4 — ZOOM
        # ===================================================================

        self._add_charts_slide(
            prs,
            blank_layout,
            "Zoom sur Réclamations en Cours",
            f"Filiale : {filiale_raw} | {periode_txt}",
            [
                (
                    "Les réclamations en cours AP par nature",
                    zoom_app_dys,
                ),
                (
                    f"Les réclamations en cours {filiale_raw} par nature",
                    zoom_filiale_dys,
                ),
            ],
        )

        # ===================================================================
        # SLIDE 5 — FINANCIAL
        # ===================================================================

        self._add_charts_slide(
            prs,
            blank_layout,
            "Réclamations Financières — Répartitions",
            f"Filiale : {filiale_raw} | {periode_txt}",
            [
                (
                    "Répartition des réclamations reçues par nature",
                    fg1_fin,
                ),
                (
                    "Répartition des réclamations en cours par nature",
                    fg2_fin,
                ),
                (
                    "Répartition des réclamations clôturées par nature",
                    fg3_fin,
                ),
            ],
        )

        # ===================================================================
        # SAVE
        # ===================================================================

        out_str = str(output_path)

        os.makedirs(
            os.path.dirname(
                os.path.abspath(out_str)
            ),
            exist_ok=True,
        )

        prs.save(out_str)

        return out_str


# ---------------------------------------------------------------------------
# BACKWARD COMPATIBILITY
# ---------------------------------------------------------------------------

_default_writer = PptxWriter()


def build_dashboard_presentation(
    *args,
    **kwargs,
) -> str:
    return _default_writer.build_dashboard_presentation(
        *args,
        **kwargs,
    )