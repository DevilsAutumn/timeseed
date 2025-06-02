"""
Core ID generation module for TimeSeed.

This module contains the main TimeSeed class responsible for generating
chronologically ordered unique identifiers with configurable bit allocation.
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Union

from .config import IDFormat, TimeSeedConfig
from .exceptions import (
    DatacenterIdError,
    DecodingError,
    FormatError,
    MachineIdError,
    SequenceOverflowError,
    TimeSeedError,
    create_clock_backward_error,
)
from .simple_ids import resolve_datacenter_id, resolve_machine_id
from .utils import FormatUtils, PerformanceMonitor, TimeUtils, ValidationUtils


@dataclass(frozen=True)
class TimeSeedComponents:
    """
    Immutable components of a decoded TimeSeed ID.

    This class represents the individual components that make up a TimeSeed ID,
    useful for debugging, analysis, and understanding ID structure.
    """

    timestamp: int
    machine_id: int
    datacenter_id: int
    sequence: int
    generated_at: datetime
    epoch_offset_ms: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert components to dictionary representation."""
        return {
            "timestamp": self.timestamp,
            "machine_id": self.machine_id,
            "datacenter_id": self.datacenter_id,
            "sequence": self.sequence,
            "generated_at": self.generated_at.isoformat(),
            "epoch_offset_ms": self.epoch_offset_ms,
        }

    @property
    def actual_timestamp_ms(self) -> int:
        """Get the actual timestamp in milliseconds since Unix epoch."""
        return self.timestamp + self.epoch_offset_ms


class TimeSeed:
    """
    High-performance chronologically ordered unique ID generator.

    TimeSeed generates 128-bit unique identifiers with configurable bit allocation
    for timestamp, machine ID, datacenter ID, and sequence components. IDs are
    guaranteed to be chronologically ordered and collision-free within the same
    millisecond when properly configured.

    Default bit allocation:
    - 48 bits: Timestamp (878 years from epoch)
    - 16 bits: Machine ID (65,536 machines)
    - 16 bits: Datacenter ID (65,536 datacenters)
    - 42 bits: Sequence (4.4 trillion IDs per millisecond)
    - 6 bits: Reserved for future use

    Example:
        # Basic usage with auto-detected machine/datacenter IDs
        generator = TimeSeed()
        id1 = generator.generate()

        # Custom configuration
        config = TimeSeedConfig.create_custom(
            timestamp_bits=50, machine_bits=10, datacenter_bits=10, sequence_bits=48
        )
        generator = TimeSeed(config)

        # Specific machine and datacenter
        generator = TimeSeed(machine_id=42, datacenter_id=7)
    """

    def __init__(
        self,
        config: Optional[TimeSeedConfig] = None,
        machine_id: Optional[int] = None,
        datacenter_id: Optional[int] = None,
    ):
        """
        Initialize TimeSeed generator.

        Args:
            config: Configuration object. Uses default if None.
            machine_id: Override machine ID from config
            datacenter_id: Override datacenter ID from config

        Raises:
            MachineIdError: If machine ID is invalid
            DatacenterIdError: If datacenter ID is invalid
        """
        # Use provided config or create default
        self.config = config or TimeSeedConfig()

        # Resolve machine and datacenter IDs
        self.machine_id = self._resolve_machine_id(machine_id)
        self.datacenter_id = self._resolve_datacenter_id(datacenter_id)

        # Validate IDs are within bit allocation limits
        self._validate_ids()

        # Thread safety and state management
        self._lock = threading.Lock()
        self._last_timestamp = -1
        self._sequence = 0

        # Performance monitoring
        self._performance_monitor = PerformanceMonitor()

        # Cache for bit masks (performance optimization)
        self._timestamp_mask = (1 << self.config.bit_allocation.timestamp_bits) - 1
        self._machine_mask = (1 << self.config.bit_allocation.machine_bits) - 1
        self._datacenter_mask = (1 << self.config.bit_allocation.datacenter_bits) - 1
        self._sequence_mask = (1 << self.config.bit_allocation.sequence_bits) - 1

    def _resolve_machine_id(self, override_id: Optional[int]) -> int:
        """Resolve machine ID using simple strategy."""
        # Use override_id if explicitly provided (including 0), else use config
        machine_id = override_id if override_id is not None else self.config.machine_id
        return resolve_machine_id(machine_id, self.config.bit_allocation.max_machine_id)

    def _resolve_datacenter_id(self, override_id: Optional[int]) -> int:
        """Resolve datacenter ID using simple strategy."""
        # Use override_id if explicitly provided (including 0), else use config
        datacenter_id = override_id if override_id is not None else self.config.datacenter_id
        return resolve_datacenter_id(datacenter_id, self.config.bit_allocation.max_datacenter_id)

    def _validate_ids(self) -> None:
        """Validate machine and datacenter IDs are within allowed ranges."""
        if not (0 <= self.machine_id <= self.config.bit_allocation.max_machine_id):
            raise MachineIdError(
                f"Machine ID {self.machine_id} exceeds maximum "
                f"{self.config.bit_allocation.max_machine_id} for "
                f"{self.config.bit_allocation.machine_bits}-bit allocation"
            )

        if not (0 <= self.datacenter_id <= self.config.bit_allocation.max_datacenter_id):
            raise DatacenterIdError(
                f"Datacenter ID {self.datacenter_id} exceeds maximum "
                f"{self.config.bit_allocation.max_datacenter_id} for "
                f"{self.config.bit_allocation.datacenter_bits}-bit allocation"
            )

    def _get_timestamp(self) -> int:
        """Get current timestamp relative to epoch."""
        current_ms = TimeUtils.get_timestamp_ms()
        return current_ms - self.config.epoch_start_ms

    def _wait_for_next_millisecond(self, last_timestamp: int) -> int:
        """Wait until the next millisecond and return new timestamp."""
        self._performance_monitor.record_wait_event()

        timestamp = self._get_timestamp()
        while timestamp <= last_timestamp:
            time.sleep(0.0001)  # Sleep 0.1ms
            timestamp = self._get_timestamp()
        return timestamp

    def _handle_clock_backward(self, current_timestamp: int) -> int:
        """Handle clock moving backward."""
        backward_ms = self._last_timestamp - current_timestamp
        self._performance_monitor.record_clock_backward()

        # Check if backward movement exceeds tolerance
        if backward_ms > self.config.clock_backward_tolerance_ms:
            raise create_clock_backward_error(backward_ms, self.config.clock_backward_tolerance_ms)

        # For small backward movements, wait until we're past the last timestamp
        return self._wait_for_next_millisecond(self._last_timestamp)

    def _handle_sequence_overflow(self, timestamp: int) -> int:
        """Handle sequence number overflow."""
        self._performance_monitor.record_sequence_overflow()

        if self.config.sequence_overflow_wait:
            # Wait for next millisecond and reset sequence
            return self._wait_for_next_millisecond(timestamp)
        else:
            # Raise exception immediately
            raise SequenceOverflowError(
                f"Sequence overflow at timestamp {timestamp}. "
                f"Maximum {self.config.bit_allocation.max_sequence} IDs per millisecond exceeded.",
                timestamp_ms=timestamp,
                max_sequence=self.config.bit_allocation.max_sequence,
            )

    def generate(self) -> int:
        """
        Generate a new TimeSeed ID.

        Returns:
            int: 128-bit unique identifier

        Raises:
            ClockBackwardError: If system clock moves backward significantly
            SequenceOverflowError: If sequence overflows and overflow_wait is False
        """
        start_time = time.time()

        try:
            with self._lock:
                timestamp = self._get_timestamp()

                # Handle clock moving backward
                if timestamp < self._last_timestamp:
                    timestamp = self._handle_clock_backward(timestamp)

                # Handle same millisecond - increment sequence
                if timestamp == self._last_timestamp:
                    self._sequence = (self._sequence + 1) & self._sequence_mask

                    # Check for sequence overflow
                    if self._sequence == 0:
                        timestamp = self._handle_sequence_overflow(timestamp)
                else:
                    # New millisecond - reset sequence
                    self._sequence = 0

                # Update last timestamp
                self._last_timestamp = timestamp

                # Ensure timestamp fits in allocated bits
                timestamp_component = timestamp & self._timestamp_mask

                # Combine all components using bit shifts
                id_value = (
                    (timestamp_component << self.config.bit_allocation.timestamp_shift)
                    | (self.machine_id << self.config.bit_allocation.machine_shift)
                    | (self.datacenter_id << self.config.bit_allocation.datacenter_shift)
                    | (self._sequence << self.config.bit_allocation.sequence_shift)
                )

                # Record performance metrics
                generation_time = (time.time() - start_time) * 1000  # Convert to ms
                self._performance_monitor.record_generation(generation_time)

                return id_value

        except Exception as e:
            if isinstance(e, TimeSeedError):
                raise
            raise TimeSeedError(f"Unexpected error during ID generation: {e}") from e

    def generate_hex(self, uppercase: bool = None) -> str:
        """
        Generate ID as hexadecimal string.

        Args:
            uppercase: Force uppercase/lowercase. Uses config default if None.
        """
        id_value = self.generate()
        use_uppercase = uppercase if uppercase is not None else self.config.hex_uppercase
        return FormatUtils.int_to_hex(id_value, uppercase=use_uppercase, min_length=32)

    def generate_base62(self) -> str:
        """Generate ID as base62 string (URL-safe)."""
        id_value = self.generate()
        return FormatUtils.int_to_base(id_value, self.config.base62_alphabet, min_length=22)

    def generate_base32(self) -> str:
        """Generate ID as Crockford base32 string."""
        id_value = self.generate()
        return FormatUtils.int_to_base32(id_value, min_length=26)

    def generate_binary(self) -> str:
        """Generate ID as binary string."""
        id_value = self.generate()
        return FormatUtils.int_to_binary(id_value, self.config.bit_allocation.total_bits)

    def to_hex(self, id_value: int, uppercase: bool = None) -> str:
        """
        Convert an existing TimeSeed ID to hexadecimal format.

        Args:
            id_value: TimeSeed ID to convert
            uppercase: Force uppercase/lowercase. Uses config default if None.

        Returns:
            str: Hexadecimal representation
        """
        use_uppercase = uppercase if uppercase is not None else self.config.hex_uppercase
        return FormatUtils.int_to_hex(id_value, uppercase=use_uppercase, min_length=32)

    def to_base62(self, id_value: int) -> str:
        """
        Convert an existing TimeSeed ID to base62 format.

        Args:
            id_value: TimeSeed ID to convert

        Returns:
            str: Base62 representation (URL-safe)
        """
        return FormatUtils.int_to_base(id_value, self.config.base62_alphabet, min_length=22)

    def to_base32(self, id_value: int) -> str:
        """
        Convert an existing TimeSeed ID to base32 format.

        Args:
            id_value: TimeSeed ID to convert

        Returns:
            str: Crockford base32 representation
        """
        return FormatUtils.int_to_base32(id_value, min_length=26)

    def to_binary(self, id_value: int) -> str:
        """
        Convert an existing TimeSeed ID to binary format.

        Args:
            id_value: TimeSeed ID to convert

        Returns:
            str: Binary representation
        """
        return FormatUtils.int_to_binary(id_value, self.config.bit_allocation.total_bits)

    def convert_format(self, id_value: int, target_format: Union[IDFormat, str]) -> str:
        """
        Convert an existing TimeSeed ID to specified format.

        Args:
            id_value: TimeSeed ID to convert
            target_format: Target format (IDFormat enum or string)

        Returns:
            str: ID in target format
        """
        if isinstance(target_format, str):
            try:
                target_format = IDFormat(target_format.lower())
            except ValueError as e:
                raise FormatError(f"Unsupported format: {target_format}") from e

        if target_format == IDFormat.INTEGER:
            return str(id_value)
        elif target_format == IDFormat.HEX:
            return self.to_hex(id_value)
        elif target_format == IDFormat.BASE62:
            return self.to_base62(id_value)
        elif target_format == IDFormat.BASE32:
            return self.to_base32(id_value)
        elif target_format == IDFormat.BINARY:
            return self.to_binary(id_value)
        else:
            raise FormatError(f"Unsupported format: {target_format}")

    def get_all_formats(self, id_value: int) -> Dict[str, str]:
        """
        Get an existing TimeSeed ID in all supported formats.

        Args:
            id_value: TimeSeed ID to convert

        Returns:
            Dict[str, str]: ID in all formats
        """
        return {
            "integer": str(id_value),
            "hex": self.to_hex(id_value),
            "base62": self.to_base62(id_value),
            "base32": self.to_base32(id_value),
            "binary": self.to_binary(id_value),
        }

    def decode(self, id_value: int) -> TimeSeedComponents:
        """
        Decode a TimeSeed ID into its components.

        Args:
            id_value: TimeSeed ID to decode

        Returns:
            TimeSeedComponents: Decoded components

        Raises:
            DecodingError: If ID cannot be decoded
        """
        try:
            # Validate ID is within expected range
            if not ValidationUtils.validate_id_range(
                id_value, self.config.bit_allocation.total_bits
            ):
                raise DecodingError(
                    f"ID value {id_value} exceeds {self.config.bit_allocation.total_bits}-bit range"
                )

            # Extract components using bit masks and shifts
            sequence = id_value & self._sequence_mask
            datacenter_id = (
                id_value >> self.config.bit_allocation.datacenter_shift
            ) & self._datacenter_mask
            machine_id = (id_value >> self.config.bit_allocation.machine_shift) & self._machine_mask
            timestamp = (
                id_value >> self.config.bit_allocation.timestamp_shift
            ) & self._timestamp_mask

            # Convert timestamp back to datetime
            actual_timestamp_ms = timestamp + self.config.epoch_start_ms
            generated_at = TimeUtils.timestamp_to_datetime(actual_timestamp_ms)

            return TimeSeedComponents(
                timestamp=timestamp,
                machine_id=machine_id,
                datacenter_id=datacenter_id,
                sequence=sequence,
                generated_at=generated_at,
                epoch_offset_ms=self.config.epoch_start_ms,
            )

        except Exception as e:
            if isinstance(e, DecodingError):
                raise
            raise DecodingError(f"Failed to decode ID {id_value}: {e}") from e

    def decode_hex(self, hex_str: str) -> TimeSeedComponents:
        """Decode hexadecimal string representation."""
        try:
            id_value = FormatUtils.hex_to_int(hex_str)
            return self.decode(id_value)
        except Exception as e:
            raise DecodingError(f"Failed to decode hex string '{hex_str}': {e}") from e

    def decode_base62(self, base62_str: str) -> TimeSeedComponents:
        """Decode base62 string representation."""
        try:
            id_value = FormatUtils.base_to_int(base62_str, self.config.base62_alphabet)
            return self.decode(id_value)
        except Exception as e:
            raise DecodingError(f"Failed to decode base62 string '{base62_str}': {e}") from e

    def decode_base32(self, base32_str: str) -> TimeSeedComponents:
        """Decode Crockford base32 string representation."""
        try:
            id_value = FormatUtils.base32_to_int(base32_str)
            return self.decode(id_value)
        except Exception as e:
            raise DecodingError(f"Failed to decode base32 string '{base32_str}': {e}") from e

    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive information about this generator."""
        return {
            "generator_config": self.config.to_dict(),
            "machine_id": self.machine_id,
            "datacenter_id": self.datacenter_id,
            "performance_stats": self._performance_monitor.get_stats(),
            "current_sequence": self._sequence,
            "last_timestamp": self._last_timestamp,
            "capacity_info": self.config.bit_allocation.get_capacity_info(),
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this generator."""
        return self._performance_monitor.get_stats()

    def reset_performance_stats(self) -> None:
        """Reset performance statistics."""
        self._performance_monitor.reset_stats()

    def validate_id(self, id_value: int) -> bool:
        """
        Validate that an ID could have been generated by this configuration.

        Note: This only validates structure, not that it was actually generated
        by this specific instance.
        """
        try:
            components = self.decode(id_value)
            return ValidationUtils.validate_id_components(
                components.timestamp,
                components.machine_id,
                components.datacenter_id,
                components.sequence,
                self.config.bit_allocation,
            )
        except Exception:
            return False

    def __repr__(self) -> str:
        """String representation of the generator."""
        return (
            f"TimeSeed(machine_id={self.machine_id}, datacenter_id={self.datacenter_id}, "
            f"bits=[{self.config.bit_allocation.timestamp_bits}t/"
            f"{self.config.bit_allocation.machine_bits}m/"
            f"{self.config.bit_allocation.datacenter_bits}d/"
            f"{self.config.bit_allocation.sequence_bits}s])"
        )
