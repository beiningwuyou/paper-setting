from __future__ import annotations

import re

NUMERIC_CITATION = re.compile(
    r"[\[［【]\s*(\d+(?:\s*[,\uff0c、;；]\s*\d+)+)\s*[\]］】]"
)


def _render_numbers(
    numbers: list[int],
    *,
    collapse_ranges: bool,
    range_separator: str,
) -> str:
    if not collapse_ranges:
        return ", ".join(str(number) for number in numbers)
    groups: list[str] = []
    index = 0
    while index < len(numbers):
        end = index
        while end + 1 < len(numbers) and numbers[end + 1] == numbers[end] + 1:
            end += 1
        if end - index >= 2:
            groups.append(f"{numbers[index]}{range_separator}{numbers[end]}")
        else:
            groups.extend(str(number) for number in numbers[index : end + 1])
        index = end + 1
    return ", ".join(groups)


def normalize_numeric_citations(
    text: str,
    *,
    sort_numbers: bool = True,
    collapse_ranges: bool = True,
    range_separator: str = "–",
) -> str:
    def replace(match: re.Match[str]) -> str:
        values = [int(value) for value in re.split(r"\s*[,\uff0c、;；]\s*", match.group(1))]
        numbers = list(dict.fromkeys(values))
        if sort_numbers:
            numbers.sort()
        return (
            "["
            + _render_numbers(
                numbers,
                collapse_ranges=collapse_ranges,
                range_separator=range_separator,
            )
            + "]"
        )

    return NUMERIC_CITATION.sub(replace, text)


def citation_needs_normalization(text: str) -> bool:
    return normalize_numeric_citations(text) != text
