import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union

import numpy as np
import pandas as pd

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from core.config import settings

from app.infrastructure.excel.reader import (
    read_mantis_export,
    sanitize_excel_value,
    _TEXT_COLUMNS_TO_SANITIZE,
)
from app.infrastructure.excel.writer import write_kpi_report
from app.domain.kpi import calculate_business_days
from app.domain.tickets.timeline import _to_naive_ts
from app.services.phase2_service import apply_phase2_correction

try:
    from app.holidays import get_all_validated_holiday_dates
except ModuleNotFoundError:
    from holidays import get_all_validated_holiday_dates


CLOSED_LABELS = {"A Clôturer", "Clôturé"}


class KpiService:
    """
    Application Service responsable de la génération du rapport KPI.

    Workflow métier :

        Excel
          ↓
        calcul brut avec "Mis à jour"
          ↓
        identification des tickets bruts hors délai
          ↓
        API + timeline métier UNIQUEMENT pour les bruts hors délai
          ↓
        délai corrigé
          ↓
        classement final
          ↓
        génération Excel

    Règles d'affichage :

    1. Ticket clôturé brut dans délai
       -> Date de clôture = "Mis à jour" Excel

    2. Ticket clôturé brut hors délai
       -> Date de clôture = vraie date de clôture métier/API
       -> même si l'API le fait finalement passer dans les délais

    3. Ticket en cours brut dans délai
       -> "Mis à jour" Excel conservé

    4. Ticket en cours brut hors délai
       -> "Mis à jour" = display_update_date calculée par la timeline
       -> "*" si cette date diffère de la date Excel

    IMPORTANT :
    raw_hors_delai et final_hors_delai sont conservés séparément.
    """

    def generate_report(
        self,
        file_path: Union[str, Path],
        start_date: str,
        end_date: str,
        date_column: str,
        sla_groups: List[Union[int, str]],
        collaborators: Optional[List[str]] = None,
        reference_date: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
    ) -> Tuple[Dict[str, Any], str]:

        # ==================================================================
        # 1. LECTURE EXCEL
        # ==================================================================

        df = read_mantis_export(file_path)

        start_dt = pd.to_datetime(
            start_date
        ).normalize()

        end_dt = pd.to_datetime(
            end_date
        ).normalize()

        if start_dt > end_dt:
            raise ValueError(
                "La date de début doit être antérieure ou égale à la date de fin."
            )

        # ==================================================================
        # 2. NORMALISATION DES DATES
        # ==================================================================

        if "Date de soumission" not in df.columns:
            raise ValueError(
                "Colonne 'Date de soumission' absente."
            )

        if "Mis à jour" not in df.columns:
            raise ValueError(
                "Colonne 'Mis à jour' absente."
            )

        if "Statut" not in df.columns:
            raise ValueError(
                "Colonne 'Statut' absente."
            )

        if "Assigné à" not in df.columns:
            raise ValueError(
                "Colonne 'Assigné à' absente."
            )

        if "Identifiant" not in df.columns:
            raise ValueError(
                "Colonne 'Identifiant' absente."
            )

        if "Sous Domaine MON" not in df.columns:
            raise ValueError(
                "Colonne 'Sous Domaine MON' absente."
            )

        df["Date de soumission"] = (
            pd.to_datetime(
                df["Date de soumission"],
                errors="coerce",
            )
            .apply(_to_naive_ts)
        )

        df["Mis à jour"] = (
            pd.to_datetime(
                df["Mis à jour"],
                errors="coerce",
            )
            .apply(_to_naive_ts)
        )

        # ==================================================================
        # 3. FILTRE COLLABORATEURS
        # ==================================================================

        if collaborators:
            df = df[
                df["Assigné à"].isin(
                    collaborators
                )
            ].copy()

        # ==================================================================
        # 4. FILTRE STATUT
        # ==================================================================

        clotures_status = [
            "A Clôturer",
            "Clôturé",
        ]

        en_cours_status = [
            "En Cours",
        ]

        valid_statuses = (
            clotures_status
            + en_cours_status
        )

        df = df[
            df["Statut"].isin(
                valid_statuses
            )
        ].copy()

        # ==================================================================
        # 5. FILTRE DE PÉRIODE
        #
        # Le filtre de période s'applique :
        # - aux tickets clôturés / A Clôturer via date_column
        # - PAS aux tickets En Cours
        # ==================================================================

        if date_column not in df.columns:
            raise ValueError(
                f"Colonne de date invalide : '{date_column}'"
            )

        filter_col = pd.to_datetime(
            df[date_column],
            errors="coerce",
        ).apply(_to_naive_ts)

        is_cloture = df["Statut"].isin(
            clotures_status
        )

        is_en_cours = df["Statut"].isin(
            en_cours_status
        )

        date_in_period = (
            filter_col >= start_dt
        ) & (
            filter_col <= end_dt
        )

        df = df[
            (
                is_cloture
                & date_in_period
            )
            | is_en_cours
        ].copy()

        # ==================================================================
        # 6. CHARGEMENT SLA
        # ==================================================================

        sla_file = settings.SLA_MAPPING_PATH

        with open(
            sla_file,
            "r",
            encoding="utf-8",
        ) as f:
            sla_mapping = json.load(f)

        domain_to_sla = {}

        for sla_value, domains in sla_mapping.items():
            for domain in domains:
                domain_to_sla[
                    domain
                ] = int(sla_value)

        df["SLA"] = (
            df["Sous Domaine MON"]
            .map(domain_to_sla)
        )

        df = df.dropna(
            subset=["SLA"]
        ).copy()

        df["SLA"] = (
            df["SLA"]
            .astype(int)
        )

        sla_groups_int = [
            int(group)
            for group in sla_groups
        ]

        df = df[
            df["SLA"].isin(
                sla_groups_int
            )
        ].copy()

        # ==================================================================
        # 7. JOURS FÉRIÉS
        # ==================================================================

        holidays = (
            get_all_validated_holiday_dates()
        )

        today_ref = (
            pd.to_datetime(
                reference_date
            ).normalize()
            if reference_date
            else pd.Timestamp.today().normalize()
        )

        # ==================================================================
        # 8. CALCUL BRUT
        # ==================================================================

        def calculate_delay_raw(
            row: pd.Series,
        ) -> float:

            submission = (
                row["Date de soumission"]
            )

            if pd.isna(submission):
                return np.nan

            if row["Statut"] in clotures_status:
                end_date_value = (
                    row["Mis à jour"]
                )
            else:
                end_date_value = today_ref

            if pd.isna(end_date_value):
                return np.nan

            start_value = (
                submission.date()
            )

            end_value = (
                end_date_value.date()
                if hasattr(
                    end_date_value,
                    "date",
                )
                else end_date_value
            )

            result = calculate_business_days(
                start_value,
                end_value,
                holidays=holidays,
            )

            return (
                result
                if result is not None
                else np.nan
            )

        df["Délai"] = df.apply(
            calculate_delay_raw,
            axis=1,
        )

        # IMPORTANT :
        # Cette colonne est l'état AVANT API.
        df["_RawHorsDelai"] = (
            df["Délai"] > df["SLA"]
        )

        # Par défaut, le résultat final = brut.
        df["HorsDelai"] = (
            df["_RawHorsDelai"]
        )

        # ==================================================================
        # 9. COLONNES UTILISÉES POUR L'AFFICHAGE
        # ==================================================================

        # Vraie date de clôture API/métier.
        df["_DateClotureAPI"] = pd.NaT

        # Date métier pour les tickets en cours.
        df["_MisAJourAPI"] = (
            df["Mis à jour"]
        )

        # True uniquement lorsqu'une date de mise à jour
        # a réellement été remplacée par la date métier.
        df["_MisAJourCorrigeeAPI"] = False

        # ==================================================================
        # 10. PHASE 2
        #
        # API UNIQUEMENT POUR LES TICKETS BRUTS HORS DÉLAI.
        # ==================================================================

        def maybe_correct_row(
            row: pd.Series,
        ) -> pd.Series:

            raw_hors_delai = bool(
                row["_RawHorsDelai"]
            )

            # --------------------------------------------------------------
            # Ticket brut dans les délais :
            # aucune API.
            # --------------------------------------------------------------

            if not raw_hors_delai:
                return pd.Series(
                    {
                        "corrected_delai":
                            row["Délai"],

                        "final_hors_delai":
                            False,

                        "effective_close_date":
                            pd.NaT,

                        "display_update_date":
                            row["Mis à jour"],

                        "updated_corrected":
                            False,
                    }
                )

            # --------------------------------------------------------------
            # Ticket brut hors délai :
            # API + règles métier.
            # --------------------------------------------------------------

            result = apply_phase2_correction(
                ticket_id=row["Identifiant"],
                current_assignee=row["Assigné à"],
                submission_date=row[
                    "Date de soumission"
                ],
                holidays=holidays,
                today_ref=today_ref,
                collaborators=collaborators,

            )

            # --------------------------------------------------------------
            # API indisponible :
            # on conserve le résultat brut.
            # --------------------------------------------------------------

            if (
                result is None
                or not isinstance(
                    result,
                    dict,
                )
            ):
                return pd.Series(
                    {
                        "corrected_delai":
                            row["Délai"],

                        "final_hors_delai":
                            True,

                        "effective_close_date":
                            pd.NaT,

                        "display_update_date":
                            row["Mis à jour"],

                        "updated_corrected":
                            False,
                    }
                )

            corrected_delai = result.get(
                "corrected_delai"
            )

            if corrected_delai is None:
                corrected_delai = row[
                    "Délai"
                ]

            corrected_delai = float(
                corrected_delai
            )

            final_hors_delai = (
                corrected_delai
                > row["SLA"]
            )

            effective_close_date = result.get(
                "effective_close_date"
            )

            display_update_date = result.get(
                "display_update_date"
            )

            # Si Phase2 n'a pas donné de date métier
            # pour l'encours, on garde Excel.
            if display_update_date is None:
                display_update_date = (
                    row["Mis à jour"]
                )

            display_update_date = (
                _to_naive_ts(
                    display_update_date
                )
                if display_update_date is not None
                else pd.NaT
            )

            original_update = _to_naive_ts(
                row["Mis à jour"]
            )

            updated_corrected = False

            if (
                pd.notna(
                    display_update_date
                )
            ):
                if pd.isna(
                    original_update
                ):
                    updated_corrected = True
                else:
                    updated_corrected = (
                        display_update_date.normalize()
                        !=
                        original_update.normalize()
                    )

            return pd.Series(
                {
                    "corrected_delai":
                        corrected_delai,

                    "final_hors_delai":
                        final_hors_delai,

                    "effective_close_date":
                        effective_close_date,

                    "display_update_date":
                        display_update_date,

                    "updated_corrected":
                        updated_corrected,
                }
            )

        # ==================================================================
        # 11. APPLICATION DE LA PHASE 2
        # ==================================================================

        if df.empty:
            corrections = pd.DataFrame(
                columns=[
                    "corrected_delai",
                    "final_hors_delai",
                    "effective_close_date",
                    "display_update_date",
                    "updated_corrected",
                ]
            )
        else:
            corrections = df.apply(
                maybe_correct_row,
                axis=1,
                result_type="expand",
            )

        df["Délai"] = corrections[
            "corrected_delai"
        ]

        # Etat FINAL du KPI.
        df["HorsDelai"] = (
            corrections[
                "final_hors_delai"
            ]
            .fillna(
                df["_RawHorsDelai"]
            )
            .astype(bool)
        )

        df["_DateClotureAPI"] = (
            corrections[
                "effective_close_date"
            ]
        )

        df["_MisAJourAPI"] = (
            corrections[
                "display_update_date"
            ]
        )

        df["_MisAJourCorrigeeAPI"] = (
            corrections[
                "updated_corrected"
            ]
            .fillna(False)
            .astype(bool)
        )

        # ==================================================================
        # 12. VÉRIFICATION DE PÉRIODE PAR LA VRAIE DATE API
        #
        # Un ticket clôturé trouvé via l'Excel dans la période mais dont
        # la vraie clôture métier est hors période doit être retiré.
        # ==================================================================

        valid_period_mask = pd.Series(
            True,
            index=df.index,
        )

        for idx, row in df.iterrows():

            if row["Statut"] not in clotures_status:
                continue

            effective_close_date = row[
                "_DateClotureAPI"
            ]

            # Seulement pour les tickets ayant réellement
            # subi Phase 2.
            if (
                bool(row["_RawHorsDelai"])
                and pd.notna(
                    effective_close_date
                )
            ):

                effective_dt = (
                    _to_naive_ts(
                        effective_close_date
                    ).normalize()
                )

                if (
                    effective_dt < start_dt
                    or effective_dt > end_dt
                ):
                    valid_period_mask.loc[
                        idx
                    ] = False

        df = df[
            valid_period_mask
        ].copy()

        # ==================================================================
        # 13. PROJET
        # ==================================================================

        if "Projet" in df.columns:
            df["Projet"] = (
                df["Projet"]
                .astype(str)
                .str.split("_")
                .str[0]
            )

        # ==================================================================
        # 14. SOUS-ENSEMBLES FINAUX
        # ==================================================================

        df_clotures = df[
            df["Statut"].isin(
                clotures_status
            )
        ].copy()

        df_clotures_hors_delai = (
            df_clotures[
                df_clotures["HorsDelai"]
            ].copy()
        )

        df_en_cours = df[
            df["Statut"].isin(
                en_cours_status
            )
        ].copy()

        df_en_cours_hors_delai = (
            df_en_cours[
                df_en_cours["HorsDelai"]
            ].copy()
        )

        # ==================================================================
        # 15. TRI
        # ==================================================================

        sort_cols = [
            "SLA",
            "Délai",
        ]

        for subset in [
            df_clotures,
            df_clotures_hors_delai,
            df_en_cours,
            df_en_cours_hors_delai,
        ]:
            subset.sort_values(
                by=sort_cols,
                ascending=[True, True],
                inplace=True,
            )

        # ==================================================================
        # 16. FORMATAGE EXCEL
        # ==================================================================

        def format_sheet_df(
            sub_df: pd.DataFrame,
            closed_sheet: bool = False,
        ) -> Tuple[
            pd.DataFrame,
            List[bool],
            List[int],
        ]:

            if sub_df.empty:

                columns = [
                    "Identifiant",
                    "Projet",
                    "Assigné à",
                    "Date de soumission",
                    "Mis à jour",
                ]

                if closed_sheet:
                    columns.append(
                        "Date de clôture"
                    )

                columns += [
                    "Résumé",
                    "Statut",
                    "Responsable",
                    "Sous Domaine MON",
                    "Délai",
                    "SLA",
                ]

                return (
                    pd.DataFrame(
                        columns=columns
                    ),
                    [],
                    [],
                )

            sub_df = sub_df.copy()

            sub_df.sort_values(
                by=[
                    "SLA",
                    "Délai",
                ],
                ascending=[True, True],
                inplace=True,
            )

            hors_delai_flags = list(
                sub_df["HorsDelai"]
            )

            sla_values = list(
                sub_df["SLA"]
            )

            result = pd.DataFrame()

            result["Identifiant"] = (
                sub_df["Identifiant"]
            )

            result["Projet"] = (
                sub_df["Projet"]
            )

            result["Assigné à"] = (
                sub_df["Assigné à"]
            )

            # --------------------------------------------------------------
            # DATE DE SOUMISSION
            # --------------------------------------------------------------

            result[
                "Date de soumission"
            ] = sub_df[
                "Date de soumission"
            ].apply(
                lambda value:
                    ""
                    if pd.isna(value)
                    else _to_naive_ts(
                        value
                    ).strftime(
                        "%Y-%m-%d"
                    )
            )

            # --------------------------------------------------------------
            # MIS À JOUR
            #
            # UNIQUEMENT MODIFIÉ POUR :
            # ticket brut hors délai + en cours
            # --------------------------------------------------------------

            def format_mis_a_jour(
                row: pd.Series,
            ) -> str:

                original_value = (
                    row["Mis à jour"]
                )

                display_value = (
                    row["_MisAJourAPI"]
                    if bool(
                        row["_RawHorsDelai"]
                    )
                    and row["Statut"]
                    not in CLOSED_LABELS
                    and pd.notna(
                        row["_MisAJourAPI"]
                    )
                    else original_value
                )

                if pd.isna(
                    display_value
                ):
                    formatted = ""
                else:
                    formatted = (
                        _to_naive_ts(
                            display_value
                        ).strftime(
                            "%Y-%m-%d"
                        )
                    )

                # Étoile uniquement si la date a été corrigée.
                if (
                    bool(
                        row["_RawHorsDelai"]
                    )
                    and row["Statut"]
                    not in CLOSED_LABELS
                    and bool(
                        row["_MisAJourCorrigeeAPI"]
                    )
                ):
                    formatted += "*"

                return formatted

            result["Mis à jour"] = (
                sub_df.apply(
                    format_mis_a_jour,
                    axis=1,
                )
            )

            # --------------------------------------------------------------
            # DATE DE CLÔTURE
            #
            # REGLE :
            #
            # 1. brut dans délai
            #    -> Mis à jour Excel
            #
            # 2. brut hors délai
            #    -> vraie date effective API
            #       même si l'API le fait finalement repasser
            #       dans les délais.
            # --------------------------------------------------------------

            if closed_sheet:

                def format_date_cloture(
                    row: pd.Series,
                ) -> str:

                    raw_hors_delai = bool(
                        row["_RawHorsDelai"]
                    )

                    if (
                        raw_hors_delai
                        and pd.notna(
                            row["_DateClotureAPI"]
                        )
                    ):
                        value = (
                            row["_DateClotureAPI"]
                        )
                    else:
                        value = (
                            row["Mis à jour"]
                        )

                    if pd.isna(value):
                        return ""

                    return _to_naive_ts(
                        value
                    ).strftime(
                        "%Y-%m-%d"
                    )

                result["Date de clôture"] = (
                    sub_df.apply(
                        format_date_cloture,
                        axis=1,
                    )
                )

            # --------------------------------------------------------------
            # AUTRES COLONNES
            # --------------------------------------------------------------

            result["Résumé"] = (
                sub_df["Résumé"]
            )

            result["Statut"] = (
                sub_df["Statut"]
            )

            result["Responsable"] = (
                sub_df["Responsable"]
            )

            result["Sous Domaine MON"] = (
                sub_df[
                    "Sous Domaine MON"
                ]
            )

            result["Délai"] = (
                sub_df["Délai"]
            )

            result["SLA"] = (
                sub_df["SLA"]
            )

            # --------------------------------------------------------------
            # ORDRE FINAL
            # --------------------------------------------------------------

            ordered_columns = [
                "Identifiant",
                "Projet",
                "Assigné à",
                "Date de soumission",
                "Mis à jour",
            ]

            if closed_sheet:
                ordered_columns.append(
                    "Date de clôture"
                )

            ordered_columns += [
                "Résumé",
                "Statut",
                "Responsable",
                "Sous Domaine MON",
                "Délai",
                "SLA",
            ]

            result = result[
                ordered_columns
            ].copy()

            # --------------------------------------------------------------
            # SANITIZATION
            # --------------------------------------------------------------

            for column in (
                _TEXT_COLUMNS_TO_SANITIZE
            ):
                if column in result.columns:
                    result[column] = (
                        result[column]
                        .apply(
                            sanitize_excel_value
                        )
                    )

            return (
                result,
                hors_delai_flags,
                sla_values,
            )

        # ==================================================================
        # 17. FEUILLES
        # ==================================================================

        formatted_clotures, \
            flags_clotures, \
            sla_clotures = format_sheet_df(
                df_clotures,
                closed_sheet=True,
            )

        formatted_clotures_hd, \
            flags_clotures_hd, \
            sla_clotures_hd = format_sheet_df(
                df_clotures_hors_delai,
                closed_sheet=True,
            )

        formatted_en_cours, \
            flags_en_cours, \
            sla_en_cours = format_sheet_df(
                df_en_cours,
                closed_sheet=False,
            )

        formatted_en_cours_hd, \
            flags_en_cours_hd, \
            sla_en_cours_hd = format_sheet_df(
                df_en_cours_hors_delai,
                closed_sheet=False,
            )

        # ==================================================================
        # 18. KPI
        # ==================================================================

        c2 = len(
            df_clotures[
                ~df_clotures["HorsDelai"]
            ]
        )

        c3 = len(
            df_clotures
        )

        c4 = len(
            df_en_cours_hors_delai
        )

        c_en_cours_dans_delai = len(
            df_en_cours[
                ~df_en_cours["HorsDelai"]
            ]
        )

        kpi_pct = 0.0

        if (
            c3 + c4
        ) > 0:

            kpi_pct = (
                c2 /
                (
                    c3 + c4
                )
            )

        # ==================================================================
        # 19. TICKETS HORS DÉLAI FINAUX
        # ==================================================================

        hors_delai_tickets = []

        for subset in [
            df_clotures_hors_delai,
            df_en_cours_hors_delai,
        ]:

            if subset.empty:
                continue

            for _, row in subset.iterrows():

                hors_delai_tickets.append(
                    {
                        "id":
                            str(
                                row[
                                    "Identifiant"
                                ]
                            ),

                        "resume":
                            (
                                str(
                                    row["Résumé"]
                                )
                                if pd.notna(
                                    row["Résumé"]
                                )
                                else ""
                            ),

                        "assigne":
                            (
                                str(
                                    row["Assigné à"]
                                )
                                if pd.notna(
                                    row["Assigné à"]
                                )
                                else ""
                            ),

                        "statut":
                            (
                                str(
                                    row["Statut"]
                                )
                                if pd.notna(
                                    row["Statut"]
                                )
                                else ""
                            ),
                    }
                )

        # ==================================================================
        # 20. STATISTIQUES
        # ==================================================================

        kpi_stats = {
            "clotures_dans_delai":
                c2,

            "clotures_hors_delai":
                c3 - c2,

            "en_cours_dans_delai":
                c_en_cours_dans_delai,

            "en_cours_hors_delai":
                c4,

            "kpi_sla_ap":
                f"{kpi_pct:.1%}",

            "c2":
                c2,

            "c3":
                c3,

            "c4":
                c4,

            "hors_delai_tickets":
                hors_delai_tickets,
        }

        # ==================================================================
        # 21. OUTPUT
        # ==================================================================

        if output_path is None:
            output_path = os.path.join(
                settings.OUTPUT_DIR,
                "ApresCalcul.xlsx",
            )
        else:
            output_path = str(
                output_path
            )

        output_parent = os.path.dirname(
            output_path
        )

        if output_parent:
            os.makedirs(
                output_parent,
                exist_ok=True,
            )

        # ==================================================================
        # 22. FEUILLE SYNTHÈSE
        # ==================================================================

        synth_data = [
            [
                "Indicateur",
                "Valeur",
            ],

            [
                f"Demandes traitées du "
                f"{start_date} au "
                f"{end_date} dans les délais",
                c2,
            ],

            [
                f"Demandes traitées du "
                f"{start_date} au "
                f"{end_date}",
                c3,
            ],

            [
                "Demandes en cours hors SLA au "
                f"{today_ref.strftime('%d-%m-%Y')}",
                c4,
            ],

            [
                "Taux de respect SLA",
                kpi_pct,
            ],
        ]

        sheets_to_write = [
            (
                "Clôturées",
                formatted_clotures,
                flags_clotures,
                sla_clotures,
            ),

            (
                "Clôturées hors délai",
                formatted_clotures_hd,
                flags_clotures_hd,
                sla_clotures_hd,
            ),

            (
                "En cours",
                formatted_en_cours,
                flags_en_cours,
                sla_en_cours,
            ),

            (
                "En cours hors délai",
                formatted_en_cours_hd,
                flags_en_cours_hd,
                sla_en_cours_hd,
            ),
        ]

        # IMPORTANT :
        # Le writer actuel doit accepter output_path.
        saved_path = write_kpi_report(
            sheets_to_write,
            synth_data,
            output_path,
        )

        return (
            kpi_stats,
            saved_path,
        )


# ============================================================================
# INSTANCE PAR DÉFAUT
# ============================================================================

_default_kpi_service = KpiService()


# ============================================================================
# WRAPPER DE COMPATIBILITÉ
# ============================================================================

def generate_report(
    file_path: Union[str, Path],
    start_date: str,
    end_date: str,
    date_column: str,
    sla_groups: List[Union[int, str]],
    collaborators: Optional[List[str]] = None,
    reference_date: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Wrapper global conservant la compatibilité avec les routes existantes.
    """

    return _default_kpi_service.generate_report(
        file_path=file_path,
        start_date=start_date,
        end_date=end_date,
        date_column=date_column,
        sla_groups=sla_groups,
        collaborators=collaborators,
        reference_date=reference_date,
        output_path=output_path,
    )