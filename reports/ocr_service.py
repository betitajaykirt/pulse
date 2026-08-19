"""
OCR service for laboratory result document parsing.

Uses OCR.Space API to extract text, then applies regex-based field
extraction for patient demographics, lab identifiers, and clinical
findings.  Provides keyword matching for Test Type and Confirmed
Disease dropdowns, plus patient-name cross-validation.
"""
from __future__ import annotations

import os
import re
from difflib import SequenceMatcher

import requests


# ── OCR.Space API client ─────────────────────────────────────────

def call_ocr_api(file_obj) -> dict:
    """
    Send an uploaded file to OCR.Space and return the API response.

    Returns dict with keys:
      - ``success`` (bool)
      - ``raw_text`` (str)  — full extracted text on success
      - ``error``   (str)   — error message on failure
    """
    api_url = os.environ.get('OCR_API_URL', 'https://api.ocr.space/parse/image')
    api_key = os.environ.get('OCR_API_KEY', '')

    if not api_key:
        return {'success': False, 'raw_text': '', 'error': 'OCR API key not configured.'}

    try:
        payload = {
            'apikey': api_key,
            'language': 'eng',
            'isOverlayRequired': 'false',
            'detectOrientation': 'true',
            'scale': 'true',
            'isTable': 'true',
            'OCREngine': '2',
        }
        files = {'file': (file_obj.name, file_obj.read(), file_obj.content_type)}
        resp = requests.post(api_url, data=payload, files=files, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if data.get('IsErroredOnProcessing'):
            error_msg = '; '.join(data.get('ErrorMessage', []) or ['OCR processing error.'])
            return {'success': False, 'raw_text': '', 'error': error_msg}

        parsed = data.get('ParsedResults', [])
        if not parsed:
            return {'success': False, 'raw_text': '', 'error': 'No text detected in document.'}

        raw_text = '\n'.join(r.get('ParsedText', '') for r in parsed)
        return {'success': True, 'raw_text': raw_text, 'error': ''}

    except requests.RequestException as exc:
        return {'success': False, 'raw_text': '', 'error': f'OCR API request failed: {exc}'}


_JUNK_IDENTIFIERS = frozenset({
    'control', 'number', 'no', 'lab', 'specimen', 'issued', 'certificate',
    'result', 'date', 'name', 'report', 'test', 'id', 'accession', 'na',
})

_PORT_RE = re.compile(r'\b(PORT[\s\-]?\d{6,8}[\s\-]?\d{3,6})\b', re.IGNORECASE)
_LC_RE = re.compile(r'\b(LC[\s\-]?\d{4}[\s\-]?[A-Za-z0-9]{4,8})\b', re.IGNORECASE)
_DATE_RE = re.compile(
    r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}'
    r'(?:\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s*[AaPp][Mm])?)?)\b'
)


def _clean(val: str) -> str:
    """Strip whitespace, trailing punctuation artefacts, and normalize."""
    if not val:
        return ''
    val = val.strip()
    val = val.rstrip('|:;,')
    val = re.sub(r'\s+', ' ', val)
    return val.strip()


def _clean_block(val: str) -> str:
    """Preserve line breaks for multi-line result summaries."""
    if not val:
        return ''
    lines = []
    for line in val.splitlines():
        line = _clean(line)
        if line:
            lines.append(line)
    return '\n'.join(lines)


def _normalize_ocr_text(raw_text: str) -> str:
    """Repair common OCR artefacts before field extraction."""
    t = raw_text or ''
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    t = t.replace('\u00a0', ' ').replace('|', '\n')
    t = t.replace('lssued', 'Issued').replace('lssue', 'Issue')
    t = t.replace('Certiflcate', 'Certificate').replace('Certifìcate', 'Certificate')
    t = re.sub(r'[ \t]+', ' ', t)
    # Put known labels on their own line when OCR glued columns together.
    label_split = (
        r'(?=Name\s*:|Birthday\s*:|Age\s*:|Gender\s*:|Sex\s*:|Address\s*:|'
        r'Barangay\s*:|City\s*:|Lab(?:oratory)?\s*(?:Number|No\.?)\s*:|'
        r'Control\s*(?:Number|No\.?)\s*:|Certificate\s*Issued|'
        r'Interpretation\s*:|Remarks\s*:|Result(?:s)?(?:\s*\([^)]+\))?\s*:)'
    )
    t = re.sub(label_split, r'\n', t, flags=re.IGNORECASE)
    return t


def _normalize_id(value: str) -> str:
    value = _clean(value).upper().replace(' ', '')
    value = re.sub(r'[^A-Z0-9\-]', '', value)
    if '-' not in value and re.fullmatch(r'PORT\d{9,14}', value):
        # PORT + YYYYMM (6) + serial
        value = f'{value[:10]}-{value[10:]}'
    if '-' not in value and re.fullmatch(r'LC\d{4}[A-Z0-9]{4,8}', value):
        value = f'LC-{value[2:6]}-{value[6:]}'
    return value


def _is_junk_identifier(value: str) -> bool:
    token = re.sub(r'[^a-z0-9]', '', (value or '').lower())
    return not token or token in _JUNK_IDENTIFIERS or len(token) < 4


def _first_group(pattern: str, text: str, flags=re.IGNORECASE) -> str:
    m = re.search(pattern, text, flags)
    return _clean(m.group(1)) if m else ''


def _extract_lab_identifiers(text: str) -> tuple[str, str]:
    """Return (control_number, lab_number) using patterns first, labels second."""
    port_match = _PORT_RE.search(text)
    lc_match = _LC_RE.search(text)
    lab_number = _normalize_id(port_match.group(1)) if port_match else ''
    control_number = _normalize_id(lc_match.group(1)) if lc_match else ''

    labeled_lab = _first_group(
        r'(?:Lab(?:oratory)?\s*(?:Number|No\.?)|Specimen\s*(?:ID|Number|No\.?)|Accession\s*(?:No\.?))\s*[:\-]\s*([A-Za-z0-9\-]+)',
        text,
    )
    labeled_control = _first_group(
        r'(?:Control\s*(?:Number|No\.?)|Laboratory\s*Control(?:\s*Number)?)\s*[:\-]\s*([A-Za-z0-9\-]+)',
        text,
    )

    def _assign_identifier(raw: str):
        nonlocal lab_number, control_number
        if not raw or _is_junk_identifier(raw):
            return
        normalized = _normalize_id(raw)
        if normalized.startswith('PORT'):
            lab_number = normalized
        elif normalized.startswith('LC'):
            control_number = normalized
        elif not lab_number and not normalized.startswith('LC'):
            lab_number = raw
        elif not control_number:
            control_number = raw

    _assign_identifier(labeled_lab)
    _assign_identifier(labeled_control)

    # Swap if OCR assigned the two identifiers to the opposite labels.
    if lab_number.startswith('LC-') and control_number.startswith('PORT'):
        lab_number, control_number = control_number, lab_number
    if lab_number.startswith('LC-') and not control_number:
        control_number, lab_number = lab_number, ''
    if control_number.startswith('PORT') and not lab_number:
        lab_number, control_number = control_number, ''

    if _is_junk_identifier(lab_number):
        lab_number = ''
    if _is_junk_identifier(control_number):
        control_number = ''
    return control_number, lab_number


def _extract_issue_date(text: str) -> str:
    labeled = _first_group(
        r'(?:Certificate\s*Issued|Result\s*Date|Date\s*Released|Date\s*Issued|Issue\s*Date)'
        r'\s*[:\-]?\s*([\d/\-]+(?:\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s*[AaPp][Mm])?)?)',
        text,
    )
    if labeled and _DATE_RE.search(labeled):
        return _clean(labeled.replace('.', ':'))

    # Prefer a date+time near certificate/issue wording.
    window = re.search(
        r'(?:Certificate|Issued|Released|Result\s*Date).{0,40}?(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}'
        r'(?:\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s*[AaPp][Mm])?)?)',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if window:
        return _clean(window.group(1).replace('.', ':'))

    birthday = _first_group(r'(?:Birthday|Date\s*of\s*Birth|DOB)\s*[:\-]?\s*([\d/\-]+)', text)
    dates = [_clean(m.group(1).replace('.', ':')) for m in _DATE_RE.finditer(text)]
    timed = [d for d in dates if re.search(r'\d{1,2}[:.]\d{2}', d)]
    if timed:
        return timed[-1]
    remaining = [d for d in dates if d != birthday]
    return remaining[-1] if remaining else ''


def _marker_status(raw: str) -> str:
    val = (raw or '').upper()
    val = val.replace('NOTDETECTED', 'NOT DETECTED')
    if 'NOT DETECTED' in val or val in {'NEGATIVE', 'NEG', 'NONREACTIVE', 'NON-REACTIVE'}:
        return 'NOT DETECTED'
    if 'DETECTED' in val or val in {'POSITIVE', 'POS', 'REACTIVE'}:
        return 'DETECTED'
    return _clean(raw).upper()


def _extract_markers(text: str) -> list[dict]:
    specs = [
        ('NS1', r'(?:DENGUE\s+(?:VIRUS\s+)?)?NS[\s\-]?1(?:\s+ANTIGEN)?'),
        ('IgM', r'(?:DENGUE\s+)?Ig[\s\-]?M(?:\s+ANTIBODY)?'),
        ('IgG', r'(?:DENGUE\s+)?Ig[\s\-]?G(?:\s+ANTIBODY)?'),
    ]
    markers = []
    seen = set()
    for name, label_re in specs:
        pattern = (
            rf'{label_re}\s*[:\-]?\s*'
            r'(DETECTED|NOT\s*DETECTED|POSITIVE|NEGATIVE|REACTIVE|NON[\s\-]?REACTIVE)'
        )
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            continue
        status = _marker_status(m.group(1))
        markers.append({
            'name': name,
            'status': status,
            'positive': status == 'DETECTED',
        })
        seen.add(name)
    return markers


def _format_findings(markers: list[dict], fallback_block: str) -> str:
    labels = {
        'NS1': 'DENGUE VIRUS NS1 ANTIGEN',
        'IgM': 'DENGUE IgM ANTIBODY',
        'IgG': 'DENGUE IgG ANTIBODY',
    }
    if markers:
        return '\n'.join(f"{labels[m['name']]}: {m['status']}" for m in markers)
    return fallback_block


def _extract_findings_block(text: str) -> str:
    m = re.search(
        r'(?:Test\s*Results?|Results?(?:\s*\([^)]+\))?|Findings?)\s*[:\-]?\s*'
        r'([\s\S]*?)'
        r'(?=\s*(?:Interpretation|Diagnostic\s*Impression|Impression|Remarks|Methodology|Recommendation|$))',
        text,
        re.IGNORECASE,
    )
    if not m:
        return ''
    return _clean_block(m.group(1))


def _extract_interpretation(text: str, markers: list[dict]) -> str:
    m = re.search(
        r'(?:Interpretation|Diagnostic\s*Impression|Impression)\s*[:\-]?\s*'
        r'([\s\S]*?)'
        r'(?=\s*(?:Remarks|Recommendation|Note|Methodology|Prepared\s*by|'
        r'Pathologist|Medical\s*Technologist|Verified\s*by|Noted\s*by|$))',
        text,
        re.IGNORECASE,
    )
    if m:
        value = _clean_block(m.group(1)).split('\n')[0]
        if value:
            return value

    m = re.search(
        r'((?:POSITIVE|NEGATIVE)\s+FOR\s+[A-Z][A-Z\s,]{8,80})',
        text,
        re.IGNORECASE,
    )
    if m:
        return _clean(m.group(1)).upper()

    positives = [m['name'] for m in markers if m['positive']]
    if 'NS1' in positives or 'IgM' in positives:
        return 'POSITIVE FOR ACUTE DENGUE FEVER INFECTION'
    if markers and not positives:
        return 'NEGATIVE FOR DENGUE FEVER INFECTION'
    return ''


def _marker_summary(markers: list[dict]) -> str:
    if not markers:
        return ''
    return ' / '.join(
        f"{m['name']}({'+' if m['positive'] else '-'})" for m in markers
    )


def _primary_result(interpretation: str, markers: list[dict]) -> str:
    interp = (interpretation or '').upper()
    if 'POSITIVE' in interp:
        detail = interpretation
        if 'ACUTE' in interp:
            return detail
        return f'POSITIVE — {interpretation}' if interpretation else 'POSITIVE'
    if 'NEGATIVE' in interp:
        return interpretation or 'NEGATIVE'
    if any(m['positive'] for m in markers):
        return 'POSITIVE'
    if markers:
        return 'NEGATIVE'
    return ''


def _extract_patient_name(text: str) -> str:
    m = re.search(
        r'(?:Patient\s*Name|^Name)\s*[:\-]\s*'
        r'([A-Za-z][A-Za-z\s,.\'-]{1,80}?)'
        r'(?=\s*(?:Birthday|Age|Nationality|Civil\s*Status|Date\s*of\s*Birth|Sex|Gender|Passport|Address|\n|$))',
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if m:
        name = _clean(m.group(1))
        name = re.sub(r'\s+', ' ', name).strip(' .,-')
        if name.lower() not in {'name', 'patient', 'patient name'}:
            return name
    m = re.search(
        r'\bName\s*[:\-]\s*([A-Z][A-Z\s,.\'-]{2,80}?)(?=\s*(?:Birthday|Age|Nationality|Gender|Sex|\n))',
        text,
        re.IGNORECASE,
    )
    return _clean(m.group(1)) if m else ''


def _extract_address(text: str) -> str:
    address = ''
    m = re.search(
        r'Address\s*[:\-]\s*'
        r'([A-Za-z0-9\s,.\-]+?)'
        r'(?=\s*(?:Barangay|City|Province|Email|Phone|Contact|Municipality|Region|\n|$))',
        text,
        re.IGNORECASE,
    )
    if m:
        address = _clean(m.group(1))
    if not address or len(address) < 5:
        m = re.search(
            r'Address\s*[:\-]\s*(.+?)(?=\s*(?:Email|Phone|Contact|Nationality|Civil\s*Status|\n|$))',
            text,
            re.IGNORECASE,
        )
        if m:
            address = _clean(m.group(1))

    m_brgy = re.search(
        r'Barangay\s*[:\-]\s*([A-Za-z0-9\s,.]+?)(?=\s*(?:City|Province|Municipality|Region|\n|$))',
        text,
        re.IGNORECASE,
    )
    if m_brgy:
        brgy_val = _clean(m_brgy.group(1))
        if brgy_val and brgy_val.lower() not in address.lower():
            address = f'{address}, BARANGAY {brgy_val}' if address else f'BARANGAY {brgy_val}'
    return address


def build_lab_overview(fields: dict) -> dict:
    markers = fields.get('markers') or []
    interpretation = fields.get('interpretation') or ''
    return {
        'patient': fields.get('patient_name') or '',
        'test_date': fields.get('result_date') or '',
        'primary_result': _primary_result(interpretation, markers),
        'markers': markers,
        'marker_summary': _marker_summary(markers),
        'verdict': (
            'POSITIVE' if 'POSITIVE' in (interpretation or '').upper()
            or any(m.get('positive') for m in markers)
            else ('NEGATIVE' if markers or 'NEGATIVE' in (interpretation or '').upper() else '')
        ),
    }


def parse_lab_fields(raw_text: str) -> dict:
    """
    Parse all structured fields from OCR-extracted laboratory text
    using pattern-first matching plus labeled fallbacks.

    Returns a dict with extracted fields (empty string when not found).
    """
    t = _normalize_ocr_text(raw_text or '')

    patient_name = _extract_patient_name(t)
    age = _first_group(r'Age\s*[:\-]?\s*(\d{1,3})', t)
    sex = _first_group(r'(?:Gender|Sex)\s*[:\-]?\s*([A-Za-z]+)', t)
    address = _extract_address(t)
    control_number, lab_number = _extract_lab_identifiers(t)
    result_date = _extract_issue_date(t)
    markers = _extract_markers(t)
    lab_results = _format_findings(markers, _extract_findings_block(t))
    interpretation = _extract_interpretation(t, markers)

    fields = {
        'patient_name': patient_name,
        'age': age,
        'sex': sex.upper() if sex else '',
        'address': address,
        'control_number': control_number,
        'lab_number': lab_number,
        'result_date': result_date,
        'lab_results': lab_results,
        'interpretation': interpretation,
        'markers': markers,
        'marker_summary': _marker_summary(markers),
    }
    fields['overview'] = build_lab_overview(fields)
    return fields


# ── Test Type keyword matching ───────────────────────────────────

_TEST_TYPE_KEYWORDS: list[tuple[list[str], str]] = [
    (['NS1 Ag & IgG/IgM Combo', 'NS1 Ag', 'IgG/IgM Combo',
      'Dengue NS1', 'NS1 Antigen', 'NS1', 'NS-1'],           'Dengue NS1 Ag & IgG/IgM Combo'),
    (['IgM ELISA', 'ELISA'],                                  'IgM ELISA'),
    (['PCR', 'Polymerase', 'RT-PCR', 'RTPCR'],                'PCR'),
    (['Rapid Diagnostic', 'RDT', 'Rapid Test',
      'Immunochromatographic', 'Lateral flow'],               'Rapid Diagnostic Test'),
    (['Culture', 'Blood Culture', 'Stool Culture'],            'Culture'),
]


def match_test_type(raw_text: str) -> str:
    """Return the best matching Test Type dropdown value, or empty string."""
    t = (raw_text or '').lower()
    for keywords, value in _TEST_TYPE_KEYWORDS:
        for kw in keywords:
            if kw.lower() in t:
                return value
    return ''


# ── Disease keyword matching ─────────────────────────────────────

_DISEASE_KEYWORDS: list[tuple[list[str], str]] = [
    (['dengue', 'DENV', 'NS1', 'dengue virus'],                         'Dengue Fever'),
    (['leptospira', 'leptospirosis'],                                     'Leptospirosis'),
    (['typhoid', 'salmonella typhi', 'widal'],                           'Typhoid Fever'),
    (['anthrax', 'bacillus anthracis'],                                  'Anthrax'),
    (['meningococcal', 'neisseria meningitidis'],                        'Meningococcal Disease'),
    (['diarrhea', 'diarrhoea', 'rotavirus', 'stool microscopy', 'AGE'], 'Diarrheal Disease'),
    (['hfmd', 'hand, foot', 'hand foot', 'enterovirus', 'coxsackie'],   'Hand, Foot, and Mouth Disease'),
]


def match_disease(raw_text: str) -> str:
    """Return the best matching Confirmed Disease dropdown value, or empty string."""
    t = (raw_text or '').lower()
    for keywords, value in _DISEASE_KEYWORDS:
        for kw in keywords:
            if kw.lower() in t:
                return value
    return ''


# ── Patient cross-validation ─────────────────────────────────────

def _name_tokens(value: str) -> set[str]:
    return {tok for tok in re.sub(r'[^a-z\s]', ' ', (value or '').lower()).split() if len(tok) > 1}


def _fuzzy_name_match(ocr_name: str, case_name: str) -> bool:
    ocr_n = re.sub(r'[^a-z\s]', '', (ocr_name or '').lower())
    case_n = re.sub(r'[^a-z\s]', '', (case_name or '').lower())
    if SequenceMatcher(None, ocr_n, case_n).ratio() >= 0.82:
        return True
    ocr_parts = _name_tokens(ocr_name)
    case_parts = _name_tokens(case_name)
    if not ocr_parts or not case_parts:
        return False
    close = 0
    for ocr_tok in ocr_parts:
        for case_tok in case_parts:
            if ocr_tok == case_tok or (
                min(len(ocr_tok), len(case_tok)) >= 4
                and SequenceMatcher(None, ocr_tok, case_tok).ratio() >= 0.75
            ):
                close += 1
                break
    return close >= 2 or (close == 1 and min(len(ocr_parts), len(case_parts)) <= 2)


def cross_validate_patient(ocr_name: str, case_name: str) -> dict:
    """
    Compare OCR-extracted patient name against the case record name.

    Returns dict with:
      - ``match`` (bool)   — True if names are considered matching
      - ``mismatch`` (bool) — True if definite mismatch detected
      - ``message`` (str)  — human-readable explanation
    """
    def normalize(n):
        return re.sub(r'[^a-z\s]', '', (n or '').lower()).strip()

    ocr_n = normalize(ocr_name)
    case_n = normalize(case_name)

    if not ocr_n:
        return {'match': False, 'mismatch': False, 'message': 'No name extracted from document.'}

    if not case_n or case_n in ('unknown resident', 'case'):
        return {'match': False, 'mismatch': False, 'message': 'No patient name on record to compare.'}

    if ocr_n == case_n:
        return {'match': True, 'mismatch': False, 'message': 'Patient name matches record.'}

    ocr_parts = set(ocr_n.split())
    case_parts = set(case_n.split())
    overlap = ocr_parts & case_parts

    if len(overlap) >= 2 or _fuzzy_name_match(ocr_name, case_name):
        return {'match': True, 'mismatch': False, 'message': 'Patient name matches record (partial match).'}

    if len(overlap) == 1 and (len(ocr_parts) <= 2 or len(case_parts) <= 2):
        return {'match': True, 'mismatch': False, 'message': 'Patient name partially matches record.'}

    return {
        'match': False,
        'mismatch': True,
        'message': 'Scanned document name does not match current patient record.',
    }
