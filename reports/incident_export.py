"""Excel workbook for the incident report download."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

REPORT_TITLE = 'CDSS REPORT SPREAD SHEET'
REPORT_HEADERS = (
    'Barangay',
    'Disease',
    'Classification',
    'Onset Date',
    'Risk Level',
    'Reporter',
    'Report Date',
)
_MIN_WIDTHS = (18, 36, 16, 16, 14, 28, 24)


def build_incident_workbook(rows):
    """Return an .xlsx where the title and every value fit in the column."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'CDSS Report'

    last_column = get_column_letter(len(REPORT_HEADERS))
    sheet.merge_cells(f'A1:{last_column}1')
    title = sheet['A1']
    title.value = REPORT_TITLE
    title.font = Font(name='Calibri', bold=True, size=16, color='FFFFFF')
    title.alignment = Alignment(horizontal='center', vertical='center')
    title.fill = PatternFill('solid', fgColor='1F4E79')
    sheet.row_dimensions[1].height = 30

    header_font = Font(name='Calibri', bold=True, size=11, color='1F2937')
    header_fill = PatternFill('solid', fgColor='D6E3F0')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1'),
    )
    for column, header in enumerate(REPORT_HEADERS, start=1):
        cell = sheet.cell(2, column, header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin
    sheet.row_dimensions[2].height = 22

    body_font = Font(name='Calibri', size=11)
    body_alignment = Alignment(vertical='center', wrap_text=False)
    for row_number, values in enumerate(rows, start=3):
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row_number, column, value)
            cell.font = body_font
            cell.alignment = body_alignment
            cell.border = thin
        sheet.row_dimensions[row_number].height = 18

    for column, minimum in enumerate(_MIN_WIDTHS, start=1):
        longest = minimum
        for cell in sheet.iter_cols(min_col=column, max_col=column, min_row=2, max_row=sheet.max_row):
            for item in cell:
                text = '' if item.value is None else str(item.value)
                longest = max(longest, min(len(text) + 3, 48))
        sheet.column_dimensions[get_column_letter(column)].width = longest

    sheet.freeze_panes = 'A3'
    sheet.auto_filter.ref = f'A2:{last_column}{max(sheet.max_row, 2)}'
    sheet.page_setup.orientation = 'landscape'
    sheet.page_setup.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_setup.paperSize = sheet.PAPERSIZE_TABLOID
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_title_rows = '1:2'
    sheet.page_setup.horizontalCentered = True
    sheet.sheet_view.showGridLines = False
    sheet.oddHeader.center.text = REPORT_TITLE

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
