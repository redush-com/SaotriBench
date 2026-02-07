"""Test cases for task_00_fizzbuzz."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — classic FizzBuzz
    TestCase(input=1, expected="1", phase=0, tags=["plain_number"]),
    TestCase(input=2, expected="2", phase=0, tags=["plain_number"]),
    TestCase(input=3, expected="Fizz", phase=0, tags=["divisible_by_3"]),
    TestCase(input=5, expected="Buzz", phase=0, tags=["divisible_by_5"]),
    TestCase(input=6, expected="Fizz", phase=0, tags=["divisible_by_3"]),
    TestCase(input=9, expected="Fizz", phase=0, tags=["divisible_by_3"]),
    TestCase(input=10, expected="Buzz", phase=0, tags=["divisible_by_5"]),
    TestCase(input=15, expected="FizzBuzz", phase=0, tags=["divisible_by_15"]),
    TestCase(input=30, expected="FizzBuzz", phase=0, tags=["divisible_by_15"]),
    TestCase(input=4, expected="4", phase=0, tags=["plain_number"]),

    # Phase 1 — divisible by 7 = "Bazz"
    TestCase(input=7, expected="Bazz", phase=1, tags=["divisible_by_7"]),
    TestCase(input=14, expected="Bazz", phase=1, tags=["divisible_by_7"]),
    TestCase(input=49, expected="Bazz", phase=1, tags=["divisible_by_7"]),
    TestCase(input=11, expected="11", phase=1, tags=["plain_number"]),

    # Phase 2 — combinations with 7
    TestCase(input=21, expected="FizzBazz", phase=2, tags=["divisible_by_21"]),
    TestCase(input=42, expected="FizzBazz", phase=2, tags=["divisible_by_21"]),
    TestCase(input=35, expected="BuzzBazz", phase=2, tags=["divisible_by_35"]),
    TestCase(input=70, expected="BuzzBazz", phase=2, tags=["divisible_by_35"]),
    TestCase(input=105, expected="FizzBuzzBazz", phase=2, tags=["divisible_by_105"]),
    TestCase(input=210, expected="FizzBuzzBazz", phase=2, tags=["divisible_by_105"]),
]
