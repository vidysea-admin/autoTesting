"""Separator characters used to split the canary (names -> char)."""
SEPS = {
    "TAB": "\t", "LF": "\n", "CR": "\r", "CRLF": "\r\n", "VT": "\x0b", "FF": "\x0c", "FS": "\x1c", "US": "\x1f",
    "NEL": "\x85", "LS_2028": " ", "PS_2029": " ", "NBSP": "\xa0", "SPACE": " ", "DOUBLE_SPACE": "  ",
    "IDEOGRAPHIC_SP": "　", "EN_SPACE": " ", "THIN_SPACE": " ", "ZWSP": "​", "ZWNJ": "‌",
    "ZWJ": "‍", "LRM": "‎", "RLM": "‏", "WORD_JOINER": "⁠", "BOM": "﻿",
    "SOFT_HYPHEN": "­", "MONGOLIAN_VS": "᠎", "CGJ": "͏", "ALM": "؜", "NUL": "\x00",
    "BACKSPACE": "\x08", "ESC": "\x1b", "DEL": "\x7f", "TAG_A": "\U000e0041", "VS16": "️",
    "COMBINING_ACUTE": "́", "BACKSLASH": "\\", "QUOTE": '"',
}
