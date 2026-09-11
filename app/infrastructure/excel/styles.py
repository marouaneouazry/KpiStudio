from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill(start_color="FFB4C6E7", end_color="FFB4C6E7", fill_type="solid")
HEADER_FONT = Font(bold=True)

RED_FILL = PatternFill(start_color="FFFF0000", end_color="FFFF0000", fill_type="solid")
RED_FILL_LIGHT = PatternFill(start_color="FFFFC7CE", end_color="FFFFC7CE", fill_type="solid")
RED_FONT = Font(bold=True, color="FF9C0006")
RED_FONT_STRONG = Font(bold=True, color="FF000000")

CENTER_ALIGN = Alignment(horizontal="center", vertical="center")


def style_header_row(ws, n_cols: int):
    """Styles the top row of an openpyxl worksheet as a header row."""
    for col in range(1, n_cols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"


def autofit_columns(ws, n_cols: int, max_width: int = 45):
    """Automatically adjusts column widths based on cell content length."""
    for col in range(1, n_cols + 1):
        letter = get_column_letter(col)
        length = max(
            [len(str(ws.cell(row=r, column=col).value or "")) for r in range(1, ws.max_row + 1)],
            default=10
        )
        ws.column_dimensions[letter].width = min(max(length + 2, 10), max_width)


def highlight_hors_delai_rows(ws, delai_col_idx: int, hors_delai_flags: list, header_offset: int = 1):
    """Highlights cells in the 'Délai' column that exceeded SLA in light red."""
    for i, is_hors_delai in enumerate(hors_delai_flags):
        excel_row = header_offset + 1 + i
        if is_hors_delai:
            cell = ws.cell(row=excel_row, column=delai_col_idx)
            cell.fill = RED_FILL_LIGHT
            cell.font = RED_FONT


def merge_sla_groups(ws, sla_col_idx: int, sla_values: list, header_offset: int = 1):
    """Merges consecutive identical SLA value cells in the SLA column."""
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
                ws.merge_cells(
                    start_row=first_row, start_column=sla_col_idx,
                    end_row=last_row, end_column=sla_col_idx
                )

            start_idx = i
