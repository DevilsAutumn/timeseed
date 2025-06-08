import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


TEST_MACHINE_ID = 42
TEST_DATACENTER_ID = 7
TEST_EPOCH = 1640995200000  # 2022-01-01 00:00:00 UTC


def assert_chronological_order(ids: list) -> None:
    for i in range(len(ids) - 1):
        assert ids[i] < ids[i + 1], f"ID {ids[i]} should be < {ids[i + 1]}"


def assert_no_duplicates(ids: list) -> None:
    unique_ids = set(ids)
    assert len(unique_ids) == len(ids), f"Found {len(ids) - len(unique_ids)} duplicates"


def assert_valid_hex_format(hex_str: str, expected_length: int = 32) -> None:
    assert len(hex_str) == expected_length, f"Hex length should be {expected_length}"
    assert all(c in "0123456789ABCDEFabcdef" for c in hex_str), "Invalid hex characters"


def assert_valid_base62_format(b62_str: str, expected_length: int = 22) -> None:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    assert len(b62_str) <= expected_length, f"Base62 length should be <= {expected_length}"
    assert all(c in alphabet for c in b62_str), "Invalid base62 characters"


def suppress_warnings():
    import warnings

    warnings.filterwarnings("ignore", message=".*random.*ID.*")
