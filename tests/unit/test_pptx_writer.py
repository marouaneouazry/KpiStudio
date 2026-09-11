import pytest
from pathlib import Path
from pptx import Presentation
from app.infrastructure.pptx.writer import PptxWriter
from app.infrastructure.pptx.styles import DARK_BG, RGBColor

def test_pptx_writer_build_dashboard_presentation(tmp_path):
    output_path = tmp_path / "TestDashboard.pptx"
    writer = PptxWriter()

    kpis_dys = [
        {"label": "REÇUES", "value": "10", "color": DARK_BG},
        {"label": "CLÔTURÉES", "value": "8", "color": RGBColor(22, 163, 74)},
        {"label": "EN COURS", "value": "2", "color": RGBColor(217, 119, 6)},
        {"label": "TAUX DE CLÔTURE", "value": "80.0%", "color": RGBColor(37, 99, 235)},
    ]

    saved_path = writer.build_dashboard_presentation(
        filiale_safe="CDM",
        filiale_raw="CDM",
        start_date="2026-01-01",
        end_date="2026-01-31",
        kpis_dys=kpis_dys,
        g1_dys={"APP": 1, "Filiale": 1},
        g2_dys={"INCIDENT": 10},
        g3_dys={"INCIDENT": 8},
        zoom_app_dys={"INCIDENT": 1},
        zoom_filiale_dys={"INCIDENT": 1},
        fg1_fin={},
        fg2_fin={},
        fg3_fin={},
        output_path=output_path
    )

    assert saved_path == str(output_path)
    assert output_path.exists()

    prs = Presentation(output_path)
    # 5 slides: Title, Dys KPIs, Dys Charts, Zoom Charts, Financial Charts
    assert len(prs.slides) == 5
