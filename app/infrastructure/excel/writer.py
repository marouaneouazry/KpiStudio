import os
import pandas as pd
from typing import List, Tuple, Any, Union
from pathlib import Path
from app.infrastructure.excel.styles import (
    HEADER_FILL,
    HEADER_FONT,
    RED_FILL,
    RED_FONT_STRONG,
    style_header_row,
    autofit_columns,
    highlight_hors_delai_rows,
    merge_sla_groups,
)

def write_kpi_report(
    sheets_data: List[Tuple[str, pd.DataFrame, List[bool], List[Any]]],
    synth_data: List[List[Any]],
    output_path: Union[str, Path]
) -> str:
    """
    Creates and saves the ApresCalcul.xlsx report containing the 4 ticket detail sheets
    and the summary SLA sheet with openpyxl formatting.
    """
    output_path_str = str(output_path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path_str)), exist_ok=True)

    with pd.ExcelWriter(output_path_str, engine='openpyxl') as writer:
        for sheet_name, df_sheet, flags, sla_values in sheets_data:
            df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            n_cols = df_sheet.shape[1] if not df_sheet.empty else 11
            style_header_row(ws, n_cols)
            if not df_sheet.empty:
                delai_col_idx = list(df_sheet.columns).index("Délai") + 1 if "Délai" in df_sheet.columns else 10
                sla_col_idx = list(df_sheet.columns).index("SLA") + 1 if "SLA" in df_sheet.columns else 11
                highlight_hors_delai_rows(ws, delai_col_idx, flags)
                merge_sla_groups(ws, sla_col_idx, sla_values)
            autofit_columns(ws, n_cols)

        # Write SLA summary sheet
        df_synth = pd.DataFrame(synth_data[1:], columns=synth_data[0])
        df_synth.to_excel(writer, sheet_name='SLA', index=False)
        ws_sla = writer.sheets['SLA']

        style_header_row(ws_sla, 2)

        last_row = ws_sla.max_row
        label_cell = ws_sla.cell(row=last_row, column=1)
        label_cell.font = HEADER_FONT
        label_cell.fill = HEADER_FILL

        value_cell = ws_sla.cell(row=last_row, column=2)
        value_cell.fill = RED_FILL
        value_cell.font = RED_FONT_STRONG
        value_cell.number_format = "0.00%"

        autofit_columns(ws_sla, 2, max_width=60)

    return output_path_str
