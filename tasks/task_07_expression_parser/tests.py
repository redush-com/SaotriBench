"""Test cases for task_07_expression_parser."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — basic + and -
    TestCase(input={"expression": "2 + 3", "variables": None}, expected=5.0, phase=0, tags=["basic_arithmetic"]),
    TestCase(input={"expression": "10 - 4", "variables": None}, expected=6.0, phase=0, tags=["basic_arithmetic"]),
    TestCase(input={"expression": "1 + 2 + 3", "variables": None}, expected=6.0, phase=0, tags=["basic_arithmetic"]),
    TestCase(input={"expression": "100 - 50 + 25", "variables": None}, expected=75.0, phase=0, tags=["basic_arithmetic"]),

    # Phase 1 — * and / with precedence
    TestCase(input={"expression": "2 + 3 * 4", "variables": None}, expected=14.0, phase=1, tags=["precedence"]),
    TestCase(input={"expression": "10 / 2 + 3", "variables": None}, expected=8.0, phase=1, tags=["precedence"]),
    TestCase(input={"expression": "2 * 3 + 4 * 5", "variables": None}, expected=26.0, phase=1, tags=["precedence"]),
    TestCase(input={"expression": "12 / 4 / 3", "variables": None}, expected=1.0, phase=1, tags=["precedence"]),

    # Phase 2 — parentheses
    TestCase(input={"expression": "(2 + 3) * 4", "variables": None}, expected=20.0, phase=2, tags=["grouping"]),
    TestCase(input={"expression": "((1 + 2) * (3 + 4))", "variables": None}, expected=21.0, phase=2, tags=["grouping"]),
    TestCase(input={"expression": "10 / (2 + 3)", "variables": None}, expected=2.0, phase=2, tags=["grouping"]),
    TestCase(input={"expression": "(((5)))", "variables": None}, expected=5.0, phase=2, tags=["grouping"]),

    # Phase 3 — unary minus
    TestCase(input={"expression": "-5", "variables": None}, expected=-5.0, phase=3, tags=["unary_operator"]),
    TestCase(input={"expression": "-(3 + 2)", "variables": None}, expected=-5.0, phase=3, tags=["unary_operator"]),
    TestCase(input={"expression": "2 + -3", "variables": None}, expected=-1.0, phase=3, tags=["unary_operator"]),
    TestCase(input={"expression": "--5", "variables": None}, expected=5.0, phase=3, tags=["unary_operator"]),
    TestCase(input={"expression": "2 * -3", "variables": None}, expected=-6.0, phase=3, tags=["unary_operator"]),

    # Phase 4 — float precision
    TestCase(input={"expression": "0.1 + 0.2", "variables": None}, expected=0.3, phase=4, tags=["float_precision"]),
    TestCase(input={"expression": "1 / 3", "variables": None}, expected=round(1/3, 10), phase=4, tags=["float_precision"]),
    TestCase(input={"expression": "0.1 * 0.1", "variables": None}, expected=0.01, phase=4, tags=["float_precision"]),
    TestCase(input={"expression": "2.5 + 3.7", "variables": None}, expected=6.2, phase=4, tags=["float_precision"]),

    # Phase 5 — variables
    TestCase(input={"expression": "x + 1", "variables": {"x": 5}}, expected=6.0, phase=5, tags=["variable_resolution"]),
    TestCase(input={"expression": "x * y", "variables": {"x": 3, "y": 4}}, expected=12.0, phase=5, tags=["variable_resolution"]),
    TestCase(input={"expression": "x + y - z", "variables": {"x": 10, "y": 20, "z": 5}}, expected=25.0, phase=5, tags=["variable_resolution"]),
    # Undefined variable -> ValueError
    TestCase(input={"expression": "x + 1", "variables": {}}, expected=None, phase=5, tags=["undefined_variable"]),
    TestCase(input={"expression": "a + b", "variables": {"a": 1}}, expected=None, phase=5, tags=["undefined_variable"]),

    # Phase 6 — implicit multiplication
    TestCase(input={"expression": "2(3)", "variables": None}, expected=6.0, phase=6, tags=["implicit_multiply"]),
    TestCase(input={"expression": "(2)(3)", "variables": None}, expected=6.0, phase=6, tags=["implicit_multiply"]),
    TestCase(input={"expression": "2(3 + 4)", "variables": None}, expected=14.0, phase=6, tags=["implicit_multiply"]),
    TestCase(input={"expression": "(1 + 2)(3 + 4)", "variables": None}, expected=21.0, phase=6, tags=["implicit_multiply"]),

    # Phase 7 — power operator, right-associative
    TestCase(input={"expression": "2 ^ 3", "variables": None}, expected=8.0, phase=7, tags=["right_associativity"]),
    TestCase(input={"expression": "2 ^ 3 ^ 2", "variables": None}, expected=512.0, phase=7, tags=["right_associativity"]),  # 2^(3^2) = 2^9 = 512, NOT (2^3)^2 = 64
    TestCase(input={"expression": "3 ^ 2 + 1", "variables": None}, expected=10.0, phase=7, tags=["right_associativity"]),
    TestCase(input={"expression": "2 * 3 ^ 2", "variables": None}, expected=18.0, phase=7, tags=["right_associativity"]),  # 2 * (3^2)
    TestCase(input={"expression": "(2 ^ 3) ^ 2", "variables": None}, expected=64.0, phase=7, tags=["right_associativity"]),  # explicit left-assoc via parens

    # Phase 8 — division by zero with context
    TestCase(input={"expression": "1 / 0", "variables": None}, expected=None, phase=8, tags=["zero_division_context"]),
    TestCase(input={"expression": "5 + 3 / (2 - 2)", "variables": None}, expected=None, phase=8, tags=["zero_division_context"]),
    TestCase(input={"expression": "x / y", "variables": {"x": 10, "y": 0}}, expected=None, phase=8, tags=["zero_division_context"]),
]
