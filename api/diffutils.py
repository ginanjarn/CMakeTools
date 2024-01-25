"""text diff helper"""

import difflib
from typing import Iterator, List


def _get_text_changes(a: str, b: str, n: int = 3) -> Iterator:
    """get text change from a to b with added n delta"""

    # SequenceMatcher requires a and b to be a list
    a = a.split("\n")
    b = b.split("\n")

    for group in difflib.SequenceMatcher(None, a, b).get_grouped_opcodes(n):
        first, last = group[0], group[-1]
        start_line_rm, end_line_rm = first[1], last[2] - 1

        rm_buffer = []
        add_buffer = []

        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for line in a[i1:i2]:
                    rm_buffer.append(line)
                    add_buffer.append(line)
                continue
            if tag in {"replace", "delete"}:
                for line in a[i1:i2]:
                    rm_buffer.append(line)
            if tag in {"replace", "insert"}:
                for line in b[j1:j2]:
                    add_buffer.append(line)

        rm_text = "\n".join(rm_buffer)
        add_text = "\n".join(add_buffer)

        yield {
            "range": {
                "start": {"line": start_line_rm, "character": 0},
                "end": {"line": end_line_rm, "character": len(rm_buffer[-1])},
            },
            "newText": add_text,
            "rangeLength": len(rm_text),
        }


def get_text_changes(src: str, new: str) -> List[dict]:
    """get text changes from srctext to newtext"""
    return list(_get_text_changes(src, new))
