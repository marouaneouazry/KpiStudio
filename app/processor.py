import pandas as pd
import numpy as np
import json
import os
import requests
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# PPTX Imports for Dashboard
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

# ---------------------------------------------------------------------------
# RÉPERTOIRES
# ---------------------------------------------------------------------------
try:
    from app.core.config import settings
except ModuleNotFoundError:
    from core.config import settings

PROJECT_ROOT = settings.PROJECT_ROOT
CONFIG_DIR = settings.CONFIG_DIR
OUTPUT_DIR = settings.OUTPUT_DIR

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# DATES — point d'entrée unique pour normaliser tz-naive / tz-aware
# ---------------------------------------------------------------------------
def _to_naive_ts(value):
    """
    Convertit n'importe quelle valeur de date/heure (chaîne, pd.Timestamp
    naive OU tz-aware, datetime, None) en pd.Timestamp tz-naive.

    C'est le correctif central du bug "cannot compare tz-naive and
    tz-aware timestamps" : l'historique Mantis renvoie des timestamps
    avec un fuseau explicite (ex. "+00:00"), alors que les dates issues
    de l'export Excel (Date de soumission, Mis à jour) et la date du jour
    (pd.Timestamp.today()) sont naturellement tz-naive.

    Plutôt que de patcher chaque comparaison une par une, on fait passer
    TOUTE date par cette fonction dès qu'elle entre dans le module — après
    ça, tout est garanti tz-naive et comparable entre soi.

    Si la valeur est tz-aware, on la convertit d'abord en UTC (pour
    préserver l'instant réel), puis on retire l'information de fuseau.
    """
    if value is None:
        return pd.NaT
    if isinstance(value, float) and pd.isna(value):
        return pd.NaT

    ts = pd.to_datetime(value)

    if ts is pd.NaT:
        return pd.NaT

    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)

    return ts


# ---------------------------------------------------------------------------
# SÉCURITÉ
# ---------------------------------------------------------------------------
def sanitize_excel_value(value):
    """Neutralise l'injection de formule Excel sur les champs texte libre
    venant de Mantis. Si la valeur commence par =, +, -, ou @, on la
    préfixe d'une apostrophe pour forcer Excel à la traiter comme du texte
    brut."""
    if isinstance(value, str) and value and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value


_TEXT_COLUMNS_TO_SANITIZE = [
    "Identifiant",
    "Projet",
    "Rapporteur",
    "Assigné à",
    "Priorité",
    "Impact",
    "Reproductibilité",
    "Version du produit",
    "Catégorie",
    "Date de soumission",
    "OS",
    "Version de l'OS",
    "Plate-forme",
    "Visibilité",
    "Mis à jour",
    "Résumé",
    "Statut",
    "Résolution",
    "Résolu dans la version",
    "Description",
    "Responsable",
    "Numéro de la DIM",
    "Ticket externe",
    "Sous Domaine MON",
]


try:
    from app.holidays import get_validated_holiday_dates
except ModuleNotFoundError:
    from holidays import get_validated_holiday_dates


def load_holidays(years=[2026]):
    return get_validated_holiday_dates(years)


# ---------------------------------------------------------------------------
# STYLES EXCEL
# ---------------------------------------------------------------------------
HEADER_FILL = PatternFill(start_color="FFB4C6E7", end_color="FFB4C6E7", fill_type="solid")
HEADER_FONT = Font(bold=True)

RED_FILL = PatternFill(start_color="FFFF0000", end_color="FFFF0000", fill_type="solid")
RED_FILL_LIGHT = PatternFill(start_color="FFFFC7CE", end_color="FFFFC7CE", fill_type="solid")
RED_FONT = Font(bold=True, color="FF9C0006")
RED_FONT_STRONG = Font(bold=True, color="FF000000")

CENTER_ALIGN = Alignment(horizontal="center", vertical="center")


def style_header_row(ws, n_cols):
    for col in range(1, n_cols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"


def autofit_columns(ws, n_cols, max_width=45):
    for col in range(1, n_cols + 1):
        letter = get_column_letter(col)
        length = max(
            [len(str(ws.cell(row=r, column=col).value or "")) for r in range(1, ws.max_row + 1)],
            default=10
        )
        ws.column_dimensions[letter].width = min(max(length + 2, 10), max_width)


def highlight_hors_delai_rows(ws, delai_col_idx, hors_delai_flags, header_offset=1):
    for i, is_hors_delai in enumerate(hors_delai_flags):
        excel_row = header_offset + 1 + i
        if is_hors_delai:
            cell = ws.cell(row=excel_row, column=delai_col_idx)
            cell.fill = RED_FILL_LIGHT
            cell.font = RED_FONT


def merge_sla_groups(ws, sla_col_idx, sla_values, header_offset=1):
    if not sla_values:
        return
    n = len(sla_values)
    start_idx = 0
    for i in range(1, n + 1):
        if i == n or sla_values[i] != sla_values[start_idx]:
            first_row = header_offset + 1 + start_idx
            last_row = header_offset + 1 + (i - 1)

            anchor = ws.cell(row=first_row, column=sla_col_idx)
            anchor.value = sla_values[start_idx]
            anchor.alignment = CENTER_ALIGN

            for r in range(first_row + 1, last_row + 1):
                ws.cell(row=r, column=sla_col_idx).value = None

            if last_row > first_row:
                ws.merge_cells(start_row=first_row, start_column=sla_col_idx,
                                end_row=last_row, end_column=sla_col_idx)

            start_idx = i


# ===========================================================================
# PHASE 2 — Correction du délai via l'historique Mantis (3 cas de pause)
# ===========================================================================
#
# Cas 1 : attente filiale ("Complément d'information" ou Responsable != AP/APP)
# Cas 2 : ticket chez quelqu'un d'autre que le titulaire final (Assigné à)
# Cas 3 : délai administratif entre "A Clôturer" (fin de travail du collab)
#         et "Clôturé" (clôture finale par la filiale)
#
# Cet appel API n'est déclenché QUE pour les tickets déjà détectés hors délai
# avec le calcul brut (performance), sur les Clôturés ET les En Cours.
# ---------------------------------------------------------------------------

# Imports délégués Phase 3 Infrastructure & Service
MANTIS_BASE_URL = settings.MANTIS_BASE_URL
MANTIS_TOKEN = settings.MANTIS_API_TOKEN
MANTIS_VERIFY_SSL = settings.MANTIS_VERIFY_SSL

from app.infrastructure.mantis import get_ticket_history, MantisClient
from app.domain.tickets.timeline import (
    _to_naive_ts,
    _merge_intervals,
    _clip_intervals,
    compute_effective_close_and_pauses,
    total_pause_business_days,
    CLOSED_LABELS,
    TEAM_QUEUE_BUCKETS,
)
from app.services.phase2_service import apply_phase2_correction, Phase2Service


# Excel Infrastructure & Service Imports (Phase 4)
from app.infrastructure.excel import (
    HEADER_FILL,
    HEADER_FONT,
    RED_FILL,
    RED_FILL_LIGHT,
    RED_FONT,
    RED_FONT_STRONG,
    CENTER_ALIGN,
    style_header_row,
    autofit_columns,
    highlight_hors_delai_rows,
    merge_sla_groups,
    read_mantis_export,
    sanitize_excel_value,
    write_kpi_report,
)
from app.services.kpi_service import generate_report, KpiService

# PowerPoint Infrastructure & Service Imports (Phase 5)
from app.infrastructure.pptx import (
    FINANCIAL_SUBDOMAINS,
    DARK_BG,
    LIGHT_BG,
    SLATE_400,
    SLATE_500,
    add_pie_chart,
    PptxWriter,
    build_dashboard_presentation,
)
from app.services.dashboard_service import generate_dashboard, DashboardService