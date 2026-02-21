"""
extractor.py
------------
Extracts well info and stimulation data from text files produced by pdf2txt.py.
"""

import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Compiled regex constants
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")

_API_DIGITS_RE = re.compile(r"\b(\d{10})\b")
_API_LABELLED_RE = re.compile(
    r"\bAPI\s*(?:No\.?|#|Number)?\s*[:\s]?\s*([\d\-OIli]{8,15})", re.I
)
_OCR_DIGIT_TABLE = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "i": "1"})

_NUM_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")

_WELL_NAME_LABEL_RE = re.compile(r"Well\s+(?:or\s+Facility\s+)?Name\s+(?:and\s+Number)?", re.I)

# Lines that are noise/form-headers — never a well name
_NOISE_LINE_RE = re.compile(
    r"""
    \b(?:Telephone|Phone|Fax|Email|Address|City|State|Zip|County|Field|Pool|
         Township|Range|Section|Footage|Qtr|Datum|Operator|FOR\s+STATE\s+USE|
         PLEASE\s+READ|SUBMIT|Notice\s+of|Report\s+of|Drilling\s+Prognosis|
         Casing|Plug\s+Well|Fracture|Redrilling|Shooting|Acidizing|
         Reclamation|Workover|Tax\s+Exemption|NDCC|
         INDUSTRIAL\s+COMMISSION|OIL\s+AND\s+GAS|BISMARCK|BOULEVARD|
         SUNDRY|NOTICES|REPORTS|FORM\s+\d|24-HOUR\s+PRODUCTION)\b
    """,
    re.I | re.X,
)
_SFN_RE = re.compile(r"^SFN\s+\d", re.I)
_COMPANY_SUFFIX_RE = re.compile(
    r"\b(?:LLC|Inc\.?|Corp\.?|Ltd\.?|L\.P\.?|LLP|Co\.?|Company|"
    r"Corporation|Incorporated|Limited|Partnership|Operating)\b",
    re.I,
)

# Stimulation table patterns
_STIM_HEADER_RE = re.compile(r"Well\s+Spec\w*\s+Stimulation|Date\s+Stimulated", re.I)
_TYPE_HEADER_RE = re.compile(r"Type\s+Treatment|Lbs\s+Proppant|Maximum\s+Treatment", re.I)
_STOP_SECTION_RE = re.compile(
    r"ADDITIONAL INFORMATION|I hereby swear|DETAILS OF WORK|^DATE\b", re.I
)

# Volume units
_UNIT_RE = re.compile(r"\b(Barrels?|BBL[Ss]?|MCF)\b", re.I)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _preprocess(text: str) -> str:
    t = (
        text.replace("\u2011", "-").replace("\u2013", "-")
            .replace("\u2014", "-").replace("\xa0", " ")
    )
    return re.sub(r"[ \t]{2,}", " ", t)


def _split_pages(text: str) -> list[str]:
    parts = re.split(r"=== PAGE \d+ ===", text)
    return [p.strip() for p in parts if p.strip()]


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _ocr_fix_digits(s: str) -> str:
    return s.translate(_OCR_DIGIT_TABLE)


def _format_api(digits: str) -> Optional[str]:
    if len(digits) < 10:
        return None
    d = digits[:10]
    return f"{d[0:2]}-{d[2:5]}-{d[5:10]}"


def _parse_number(tok: str) -> Optional[int | float]:
    t = tok.replace(",", "")
    try:
        return float(t) if "." in t else int(t)
    except ValueError:
        return None


def _norm_unit(s: str) -> str:
    s = s.upper()
    if "MCF" in s:
        return "MCF"
    return "Barrels"


# ---------------------------------------------------------------------------
# Well-name extraction
# ---------------------------------------------------------------------------

# Trailing noise patterns that bleed in from adjacent OCR columns
_TRAILING_QTR_RE = re.compile(
    r"\s+(?:[NS][EW][NS][EW]|[NS][EW]\s+[NS][EW]|LOT\s*\d|\d{1,3}\s+[NS]\s+\d{1,3}(?:\s+[EW])?|\d{1,3}\s+[NS]\s+\d{1,3}).*$"
)
# Strip bare section/township/range numbers that trail after the well number
# e.g. "Basic Game & Fish 34-3 2 153 N 101"
_TRAILING_LOCATION_RE = re.compile(
    r"\s+\d{1,3}\s+\d{1,3}\s+[NS]\s+\d{1,3}.*$"  # <section> <township> N/S <range>
)
_TRAILING_COUNTY_RE = re.compile(
    r"\s+(?:McKenzie|Williams|Mountrail|Divide|Burke|Bottineau|Ward|Dunn|Billings|Stark|"
    r"Renville|McLean|Mercer|Morton|Grant|Adams|Hettinger|Bowman|Slope|Sioux|Emmons|"
    r"Oliver|Golden\s+Valley|County)\b.*$",
    re.I,
)


def _clean_well_name(name: str) -> str:
    """Strip label prefix and trailing OCR noise from a candidate well name."""
    # Remove leading labels
    name = re.sub(r"^\s*(?:Well\s+(?:or\s+Facility\s+)?Name(?:\s+and\s+Number)?)\s*[:\-]+\s*", "", name, flags=re.I)
    name = name.strip()
    # Cut at pipe/bracket garbage
    m = re.search(r"[|\[\]{}@$%^*+=~`<>]", name)
    if m:
        name = name[:m.start()]

    # Cut off OCR/Trailing garbage
    name = re.sub(r"\s+[-\.]{3,}.*$", "", name)
    name = _TRAILING_LOCATION_RE.sub("", name)
    name = _TRAILING_QTR_RE.sub("", name)
    name = _TRAILING_COUNTY_RE.sub("", name)

    # Strip trailing punctuation/noise words (those without digits)
    tokens = name.split()
    while len(tokens) > 1:
        last = tokens[-1]
        if re.search(r"\d", last):
            break
        # keep known well-type suffixes
        if re.match(r"^(?:SWD|WD|WI|HR?|TXR?|ST|TA|CBM|H|T|B)$", last, re.I):
            break
        # At least one digit in the remaining tokens
        if not re.search(r"\d", " ".join(tokens[:-1])):
            break
        tokens = tokens[:-1]
    return " ".join(tokens).strip(" \t\n\r-;,.|")


def _is_well_name(line: str) -> bool:
    """
    Returns True if line looks like a well name:
    - Starts with an English word (2+ ENG chars)
    - Contains a number component (possibly hyphenated like 34-3H, 41-12T)
    - Is not a form header, company name, or noise line
    """
    line = line.strip()
    if not line or len(line) > 100:
        return False
    if _SFN_RE.match(line):
        return False
    if _NOISE_LINE_RE.search(line):
        return False
    if _COMPANY_SUFFIX_RE.search(line):
        return False
    if _DATE_RE.search(line):
        return False
    
    # 3 exclude conditions that mentioned above
    if not re.match(r"[A-Z][A-Za-z]", line):
        return False
    if not re.search(r"[A-Za-z]{2,}", line):
        return False
    if not re.search(r"\d", line):
        return False

    return True


def _extract_well_name(pages: list[str]) -> Optional[str]:
    """
    Try 2 strategies, ideally the first one should work
    Strategy 1: find "Well Name and Number" label -> grab the next non-empty
    line (skipping known column headers). Returns immediately if found.

    Strategy 2: page-wide scan for any line matching the well-name pattern
    that contains a hyphenated number like 34-3H.
    """
    # Strategy 1
    for page in pages:
        lines = [ln.rstrip() for ln in page.splitlines()]
        for i, ln in enumerate(lines):
            if _WELL_NAME_LABEL_RE.search(ln):

                # check inline
                after = _WELL_NAME_LABEL_RE.split(ln, maxsplit=1)[-1].strip(" :-")
                if after and _is_well_name(after):
                    return _clean_well_name(after)
                
                # scan next few lines
                for j in range(i + 1, min(len(lines), i + 6)):
                    candidate = lines[j].strip()
                    if not candidate:
                        continue
                    # Skip column-header continuation lines
                    if re.match(r"^(?:Footages?|Qtr|Section|Township|Range|County|Field|Pool|24-HOUR)", candidate, re.I):
                        continue
                    if _is_well_name(candidate):
                        return _clean_well_name(candidate)
                    break

    # Strategy 2
    for page in pages:
        for ln in page.splitlines():
            candidate = ln.strip()
            if not candidate:
                continue
            if not re.search(r"[A-Za-z]{2,}.*\d{1,4}-\d{1,3}[A-Za-z0-9]?", candidate):
                continue
            if re.search(r"Well\s+File\b", candidate, re.I):
                continue
            if _is_well_name(candidate):
                cleaned = _clean_well_name(candidate)
                if cleaned and re.search(r"\d", cleaned):
                    return cleaned

    return None


# ---------------------------------------------------------------------------
# API extraction
# ---------------------------------------------------------------------------

def _extract_api(text: str) -> Optional[str]:
    """
    Try 4 strategies to extract API number
    """
    # 1 — labelled API
    for m in _API_LABELLED_RE.finditer(text):
        span_start = max(0, m.start() - 80)
        context = text[span_start: m.end() + 80]
        if re.search(r"Well\s+File\b", context, re.I):
            continue
        nearby = text[span_start: m.end() + 80]
        well_name_count = len(re.findall(r"\d{1,3}-\d{1,3}[A-Za-z0-9]?", nearby))
        if well_name_count > 1:
            continue
        raw = _ocr_fix_digits(m.group(1))
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 10:
            return _format_api(digits[:10])

    # 2 — formatted XX-XXX-XXXXX
    for m in re.finditer(r"\b(\d{2})-(\d{3})-(\d{5})\b", text):
        digits = m.group(1) + m.group(2) + m.group(3)
        return _format_api(digits)

    # 3 — bare 10-digit run
    fixed = _ocr_fix_digits(text)
    for m in _API_DIGITS_RE.finditer(fixed):
        digits = m.group(1)
        state = int(digits[:2])
        if 1 <= state <= 56:
            return _format_api(digits)

    # 4 — spaced/dashed API
    m = re.search(r"(\d{2})\s*[- ]\s*(\d{3})\s*[- ]\s*(\d{5})", text)
    if m:
        digits = m.group(1) + m.group(2) + m.group(3)
        return _format_api(digits)

    return None


# ---------------------------------------------------------------------------
# Operator extraction
# ---------------------------------------------------------------------------

def _extract_operator(text: str) -> Optional[str]:
    _PHONE_STRIP_RE = re.compile(
        r"\s+(?:Rig|Telephone|Phone)?[:\s]*\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}.*$"
    )

    def clean(s: str) -> str:
        return _PHONE_STRIP_RE.sub("", s).strip()

    def looks_like_company(s: str) -> bool:
        if not s or not s[0].isupper():
            return False
        if _NOISE_LINE_RE.search(s):
            return False
        return bool(re.search(r"[A-Za-z]{3,}", s))

    # Pattern 1: "Operator: <company>"
    for m in re.finditer(r"\bOperator\b\s*:\s*(.+)", text, re.I):
        val = clean(m.group(1)).split("  ")[0].strip()
        if val and looks_like_company(val):
            return val

    # Pattern 2: "Operator" standalone label -> next non-empty line
    for m in re.finditer(r"^[ \t]*Operator[ \t]*$", text, re.I | re.M):
        for line in text[m.end():].splitlines():
            line = line.strip()
            if line and looks_like_company(line):
                return clean(line)
            if line:
                break

    # Pattern 2b: "Operator" followed by other column headers on same line →
    # company is on the very next non-empty line
    for m in re.finditer(r"^[ \t]*Operator\b[^\n]+", text, re.I | re.M):
        if ":" in m.group(0):
            continue  # handled by Pattern 1
        for line in text[m.end():].splitlines():
            line = line.strip()
            if line and looks_like_company(line):
                return clean(line)
            if line:
                break

    # Pattern 3: company+phone inline (1+ spaces before phone)
    for m in re.compile(r"^(.+?)\s+\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}", re.M).finditer(text):
        candidate = m.group(1).strip()
        if looks_like_company(candidate) and not re.search(r"\bOperator\b", candidate, re.I):
            return candidate

    return None


# ---------------------------------------------------------------------------
# Stimulation data extraction
# ---------------------------------------------------------------------------

def _empty_stim() -> dict:
    return {k: None for k in [
        "date_stimulated", "stimulated_formation", "top_ft", "bottom_ft",
        "stimulated_in", "stimulation_stages", "volume", "volume_units",
        "type_treatment", "acid_pct", "lbs_proppant",
        "max_treatment_pressure_psi", "max_treatment_rate_bbls_min", "details",
    ]}


def _extract_stimulation_data(pages: list[str]) -> dict:
    """
    Find the Well Specific Stimulations table and parse the first populated row.

    Table structure (two header rows, OCR may mangle them):
      Row-header-1: Date Stimulated | Stimulated Formation | Top (Ft) | Bottom (Ft) | Stimulation Stages | Volume | Volume Units
      Data-row-1:   <date>          | <formation>          | <top>    | <bottom>    | <stages>           | <vol>  | <units>
      Row-header-2: Type Treatment | Acid% | Lbs Proppant | Maximum Treatment Pressure (PSI) | Maximum Treatment Rate (BBLS/Min)
      Data-row-2:   <type>         |       | <lbs>        | <psi>                            | <rate>
      Details:      <free text>
    """
    # Find page with stimulation section
    stim_page = None
    for p in pages:
        if _STIM_HEADER_RE.search(p):
            stim_page = p
            break
    if stim_page is None:
        return _empty_stim()

    lines = [ln.rstrip() for ln in stim_page.splitlines()]

    # Find the header line index
    header_idx = next((i for i, ln in enumerate(lines) if _STIM_HEADER_RE.search(ln)), None)
    if header_idx is None:
        return _empty_stim()

    # Skip header/label continuation lines to find first data row
    _COL_LABEL_RE = re.compile(
        r"^[\s\|]*(?:Date\s+Stimulated|Stimulated\s+Formation|Top\s*\(?Ft|Bottom\s*\(?Ft|"
        r"Stimulation\s+Stages|Volume|Type\s+Treatment|Lbs\s+Proppant|Maximum\s+Treatment|Acid\s*%)",
        re.I,
    )

    def next_data(start: int) -> Optional[int]:
        """
        Return the index of the candidate date row
        """
        for j in range(start, len(lines)):
            ln = lines[j].strip()
            if ln and not _STIM_HEADER_RE.search(ln) and not _COL_LABEL_RE.match(lines[j]):
                return j
        return None

    candidate_idx1 = next_data(header_idx + 1)
    if candidate_idx1 is None:
        return _empty_stim()
    row1 = lines[candidate_idx1].strip()

    # Find the type-treatment sub-header and data row
    type_hdr_idx = next(
        (j for j in range(candidate_idx1 + 1, min(len(lines), candidate_idx1 + 10)) if _TYPE_HEADER_RE.search(lines[j])),
        None,
    )
    candidate_idx2 = None
    if type_hdr_idx is not None:
        candidate_idx2 = next((j for j in range(type_hdr_idx + 1, len(lines)) if lines[j].strip()), None)
    elif candidate_idx1 is not None: # Sometimes the type-treatment header is missing or OCR-mangled
        candidate_idx2 = next((j for j in range(candidate_idx1 + 1, len(lines)) if lines[j].strip()), None)
    row2 = lines[candidate_idx2].strip() if candidate_idx2 is not None else ""

    # Details lines after row2
    details_lines = []
    details_line_cnt = 0
    if candidate_idx2 is not None:
        k = candidate_idx2 + 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        if k < len(lines) and re.match(r"^\s*Details?\b", lines[k], re.I):
            k += 1
        while k < len(lines):
            ln = lines[k].strip()
            if not ln or _STOP_SECTION_RE.search(ln) or _COL_LABEL_RE.match(lines[k]) or details_line_cnt >3:
                break
            details_lines.append(ln)
            details_line_cnt += 1
            k += 1

    # ---- Parse row1: date | formation | top | bottom | stages | volume | units ----
    date_stimulated = None
    stimulated_formation = None
    top_ft = None
    bottom_ft = None
    stimulated_in = None
    stimulation_stages = None
    volume = None
    volume_units = None

    if row1:
        # Date: first date pattern
        dm = _DATE_RE.search(row1)
        if dm:
            date_stimulated = dm.group(1)
            remaining = row1[dm.end():].strip(" |")
        else:
            # No date found — treat whole row as remaining
            remaining = row1

        # Extract all numbers from remaining
        nums = [m.group(0) for m in _NUM_RE.finditer(remaining)]
        # Depths: 3-6 digit integers
        depth_nums = [n for n in nums if re.fullmatch(r"\d{3,6}", n)]

        # Formation: text before the first depth number
        if depth_nums:
            pos0 = remaining.find(depth_nums[0])
            form_raw = remaining[:pos0].strip(" |,-")
            if form_raw:
                stimulated_formation = re.sub(r"[\d\|\-\/\(\)\[\]\:]+", " ", form_raw).strip() or None

        if len(depth_nums) >= 2:
            top_ft = _parse_number(depth_nums[0])
            bottom_ft = _parse_number(depth_nums[1])
            pos1 = remaining.find(depth_nums[1],remaining.find(depth_nums[0]) + len(depth_nums[0]))
            after = remaining[pos1 + len(depth_nums[1]):].strip(" |") if pos1 >= 0 else ""
            after_nums = [m.group(0) for m in _NUM_RE.finditer(after)]
            if after_nums:
                v0 = _parse_number(after_nums[0])
                # stages are typically small (<1000), volume large
                if isinstance(v0, int) and v0 < 1000:
                    stimulation_stages = v0
                    if len(after_nums) >= 2:
                        volume = _parse_number(after_nums[1])
                else:
                    volume = v0
            um = _UNIT_RE.search(after)
            if um:
                volume_units = _norm_unit(um.group(1))

        elif len(depth_nums) == 1:
            top_ft = _parse_number(depth_nums[0])
            pos0 = remaining.find(depth_nums[0])
            after = remaining[pos0 + len(depth_nums[0]):].strip(" |")
            after_nums = [m.group(0) for m in _NUM_RE.finditer(after)]
            for ns in after_nums:
                v = _parse_number(ns)
                if isinstance(v, int) and v >= 1000:
                    volume = v
                    break
            um = _UNIT_RE.search(after)
            if um:
                volume_units = _norm_unit(um.group(1))

        else:
            # No depths — try volume directly
            vm = re.search(r"(\d{1,3}(?:,\d{3})+)\s*(?:Barrels?|BBL[Ss]?|MCF)\b", row1, re.I)
            if vm:
                volume = _parse_number(vm.group(1))
                um = _UNIT_RE.search(row1[vm.start():])
                if um:
                    volume_units = _norm_unit(um.group(1))

        # Stimulated in (Cased/Open Hole)
        si = re.search(r"\b(Cased\s+Hole|Open\s+Hole)\b", row1, re.I)
        if si:
            stimulated_in = si.group(1)

    # ---- Parse row2: type | acid% (empty) | lbs | pressure | rate ----
    type_treatment = None
    acid_pct = None # often empty
    lbs_proppant = None
    max_pressure = None
    max_rate = None

    if row2:
        nums2 = [m.group(0) for m in _NUM_RE.finditer(row2)]
        # type_treatment = text before the first number
        if nums2:
            pos = row2.find(nums2[0])
            before = row2[:pos].strip(" |:,-")
            type_treatment = before or None
        else:
            type_treatment = row2.strip() or None

        # Map numbers left-to-right: [acid_pct, lbs_proppant, max_pressure, max_rate]
        # Acid% is almost always empty/missing, just neglect it.
        targets = ["lbs_proppant", "max_pressure", "max_rate"]
        ti = 0
        for tok in nums2:
            if ti >= len(targets):
                break
            val = _parse_number(tok)
            t = targets[ti]
            if t == "lbs_proppant":
                lbs_proppant = int(val) if isinstance(val, (int, float)) else None
            elif t == "max_pressure":
                max_pressure = int(val) if isinstance(val, (int, float)) else None
            elif t == "max_rate":
                max_rate = float(val) if isinstance(val, (int, float)) else None
            ti += 1

    return {
        "date_stimulated":             date_stimulated,
        "stimulated_formation":        stimulated_formation,
        "top_ft":                      top_ft,
        "bottom_ft":                   bottom_ft,
        "stimulated_in":               stimulated_in,
        "stimulation_stages":          stimulation_stages,
        "volume":                      volume,
        "volume_units":                volume_units,
        "type_treatment":              type_treatment,
        "acid_pct":                    acid_pct,
        "lbs_proppant":                lbs_proppant,
        "max_treatment_pressure_psi":  max_pressure,
        "max_treatment_rate_bbls_min": max_rate,
        "details":                     "\n".join(details_lines) if details_lines else None,
    }


# ---------------------------------------------------------------------------
# Well info extraction
# ---------------------------------------------------------------------------

def _extract_well_info(pages: list[str], full_text: str) -> dict:
    collapsed = _collapse(full_text)

    well_name = _extract_well_name(pages)
    api = _extract_api(full_text)

    # Operator: prefer page with "Well Name and Number" label
    form_page = next((p for p in pages if _WELL_NAME_LABEL_RE.search(p)), None)
    operator = _extract_operator(form_page or full_text)

    # County/State
    county_state = None
    m = re.search(r"([A-Z][A-Za-z]+\s+County,\s+[A-Za-z\s]+?)(?:\n|$)", full_text)
    if m:
        county_state = m.group(1).strip()
    if not county_state:
        m = re.search(r"County\s*[/,]?\s*State\s*[:\-]?\s*(.+)", full_text, re.I)
        if m:
            county_state = m.group(1).strip()

    # Coordinates
    lat = (
        re.search(r"Lat(?:itude)?\s*[:\-]?\s*([\d]+°\s*[\d]+[\'′][\d\.]+[\"″]?\s*[NS]?)", collapsed, re.I)
        or re.search(r"Lat(?:itude)?\s*[:\-]?\s*([-+]?[1-8]?\d\.\d{4,})", collapsed, re.I)
    )
    lon = (
        re.search(r"Lon(?:g(?:itude)?)?\s*[:\-]?\s*([\d]+°\s*[\d]+[\'′][\d\.]+[\"″]?\s*[EW]?)", collapsed, re.I)
        or re.search(r"Lon(?:g(?:itude)?)?\s*[:\-]?\s*([-+]?(?:1[0-7]\d|\d{1,2})\.\d{4,})", collapsed, re.I)
    )

    datum = re.search(r"\bDatum\s*[:\-]?\s*([^\n]+)", full_text, re.I)

    return {
        "well_name_and_number": well_name or "",
        "api":                  api or "",
        "operator":             operator,
        "county_state":         county_state,
        "datum":                datum.group(1).strip() if datum else None,
        "latitude":             lat.group(1).strip() if lat else None,
        "longitude":            lon.group(1).strip() if lon else None,
    }


# ---------------------------------------------------------------------------
# Public Extractor class
# ---------------------------------------------------------------------------

class Extractor:
    def __init__(self, txt_folder: str = "./raw-txt"):
        self.folder = Path(txt_folder)

    def extract_txt(self, txt_path: Path) -> dict:
        raw = txt_path.read_text(encoding="utf-8")
        text = _preprocess(raw)
        pages = _split_pages(text)
        return {
            "file":             txt_path.name,
            "well_info":        _extract_well_info(pages, text),
            "stimulation_data": _extract_stimulation_data(pages),
        }

    def extract_all(self) -> list[dict]:
        results = []
        for txt in sorted(self.folder.glob("*.txt")):
            try:
                result = self.extract_txt(txt)
                results.append(result)
                print("Extracted:", txt.name)
            except Exception as e:
                print("Failed:", txt.name, "|", e)
        return results