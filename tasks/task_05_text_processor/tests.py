"""Test cases for task_05_text_processor."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — basic whitespace normalization (trim + collapse)
    TestCase(
        input={"text": "  hello   world  ", "options": None},
        expected="hello world",
        phase=0, tags=["basic_whitespace"],
    ),
    TestCase(
        input={"text": "no  extra   spaces", "options": None},
        expected="no extra spaces",
        phase=0, tags=["basic_whitespace"],
    ),
    TestCase(
        input={"text": "\t tab \t and \n newline \n", "options": None},
        expected="tab and newline",
        phase=0, tags=["basic_whitespace"],
    ),
    TestCase(
        input={"text": "already clean", "options": None},
        expected="already clean",
        phase=0, tags=["basic_whitespace"],
    ),
    TestCase(
        input={"text": "   ", "options": None},
        expected="",
        phase=0, tags=["basic_whitespace"],
    ),

    # Phase 1 — unicode normalization (NFC)
    # e + combining acute accent -> é
    TestCase(
        input={"text": "caf\u0065\u0301", "options": None},
        expected="caf\u00e9",
        phase=1, tags=["unicode_combining"],
    ),
    TestCase(
        input={"text": "n\u0303o", "options": None},
        expected="\u00f1o",
        phase=1, tags=["unicode_combining"],
    ),
    TestCase(
        input={"text": "  re\u0301sume\u0301  ", "options": None},
        expected="r\u00e9sum\u00e9",
        phase=1, tags=["unicode_combining"],
    ),

    # Phase 2 — preserve whitespace inside double quotes
    # Whitespace inside quotes is NOT collapsed
    TestCase(
        input={"text": 'say  "hello   world"  now', "options": None},
        expected='say "hello   world" now',
        phase=2, tags=["quoted_content"],
    ),
    TestCase(
        input={"text": '"  spaces  "', "options": None},
        expected='"  spaces  "',
        phase=2, tags=["quoted_content"],
    ),
    TestCase(
        input={"text": 'a  "b  c"  d  "e  f"  g', "options": None},
        expected='a "b  c" d "e  f" g',
        phase=2, tags=["quoted_content"],
    ),
    TestCase(
        input={"text": 'no  quotes  here', "options": None},
        expected='no quotes here',
        phase=2, tags=["quoted_content"],
    ),

    # Phase 3 — escape sequences inside quotes become literal chars
    TestCase(
        input={"text": '"hello\\nworld"', "options": None},
        expected='"hello\nworld"',
        phase=3, tags=["escape_handling"],
    ),
    TestCase(
        input={"text": '"tab\\there"', "options": None},
        expected='"tab\there"',
        phase=3, tags=["escape_handling"],
    ),
    TestCase(
        input={"text": 'outside  "in\\nside"  outside', "options": None},
        expected='outside "in\nside" outside',
        phase=3, tags=["escape_handling"],
    ),
    # Escapes outside quotes stay as-is (literal backslash)
    TestCase(
        input={"text": 'no\\nquotes', "options": None},
        expected='no\\nquotes',
        phase=3, tags=["escape_handling"],
    ),

    # Phase 4 — analysis mode returns dict
    TestCase(
        input={"text": "hello world", "options": {"mode": "analyze"}},
        expected={"text": "hello world", "stats": {"words": 2, "chars": 11}},
        phase=4, tags=["analysis_mode"],
    ),
    TestCase(
        input={"text": "  one  ", "options": {"mode": "analyze"}},
        expected={"text": "one", "stats": {"words": 1, "chars": 3}},
        phase=4, tags=["analysis_mode"],
    ),
    TestCase(
        input={"text": '  say  "hi  there"  ', "options": {"mode": "analyze"}},
        expected={"text": 'say "hi  there"', "stats": {"words": 3, "chars": 15}},
        phase=4, tags=["analysis_mode"],
    ),
    # Normal mode still returns string
    TestCase(
        input={"text": "  test  ", "options": {"mode": "normal"}},
        expected="test",
        phase=4, tags=["analysis_mode"],
    ),
    TestCase(
        input={"text": "  test  ", "options": None},
        expected="test",
        phase=4, tags=["analysis_mode"],
    ),

    # Phase 5 — nested quotes: single inside double, escaped quotes
    TestCase(
        input={"text": "he  said  \"it's  fine\"  ok", "options": None},
        expected="he said \"it's  fine\" ok",
        phase=5, tags=["nested_quotes"],
    ),
    TestCase(
        input={"text": '"she said \\"hello\\"  there"', "options": None},
        expected='"she said "hello"  there"',
        phase=5, tags=["nested_quotes"],
    ),
    TestCase(
        input={"text": "plain  'single  quotes'  text", "options": None},
        expected="plain 'single quotes' text",
        phase=5, tags=["nested_quotes"],
    ),

    # Phase 6 — punctuation normalization (collapse consecutive punctuation)
    # But NOT inside quotes
    TestCase(
        input={"text": "wow!!!  great...", "options": None},
        expected="wow! great.",
        phase=6, tags=["punctuation_normalization"],
    ),
    TestCase(
        input={"text": "hmm???  ok!!!", "options": None},
        expected="hmm? ok!",
        phase=6, tags=["punctuation_normalization"],
    ),
    TestCase(
        input={"text": '"keep!!!  these"  but!!!  not', "options": None},
        expected='"keep!!!  these" but! not',
        phase=6, tags=["punctuation_normalization"],
    ),
    TestCase(
        input={"text": "a,,b..c", "options": None},
        expected="a,b.c",
        phase=6, tags=["punctuation_normalization"],
    ),
]
