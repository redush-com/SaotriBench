"""Test cases for task_03_validate_brackets."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — round brackets only
    TestCase(input="()", expected=True, phase=0, tags=["round_only"]),
    TestCase(input="(())", expected=True, phase=0, tags=["round_only"]),
    TestCase(input="()()", expected=True, phase=0, tags=["round_only"]),
    TestCase(input="((()))", expected=True, phase=0, tags=["round_only"]),
    TestCase(input="(", expected=False, phase=0, tags=["round_only"]),
    TestCase(input=")", expected=False, phase=0, tags=["round_only"]),
    TestCase(input=")(", expected=False, phase=0, tags=["round_only"]),
    TestCase(input="(()", expected=False, phase=0, tags=["round_only"]),

    # Phase 1 — mixed bracket types: (), [], {}
    TestCase(input="[()]", expected=True, phase=1, tags=["mixed_brackets"]),
    TestCase(input="{[()]}", expected=True, phase=1, tags=["mixed_brackets"]),
    TestCase(input="()[]{}", expected=True, phase=1, tags=["mixed_brackets"]),
    TestCase(input="{[(())]}", expected=True, phase=1, tags=["mixed_brackets"]),
    TestCase(input="[)", expected=False, phase=1, tags=["mixed_brackets"]),
    TestCase(input="{(]}", expected=False, phase=1, tags=["mixed_brackets"]),
    TestCase(input="([)]", expected=False, phase=1, tags=["mixed_brackets"]),
    TestCase(input="{[}", expected=False, phase=1, tags=["mixed_brackets"]),

    # Phase 2 — whitespace handling and empty input
    TestCase(input="", expected=True, phase=2, tags=["empty_input"]),
    TestCase(input="  ", expected=True, phase=2, tags=["whitespace"]),
    TestCase(input="( )", expected=True, phase=2, tags=["whitespace"]),
    TestCase(input="[ ( ) ]", expected=True, phase=2, tags=["whitespace"]),
    TestCase(input=" { [ ] } ", expected=True, phase=2, tags=["whitespace"]),
    TestCase(input="(  ]", expected=False, phase=2, tags=["whitespace"]),

    # Phase 3 — ValueError with position for invalid inputs
    # (valid inputs still return True, invalid ones raise ValueError)
    TestCase(input="(([]))", expected=True, phase=3, tags=["round_only"]),
    TestCase(input="(]", expected=False, phase=3, tags=["error_position"]),
    TestCase(input="({[}])", expected=False, phase=3, tags=["error_position"]),
    TestCase(input="((((", expected=False, phase=3, tags=["error_position"]),
    TestCase(input="]", expected=False, phase=3, tags=["error_position"]),

    # Phase 4 — regression testing with complex edge cases
    TestCase(input="([{}]){()}", expected=True, phase=4, tags=["interleaved_brackets"]),
    TestCase(input="((", expected=False, phase=4, tags=["missing_closure"]),
    TestCase(input="))", expected=False, phase=4, tags=["early_closure"]),
    TestCase(input="{[}]", expected=False, phase=4, tags=["early_closure"]),
    TestCase(input="[{}](", expected=False, phase=4, tags=["missing_closure"]),
]
