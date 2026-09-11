import os

import pandas as pd

from pathlib import Path
from typing import Tuple, Dict, Any, Union, Optional

from pptx.dml.color import RGBColor

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from core.config import settings

from app.infrastructure.excel.reader import (
    read_mantis_export,
    sanitize_excel_value,
)

from app.infrastructure.pptx.styles import (
    FINANCIAL_SUBDOMAINS,
    DARK_BG,
)

from app.infrastructure.pptx.writer import (
    PptxWriter,
)


def _group_counts(
    sub_df: pd.DataFrame,
    col: str = "Sous Domaine MON",
) -> dict:
    if sub_df.empty:
        return {}

    return (
        sub_df[col]
        .value_counts()
        .to_dict()
    )


class DashboardService:
    """
    Application Service responsible for orchestrating
    PowerPoint Dashboard generation.

    Business calculations remain unchanged.

    output_path is optional so callers can isolate
    every generated dashboard in a dedicated job directory.
    """

    def __init__(
        self,
        pptx_writer: Optional[PptxWriter] = None,
    ):
        self.writer = (
            pptx_writer
            or PptxWriter()
        )

    def generate_dashboard(
        self,
        file_path: Union[str, Path],
        start_date: str,
        end_date: str,
        filiale: str,
        output_path: Optional[
            Union[str, Path]
        ] = None,
    ) -> Tuple[
        Dict[str, Any],
        str,
    ]:

        # ===================================================================
        # READ SOURCE
        # ===================================================================

        df = read_mantis_export(
            file_path
        )

        df["Date de soumission"] = (
            pd.to_datetime(
                df[
                    "Date de soumission"
                ],
                format="%Y-%m-%d",
                errors="coerce",
            )
        )

        df["Mis à jour"] = (
            pd.to_datetime(
                df[
                    "Mis à jour"
                ],
                format="%Y-%m-%d",
                errors="coerce",
            )
        )

        df["Filiale"] = (
            df["Projet"]
            .astype(str)
            .str.split("_")
            .str[0]
        )

        start_dt = pd.to_datetime(
            start_date
        )

        end_dt = pd.to_datetime(
            end_date
        )

        # ===================================================================
        # BASE DATASET
        # ===================================================================

        df_base = df[
            (
                df["Filiale"]
                == filiale
            )
            & (
                df["Responsable"].isin(
                    [
                        "APP",
                        "Filiale",
                    ]
                )
            )
        ].copy()

        is_financial = (
            df_base[
                "Sous Domaine MON"
            ].isin(
                FINANCIAL_SUBDOMAINS
            )
        )

        df_dys = df_base[
            ~is_financial
        ].copy()

        df_fin = df_base[
            is_financial
        ].copy()

        clotures_status = [
            "A Clôturer",
            "Clôturé",
        ]

        def in_period(
            series,
            start,
            end,
        ):
            return (
                series >= start
            ) & (
                series <= end
            )

        # ===================================================================
        # DYSFUNCTION
        # ===================================================================

        dys_recues = df_dys[
            in_period(
                df_dys[
                    "Date de soumission"
                ],
                start_dt,
                end_dt,
            )
        ]

        dys_clotures = df_dys[
            df_dys[
                "Statut"
            ].isin(
                clotures_status
            )
            & in_period(
                df_dys[
                    "Mis à jour"
                ],
                start_dt,
                end_dt,
            )
            & in_period(
                df_dys[
                    "Date de soumission"
                ],
                start_dt,
                end_dt,
            )
        ]

        dys_en_cours = df_dys[
            df_dys[
                "Statut"
            ]
            == "En Cours"
        ]

        total_dys_recues = len(
            dys_recues
        )

        total_dys_clotures = len(
            dys_clotures
        )

        total_dys_en_cours = len(
            dys_en_cours
        )

        taux_dys = (
            total_dys_clotures
            / total_dys_recues
            if total_dys_recues > 0
            else 0.0
        )

        dys_en_cours_app = df_dys[
            df_dys[
                "Statut"
            ]
            == "En Cours"
        ]

        dys_en_cours_filiale = df_dys[
            df_dys[
                "Statut"
            ]
            == "Complément d'information"
        ]

        g1_dys = {
            "APP": len(
                dys_en_cours_app
            ),
            "Filiale": len(
                dys_en_cours_filiale
            ),
        }

        g2_dys = _group_counts(
            dys_recues
        )

        g3_dys = _group_counts(
            dys_clotures
        )

        zoom_app_dys = _group_counts(
            dys_en_cours_app
        )

        zoom_filiale_dys = _group_counts(
            dys_en_cours_filiale
        )

        # ===================================================================
        # FINANCIAL
        # ===================================================================

        fin_recues = df_fin[
            in_period(
                df_fin[
                    "Date de soumission"
                ],
                start_dt,
                end_dt,
            )
        ]

        fin_en_cours = df_fin[
            df_fin[
                "Statut"
            ].isin(
                [
                    "En Cours",
                    "Complément d'information",
                ]
            )
        ]

        fin_clotures = df_fin[
            df_fin[
                "Statut"
            ].isin(
                clotures_status
            )
            & in_period(
                df_fin[
                    "Mis à jour"
                ],
                start_dt,
                end_dt,
            )
        ]

        fg1_fin = _group_counts(
            fin_recues
        )

        fg2_fin = _group_counts(
            fin_en_cours
        )

        fg3_fin = _group_counts(
            fin_clotures
        )

        # ===================================================================
        # KPI DATA
        # ===================================================================

        filiale_safe = (
            sanitize_excel_value(
                filiale.upper()
            )
        )

        kpis_dys = [
            {
                "label": "REÇUES",
                "value": str(
                    total_dys_recues
                ),
                "color": DARK_BG,
            },
            {
                "label": "CLÔTURÉES",
                "value": str(
                    total_dys_clotures
                ),
                "color": RGBColor(
                    22,
                    163,
                    74,
                ),
            },
            {
                "label": "EN COURS",
                "value": str(
                    total_dys_en_cours
                ),
                "color": RGBColor(
                    217,
                    119,
                    6,
                ),
            },
            {
                "label": "TAUX DE CLÔTURE",
                "value": (
                    f"{taux_dys:.1%}"
                ),
                "color": RGBColor(
                    37,
                    99,
                    235,
                ),
            },
        ]

        # ===================================================================
        # OUTPUT PATH
        # ===================================================================

        if output_path is None:
            output_path = os.path.join(
                settings.OUTPUT_DIR,
                "Dashboard.pptx",
            )

        output_path = str(
            output_path
        )

        os.makedirs(
            os.path.dirname(
                os.path.abspath(
                    output_path
                )
            ),
            exist_ok=True,
        )

        saved_path = (
            self.writer.build_dashboard_presentation(
                filiale_safe=filiale_safe,
                filiale_raw=filiale,
                start_date=start_date,
                end_date=end_date,
                kpis_dys=kpis_dys,
                g1_dys=g1_dys,
                g2_dys=g2_dys,
                g3_dys=g3_dys,
                zoom_app_dys=zoom_app_dys,
                zoom_filiale_dys=zoom_filiale_dys,
                fg1_fin=fg1_fin,
                fg2_fin=fg2_fin,
                fg3_fin=fg3_fin,
                output_path=output_path,
            )
        )

        # ===================================================================
        # GLOBAL KPI
        # ===================================================================

        total_receves = len(
            df[
                (df["Filiale"] == filiale)
                & (
                    df[
                        "Date de soumission"
                    ] >= start_dt
                )
                & (
                    df[
                        "Date de soumission"
                    ] <= end_dt
                )
            ]
        )

        total_clotures = len(
            df[
                (df["Filiale"] == filiale)
                & df["Statut"].isin(
                    clotures_status
                )
                & (
                    df[
                        "Mis à jour"
                    ] >= start_dt
                )
                & (
                    df[
                        "Mis à jour"
                    ] <= end_dt
                )
            ]
        )

        total_en_cours = len(
            df[
                (df["Filiale"] == filiale)
                & df["Statut"].isin(
                    [
                        "En Cours",
                        "Mise En Production",
                    ]
                )
            ]
        )

        kpi_stats = {
            "total_receves": total_receves,
            "total_clotures": total_clotures,
            "total_en_cours": total_en_cours,
            "dysfonctionnement": {
                "recues": total_dys_recues,
                "clotures": total_dys_clotures,
                "en_cours": total_dys_en_cours,
                "taux_cloture": (
                    f"{taux_dys:.1%}"
                ),
            },
            "financieres": {
                "recues": len(
                    fin_recues
                ),
                "clotures": len(
                    fin_clotures
                ),
                "en_cours": len(
                    fin_en_cours
                ),
            },
        }

        return (
            kpi_stats,
            saved_path,
        )


_default_dashboard_service = (
    DashboardService()
)


def generate_dashboard(
    file_path: Union[str, Path],
    start_date: str,
    end_date: str,
    filiale: str,
    output_path: Optional[
        Union[str, Path]
    ] = None,
) -> Tuple[
    Dict[str, Any],
    str,
]:
    """
    Global helper delegating to DashboardService.

    output_path remains optional for backward compatibility.
    """

    return (
        _default_dashboard_service.generate_dashboard(
            file_path=file_path,
            start_date=start_date,
            end_date=end_date,
            filiale=filiale,
            output_path=output_path,
        )
    )