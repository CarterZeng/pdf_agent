import re
import unicodedata


def normalize_unicode(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = text.replace("\t", " ")
    return text


def remove_page_numbers(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        s = line.strip()
        if re.fullmatch(r"\d{1,4}", s):
            continue
        if re.fullmatch(r"[-–—]?\s*\d{1,4}\s*[-–—]?", s):
            continue
        if re.fullmatch(r"Page\s+\d+(\s+of\s+\d+)?", s, flags=re.I):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def fix_hyphenation(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", text)


def remove_repeated_headers_footers(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        s = line.strip()
        if len(s) < 5:
            cleaned.append(line)
            continue
        if re.fullmatch(r".*(conference|journal|proceedings|copyright).*", s, flags=re.I):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def remove_noise_symbols(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[■□▪▫●○◆◇▶►▼△▲]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def remove_formula_noise(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(RRRR|CCCC|PPPP|FFFF){2,}", " ", text)
    text = re.sub(r"[A-Z]{2,}[=\-−_]{1,}[A-Z]{2,}", " ", text)
    return text


def clean_ocr_spacing(text: str) -> str:
    if not text:
        return ""
    def join_letter_spaced_word(match: re.Match) -> str:
        return match.group(0).replace(" ", "")

    # Only fix OCR-style letter-by-letter spacing like "N e u r a l".
    # Keep normal word boundaries so phrases do not collapse into "approachtoauto".
    text = re.sub(r"\b(?:[A-Za-z]\s+){2,}[A-Za-z]\b", join_letter_spaced_word, text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return text


def truncate_references(text: str) -> str:
    if not text:
        return ""
    patterns = [r"\bReferences\b", r"\bREFERENCE\b", r"参考文献"]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return text[:m.start()].strip()
    return text


def merge_broken_lines(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def clean_for_output(text: str) -> str:
    if not text:
        return ""
    text = normalize_unicode(text)
    text = clean_ocr_spacing(text)
    text = fix_spaced_hyphen_terms(text)
    text = fix_broken_english_words(text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def fix_broken_english_words(text: str) -> str:
    if not text:
        return ""

    # Only repair obvious OCR suffix splits like "label ing" -> "labeling".
    # Avoid joining normal word boundaries such as "a method" or "approach to".
    suffixes = [
        "s", "es", "ed", "er", "ers", "ing", "ion", "ions",
        "ment", "ments", "ness", "less", "ful", "able", "ible",
        "al", "ally", "ly",
    ]
    suffix_pattern = "|".join(suffixes)
    return re.sub(rf"\b([A-Za-z]{{3,}})\s+({suffix_pattern})\b", r"\1\2", text)

def fix_spaced_hyphen_terms(text: str) -> str:
    if not text:
        return ""
    # N -gram -> N-gram
    # full -text -> full-text
    text = re.sub(r"\b([A-Za-z]+)\s*-\s*([A-Za-z]+)\b", r"\1-\2", text)
    return text


def clean_for_index(text: str) -> str:
    text = normalize_unicode(text)
    text = fix_hyphenation(text)
    text = remove_page_numbers(text)
    text = remove_repeated_headers_footers(text)
    text = remove_noise_symbols(text)
    text = remove_formula_noise(text)
    text = clean_ocr_spacing(text)
    text = fix_spaced_hyphen_terms(text)
    text = fix_broken_english_words(text)
    text = truncate_references(text)
    text = merge_broken_lines(text)
    return text.strip()
