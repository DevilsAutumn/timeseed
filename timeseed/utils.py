"""
Utility functions for TimeSeed operations.

This module provides essential utility functions for format conversion,
time operations, validation, and performance monitoring.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Union


class FormatUtils:
    """Format conversion utilities."""

    # Standard alphabets for different bases
    BASE32_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32
    BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    @staticmethod
    def int_to_base(num: int, alphabet: str, min_length: int = 0) -> str:
        """
        Convert integer to arbitrary base using given alphabet.

        Args:
            num: Integer to convert
            alphabet: Characters to use for encoding
            min_length: Minimum length of output (zero-padded)
        """
        if num == 0:
            result = alphabet[0]
        else:
            base = len(alphabet)
            result = ""
            while num > 0:
                result = alphabet[num % base] + result
                num //= base

        # Pad with leading zeros if needed
        if len(result) < min_length:
            result = alphabet[0] * (min_length - len(result)) + result

        return result

    @staticmethod
    def base_to_int(encoded: str, alphabet: str) -> int:
        """
        Convert base-encoded string back to integer.

        Args:
            encoded: Encoded string
            alphabet: Characters used for encoding
        """
        base = len(alphabet)
        result = 0
        for char in encoded:
            if char not in alphabet:
                raise ValueError(f"Invalid character '{char}' for alphabet")
            result = result * base + alphabet.index(char)
        return result

    @staticmethod
    def int_to_hex(num: int, uppercase: bool = True, min_length: int = 0) -> str:
        """Convert integer to hexadecimal string."""
        hex_str = f"{num:x}"
        if uppercase:
            hex_str = hex_str.upper()

        if len(hex_str) < min_length:
            hex_str = "0" * (min_length - len(hex_str)) + hex_str

        return hex_str

    @staticmethod
    def int_to_base32(num: int, min_length: int = 0) -> str:
        """Convert integer to Crockford base32."""
        return FormatUtils.int_to_base(num, FormatUtils.BASE32_ALPHABET, min_length)

    @staticmethod
    def int_to_base62(num: int, min_length: int = 0) -> str:
        """Convert integer to base62."""
        return FormatUtils.int_to_base(num, FormatUtils.BASE62_ALPHABET, min_length)

    @staticmethod
    def hex_to_int(hex_str: str) -> int:
        """Convert hexadecimal string to integer."""
        return int(hex_str, 16)

    @staticmethod
    def base32_to_int(encoded: str) -> int:
        """Convert Crockford base32 to integer."""
        return FormatUtils.base_to_int(encoded.upper(), FormatUtils.BASE32_ALPHABET)

    @staticmethod
    def base62_to_int(encoded: str) -> int:
        """Convert base62 to integer."""
        return FormatUtils.base_to_int(encoded, FormatUtils.BASE62_ALPHABET)

    @staticmethod
    def int_to_binary(num: int, bits: int) -> str:
        """Convert integer to binary string with specified bit width."""
        return f"{num:0{bits}b}"


class TimeUtils:
    """Time-related utility functions."""

    @staticmethod
    def get_timestamp_ms() -> int:
        """Get current timestamp in milliseconds."""
        return int(time.time() * 1000)

    @staticmethod
    def timestamp_to_datetime(timestamp_ms: int) -> datetime:
        """Convert millisecond timestamp to datetime object."""
        return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)

    @staticmethod
    def datetime_to_timestamp(dt: datetime) -> int:
        """Convert datetime object to millisecond timestamp."""
        return int(dt.timestamp() * 1000)


class ValidationUtils:
    """Validation utility functions."""

    @staticmethod
    def validate_id_components(
        timestamp: int, machine_id: int, datacenter_id: int, sequence: int, bit_allocation: Any
    ) -> bool:
        """
        Validate that all ID components are within their bit ranges.

        Args:
            timestamp: Timestamp component
            machine_id: Machine ID component
            datacenter_id: Datacenter ID component
            sequence: Sequence component
            bit_allocation: BitAllocation instance
        """
        if not (0 <= timestamp <= bit_allocation.max_timestamp):
            return False
        if not (0 <= machine_id <= bit_allocation.max_machine_id):
            return False
        if not (0 <= datacenter_id <= bit_allocation.max_datacenter_id):
            return False
        if not (0 <= sequence <= bit_allocation.max_sequence):
            return False
        return True

    @staticmethod
    def validate_id_range(id_value: int, total_bits: int) -> bool:
        """Validate that ID value fits within the specified bit range."""
        max_value = (1 << total_bits) - 1
        return 0 <= id_value <= max_value


class PerformanceMonitor:
    """Performance monitoring and statistics collection."""

    def __init__(self) -> None:
        self._stats: Dict[str, Union[int, List[float]]] = {
            "ids_generated": 0,
            "sequence_overflows": 0,
            "clock_backward_events": 0,
            "wait_events": 0,
            "generation_times": [],
        }
        self._lock = threading.Lock()

    def record_generation(self, generation_time_ms: float) -> None:
        """Record ID generation statistics."""
        with self._lock:
            ids_generated = self._stats["ids_generated"]
            if isinstance(ids_generated, int):
                self._stats["ids_generated"] = ids_generated + 1

            generation_times = self._stats["generation_times"]
            if isinstance(generation_times, list):
                generation_times.append(generation_time_ms)

                # Keep only recent times for memory efficiency
                if len(generation_times) > 10000:
                    self._stats["generation_times"] = generation_times[-5000:]

    def record_sequence_overflow(self) -> None:
        """Record sequence overflow event."""
        with self._lock:
            overflows = self._stats["sequence_overflows"]
            if isinstance(overflows, int):
                self._stats["sequence_overflows"] = overflows + 1

    def record_clock_backward(self) -> None:
        """Record clock backward event."""
        with self._lock:
            events = self._stats["clock_backward_events"]
            if isinstance(events, int):
                self._stats["clock_backward_events"] = events + 1

    def record_wait_event(self) -> None:
        """Record wait event."""
        with self._lock:
            events = self._stats["wait_events"]
            if isinstance(events, int):
                self._stats["wait_events"] = events + 1

    def get_stats(self) -> Dict[str, Union[int, float, List[float]]]:
        """Get performance statistics."""
        with self._lock:
            # Create a new dictionary with broader type
            stats: Dict[str, Union[int, float, List[float]]] = {}
            for key, value in self._stats.items():
                stats[key] = value

            # Calculate additional metrics
            generation_times = stats["generation_times"]
            if generation_times and isinstance(generation_times, list):
                times: List[float] = generation_times
                stats["avg_generation_time"] = sum(times) / len(times)
                stats["min_generation_time"] = min(times)
                stats["max_generation_time"] = max(times)

                # Calculate generation rate (handle zero time span)
                if len(times) > 1:
                    time_span = max(times) - min(times)
                    stats["recent_generation_rate"] = len(times) / time_span if time_span > 0 else 0
                else:
                    stats["recent_generation_rate"] = 0.0
            else:
                stats["avg_generation_time"] = 0.0
                stats["min_generation_time"] = 0.0
                stats["max_generation_time"] = 0.0
                stats["recent_generation_rate"] = 0.0

            return stats

    def reset_stats(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._stats = {
                "ids_generated": 0,
                "sequence_overflows": 0,
                "clock_backward_events": 0,
                "wait_events": 0,
                "generation_times": [],
            }
