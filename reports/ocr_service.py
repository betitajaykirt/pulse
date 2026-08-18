"""
OCR service for laboratory result document parsing.

Uses OCR.Space API to extract text, then applies regex-based field
extraction for patient demographics, lab identifiers, and clinical
findings.  Provides keyword matching for Test Type and Confirmed
Disease dropdowns, plus patient-name cross-validation.
"""
import os
import re
import requests
from typing import Optional


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
            'OCREngine': '2',
        }
        files = {'file': (file_obj.name, file_obj.read(), file_obj.content_type)}
        resp = requests.post(api_url, data=payload, files=files, timeout=30)
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


# ── Regex helpers ────────────────────────────────────────────────

def _extract_after(text: str, anchors: list[str], multiline: bool = False) -> str:
    """Return the value that follows any of the given anchors (case-insensitive)."""
    for anchor in anchors:
        pattern = re.escape(anchor) + r'\s*(.+)'
        flags = re.IGNORECASE | (re.DOTALL if multiline else 0)
        m = re.search(pattern, text, flags)
        if m:
            val = m.group(1).strip()
            # For single-line extractions, trim at the next newline
            if not multiline:
                val = val.split('\n')[0].strip()
            # Clean trailing punctuation artefacts
            val = val.rstrip('|:;,')
            return val.strip()
    return ''


def _extract_block(text: str, anchors: list[str]) -> str:
    """
    Extract a multi-line text block following an anchor heading.

    Captures everything from the anchor to the next section heading
    or end of text.
    """
    for anchor in anchors:
        pattern = re.escape(anchor) + r'\s*[:\-]?\s*\n?([\s\S]+?)(?=\n\s*[A-Z][a-z]+\s*[:\-]|\Z)'
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            block = m.group(1).strip()
            # Also try inline (same line) if block is empty
            if not block:
                inline = _extract_after(text, [anchor])
                if inline:
                    return inline
            return block
    return ''


# ── Field extraction engine ──────────────────────────────────────

def parse_lab_fields(raw_text: str) -> dict:
    """
    Parse all structured fields from OCR-extracted laboratory text.

    Returns a dict with extracted fields (empty string when not found).
    """
    t = raw_text or ''

    # ── Patient Demographics ──
    patient_name = _extract_after(t, ['Patient Name:', 'Patient:', 'Name:'])
    age = _extract_after(t, ['Age:'])
    sex = _extract_after(t, ['Sex:', 'Gender:'])
    address = _extract_after(t, ['Address:', 'Barangay:', 'City:'])

    # ── Lab Identifiers ──
    control_number = _extract_after(t, ['Control Number:', 'Control No:', 'Control No.:'])
    if not control_number:
        m = re.search(r'LC-\d{4}-\d{4,6}', t)
        if m:
            control_number = m.group(0)

    lab_number = _extract_after(t, [
        'Lab Number:', 'Lab No:', 'Lab No.:',
        'Specimen ID:', 'Specimen No:', 'Specimen No.:',
        'Accession No:', 'Accession No.:',
    ])

    result_date = _extract_after(t, [
        'Certificate Issued:', 'Result Date:', 'Date Released:', 'Date Issued:',
    ])
    if not result_date:
        # Fallback: generic "Date:" but only if it looks like a date value
        date_candidate = _extract_after(t, ['Date:'])
        if date_candidate and re.search(r'\d', date_candidate):
            result_date = date_candidate

    # ── Clinical Findings ──
    lab_results = _extract_after(t, ['Test Results:', 'Test Result:', 'Result:', 'Findings:'])
    if not lab_results:
        lab_results = _extract_block(t, ['Test Results:', 'Test Result:', 'Result:', 'Findings:'])

    interpretation = _extract_after(t, ['Interpretation:', 'Diagnostic Impression:', 'Impression:'])
    if not interpretation:
        interpretation = _extract_block(t, ['Interpretation:', 'Diagnostic Impression:', 'Impression:'])

    return {
        'patient_name': patient_name,
        'age': age,
        'sex': sex,
        'address': address,
        'control_number': control_number,
        'lab_number': lab_number,
        'result_date': result_date,
        'lab_results': lab_results,
        'interpretation': interpretation,
    }


# ── Test Type keyword matching ───────────────────────────────────

_TEST_TYPE_KEYWORDS: list[tuple[list[str], str]] = [
    (['NS1', 'NS-1', 'NS1 Antigen'],                    'NS1 Antigen'),
    (['IgM', 'ELISA', 'IgM ELISA'],                     'IgM ELISA'),
    (['PCR', 'Polymerase', 'RT-PCR', 'RTPCR'],          'PCR'),
    (['Rapid Diagnostic', 'RDT', 'Rapid Test'],          'Rapid Diagnostic Test'),
    (['Culture', 'Blood Culture', 'Stool Culture'],      'Culture'),
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

    # Exact match
    if ocr_n == case_n:
        return {'match': True, 'mismatch': False, 'message': 'Patient name matches record.'}

    # Token overlap: if at least 2 name parts match, consider it a match
    ocr_parts = set(ocr_n.split())
    case_parts = set(case_n.split())
    overlap = ocr_parts & case_parts

    if len(overlap) >= 2:
        return {'match': True, 'mismatch': False, 'message': 'Patient name matches record (partial match).'}

    if len(overlap) == 1 and (len(ocr_parts) <= 2 or len(case_parts) <= 2):
        return {'match': True, 'mismatch': False, 'message': 'Patient name partially matches record.'}

    return {
        'match': False,
        'mismatch': True,
        'message': 'Scanned document name does not match current patient record.',
    }
