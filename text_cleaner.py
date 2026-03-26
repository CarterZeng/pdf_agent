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
    text = re.sub(r"(?<=[A-Za-z])\s+(?=[A-Za-z])", " ", text)
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
    text = fix_spaced_hyphen_terms(text)
    text = fix_broken_english_words(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def fix_broken_english_words(text: str) -> str:
    if not text:
        return ""

    prev = None
    while prev != text:
        prev = text

        # c ustom -> custom
        text = re.sub(r"\b([A-Za-z])\s+([a-z]{2,})\b", r"\1\2", text)

        # autom a ting -> automating
        text = re.sub(r"\b([A-Za-z]{2,})\s+([a-z]{1,2})\s+([a-z]{2,})\b", r"\1\2\3", text)

        # paper s -> papers
        text = re.sub(r"\b([A-Za-z]{2,})\s+([a-zA-Z])\b", r"\1\2", text)

    return text

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