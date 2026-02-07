"""Test cases for task_01_transform_list.

Rules (cumulative):
  Phase 0: double all numbers
  Phase 1: negatives -> take absolute value first, then double. Plus no_mutation.
  Phase 2: if any result element > 100, cap at 100. Plus correct_type (list).

Expected values reflect the FINAL correct behavior for each test's input.
Earlier phases use inputs that don't trigger later rules.
"""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — basic doubling. Only small positives (no negatives, no overflow)
    # Naive [x*2 for x in lst] passes these AND the final solution does too.
    TestCase(input=[1, 2, 3], expected=[2, 4, 6], phase=0, tags=["basic"]),
    TestCase(input=[10], expected=[20], phase=0, tags=["basic"]),
    TestCase(input=[7, 5], expected=[14, 10], phase=0, tags=["basic"]),
    TestCase(input=[0], expected=[0], phase=0, tags=["basic"]),

    # Phase 1 — inputs with negatives
    # Naive solution doubles negatives: [-3, 2] -> [-6, 4] (WRONG)
    # Correct: abs first, then double: [-3, 2] -> [6, 4]
    # These inputs have small abs values so no cap needed
    TestCase(
        input=[-3, 2], expected=[6, 4], phase=1, tags=["negative_handling"]
    ),
    TestCase(
        input=[-1, -2, -3], expected=[2, 4, 6], phase=1, tags=["negative_handling"]
    ),
    TestCase(
        input=[4, -5, 6], expected=[8, 10, 12], phase=1, tags=["negative_handling"]
    ),
    TestCase(
        input=[-10, 10], expected=[20, 20], phase=1, tags=["negative_handling"]
    ),

    # Phase 2 — large values that exceed 100 after doubling
    # A solution that handles negatives via abs+double but doesn't cap will fail:
    # e.g. [60, -80] -> [120, 160] (WRONG) vs [100, 100] (correct with cap)
    TestCase(
        input=[60, 30], expected=[100, 60], phase=2, tags=["cap_overflow"]
    ),
    TestCase(
        input=[100], expected=[100], phase=2, tags=["cap_overflow"]
    ),
    TestCase(
        input=[-80, 20, 51], expected=[100, 40, 100], phase=2, tags=["cap_overflow"]
    ),
    TestCase(
        input=[50, 50, 50], expected=[100, 100, 100], phase=2, tags=["cap_overflow"]
    ),
]
