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


# ── Strict Regex Anchor Extraction ───────────────────────────────
#
# Each field is extracted with a dedicated regex that uses lookahead
# boundaries anchored to known neighboring labels.  This prevents
# column-bleeding where OCR line offsets cause values to leak into
# adjacent fields.


def _clean(val: str) -> str:
    """Strip whitespace, trailing punctuation artefacts, and normalize."""
    if not val:
        return ''
    val = val.strip()
    val = val.rstrip('|:;,')
    # collapse internal whitespace runs
    val = re.sub(r'\s+', ' ', val)
    return val.strip()


# ── Field extraction engine ──────────────────────────────────────

def parse_lab_fields(raw_text: str) -> dict:
    """
    Parse all structured fields from OCR-extracted laboratory text
    using strict regex anchor matching with lookahead boundaries.

    Returns a dict with extracted fields (empty string when not found).
    """
    t = raw_text or ''

    # ── Patient Demographics ─────────────────────────────────────

    # Patient Name — stop at Birthday, Age, Nationality, Civil Status, or EOL
    patient_name = ''
    m = re.search(
        r'(?:Patient\s*Name|Patient|Name)\s*[:]\s*'
        r'([A-Za-z\s,.]+?)'
        r'(?=\s*(?:Birthday|Age|Nationality|Civil\s*Status|Date\s*of\s*Birth|Sex|Gender|\n|$))',
        t, re.IGNORECASE
    )
    if m:
        patient_name = _clean(m.group(1))

    # Age + Gender — often on the same line or nearby
    age = ''
    sex = ''
    m = re.search(r'Age\s*[:]\s*(\d+)', t, re.IGNORECASE)
    if m:
        age = m.group(1).strip()
    m = re.search(r'(?:Gender|Sex)\s*[:]\s*([A-Za-z]+)', t, re.IGNORECASE)
    if m:
        sex = _clean(m.group(1))

    # Address — stop at Barangay, City, Province, Email, Phone, Contact, or EOL
    address = ''
    m = re.search(
        r'Address\s*[:]\s*'
        r'([A-Za-z0-9\s,.]+?)'
        r'(?=\s*(?:Barangay|City|Province|Email|Phone|Contact|Municipality|\n|$))',
        t, re.IGNORECASE
    )
    if m:
        address = _clean(m.group(1))
    # If the address regex was too narrow (stopped at Barangay), try a broader capture
    if not address or len(address) < 5:
        m = re.search(
            r'Address\s*[:]\s*(.+?)(?=\s*(?:Email|Phone|Contact|Nationality|Civil\s*Status|\n|$))',
            t, re.IGNORECASE
        )
        if m:
            address = _clean(m.group(1))

    # Also try to append Barangay info if found separately
    m_brgy = re.search(r'Barangay\s*[:]\s*([A-Za-z0-9\s,.]+?)(?=\s*(?:City|Province|Municipality|\n|$))', t, re.IGNORECASE)
    if m_brgy:
        brgy_val = _clean(m_brgy.group(1))
        if brgy_val and brgy_val.lower() not in address.lower():
            address = f"{address}, BARANGAY {brgy_val}" if address else f"BARANGAY {brgy_val}"

    # ── Laboratory Identifiers ───────────────────────────────────

    # Control Number — match LC-YYYY-XXXXXX pattern or anchored extraction
    control_number = ''
    m = re.search(r'(?:Control\s*(?:Number|No\.?)\s*[:]\s*)([A-Za-z0-9\-]+)', t, re.IGNORECASE)
    if m:
        control_number = _clean(m.group(1))
    if not control_number:
        # Fallback: standalone LC-YYYY-XXXXXX pattern anywhere in text
        m = re.search(r'(LC-\d{4}-[A-Za-z0-9]{4,6})', t)
        if m:
            control_number = m.group(1)

    # Lab / Specimen Number — match PORT or similar patterns
    lab_number = ''
    m = re.search(
        r'(?:Lab\s*(?:Number|No\.?)|Specimen\s*(?:ID|Number|No\.?)|Accession\s*(?:No\.?))\s*[:]\s*([A-Za-z0-9\-]+)',
        t, re.IGNORECASE
    )
    if m:
        lab_number = _clean(m.group(1))
    if not lab_number:
        # Fallback: standalone PORT pattern
        m = re.search(r'(PORT\d{6,8}-\d{3,6})', t)
        if m:
            lab_number = m.group(1)

    # Certificate / Issue Date — capture date+time values
    result_date = ''
    m = re.search(
        r'(?:Certificate\s*Issued|Result\s*Date|Date\s*Released|Date\s*Issued)\s*[:]\s*'
        r'([\d/\-\s:APMapm]+)',
        t, re.IGNORECASE
    )
    if m:
        result_date = _clean(m.group(1))
    if not result_date:
        # Fallback: generic "Date:" only if value looks like a date
        m = re.search(r'Date\s*[:]\s*([\d/\-]+(?:\s+[\d:]+(?:\s*[APMapm]+)?)?)', t, re.IGNORECASE)
        if m:
            result_date = _clean(m.group(1))

    # ── Clinical Findings & Interpretation ───────────────────────

    # Lab Results / Findings — capture everything until Interpretation:
    lab_results = ''
    m = re.search(
        r'(?:Test\s*Results?|Result|Findings?)\s*[:]\s*'
        r'([\s\S]*?)'
        r'(?=\s*(?:Interpretation|Diagnostic\s*Impression|Impression|Remarks|$))',
        t, re.IGNORECASE
    )
    if m:
        lab_results = _clean(m.group(1))

    # Interpretation — capture everything until Remarks: or end
    interpretation = ''
    m = re.search(
        r'(?:Interpretation|Diagnostic\s*Impression|Impression)\s*[:]\s*'
        r'([\s\S]*?)'
        r'(?=\s*(?:Remarks|Recommendation|Note|Prepared\s*by|Pathologist|Medical\s*Technologist|$))',
        t, re.IGNORECASE
    )
    if m:
        interpretation = _clean(m.group(1))

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
    (['NS1 Ag & IgG/IgM Combo', 'NS1 Ag', 'IgG/IgM Combo',
      'Dengue NS1', 'NS1 Antigen', 'NS1', 'NS-1'],           'Dengue NS1 Ag & IgG/IgM Combo'),
    (['IgM', 'ELISA', 'IgM ELISA'],                           'IgM ELISA'),
    (['PCR', 'Polymerase', 'RT-PCR', 'RTPCR'],                'PCR'),
    (['Rapid Diagnostic', 'RDT', 'Rapid Test'],                'Rapid Diagnostic Test'),
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
