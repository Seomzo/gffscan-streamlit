import re

def normalize_part_number(part_num: str) -> str:
    """
    Convert to uppercase, remove spaces/dashes, etc. for consistent matching.
    e.g. "N-908-514-01" -> "N90851401"
    """
    return re.sub(r"[\s\-]+", "", part_num.upper())

def extract_required_parts(snippet_text: str) -> set:
    """
    Parse each bullet line to find the part number.
    Lines look like:
      "- N 105 524 04 / Engine Mount Bolt / 2"
    We'll take everything before the first slash as the part number,
    then normalize it.
    """
    part_pattern = re.compile(r"^\s*-\s+(.+)$", re.MULTILINE)
    lines = part_pattern.findall(snippet_text)
    required = set()

    for line in lines:
        tokens = line.split("/")
        if tokens:
            raw_part = tokens[0].strip()
            norm = normalize_part_number(raw_part)
            required.add(norm)
    return required

def build_snippets_dict(SNIPPETS: dict) -> dict:
    """
    Given the SNIPPETS dictionary from onetime_use_parts.py,
    return a dict {snippet_key -> set_of_required_parts}
    """
    snippet_parts = {}
    for key, text in SNIPPETS.items():
        snippet_parts[key] = extract_required_parts(text)
    return snippet_parts

def find_best_snippet_for_parts(replaced_parts: list, snippet_parts_map: dict):
    """
    replaced_parts: e.g. ["N-908-514-01", "N-911-455-02", ...]
    snippet_parts_map: {snippet_key -> set_of_required_parts}

    returns (best_snippet_key, overlap_count)
    """
    replaced_set = set(normalize_part_number(rp) for rp in replaced_parts)
    best_key = None
    best_overlap = 0

    for snippet_key, required_set in snippet_parts_map.items():
        overlap = replaced_set.intersection(required_set)
        if len(overlap) > best_overlap:
            best_overlap = len(overlap)
            best_key = snippet_key

    return best_key, best_overlap