"""
Configuration module for TimeSeed ID generation.

This module provides flexible configuration for bit allocation and ID generation parameters.
"""

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class IDFormat(Enum):
    """Supported ID output formats."""

    INTEGER = "integer"
    HEX = "hex"
    BASE62 = "base62"
    BASE32 = "base32"
    BINARY = "binary"


@dataclass(frozen=True)
class BitAllocation:
    """
    Immutable configuration for bit allocation in TimeSeed IDs.

    Default allocation:
    [48 bits: Timestamp] [16 bits: Machine ID] [16 bits: Datacenter] [42 bits: Sequence]

    Total: 122 bits (leaving 6 bits for future use or padding)
    """

    timestamp_bits: int = 48
    machine_bits: int = 16
    datacenter_bits: int = 16
    sequence_bits: int = 42
    total_bits: int = 128

    def __post_init__(self) -> None:
        """Validate bit allocation after initialization."""
        used_bits = (
            self.timestamp_bits + self.machine_bits + self.datacenter_bits + self.sequence_bits
        )

        if used_bits > self.total_bits:
            raise ValueError(
                f"Total allocated bits ({used_bits}) exceeds maximum ({self.total_bits}). "
                f"Reduce some bit allocations."
            )

        if self.timestamp_bits < 32:
            raise ValueError("Timestamp bits must be at least 32 for reasonable time range")

        if self.machine_bits < 1:
            raise ValueError("Machine bits must be at least 1")

        if self.datacenter_bits < 1:
            raise ValueError("Datacenter bits must be at least 1")

        if self.sequence_bits < 8:
            raise ValueError("Sequence bits must be at least 8 for reasonable throughput")

    @property
    def max_timestamp(self) -> int:
        """Maximum timestamp value that can be encoded."""
        return (1 << self.timestamp_bits) - 1

    @property
    def max_machine_id(self) -> int:
        """Maximum machine ID that can be encoded."""
        return (1 << self.machine_bits) - 1

    @property
    def max_datacenter_id(self) -> int:
        """Maximum datacenter ID that can be encoded."""
        return (1 << self.datacenter_bits) - 1

    @property
    def max_sequence(self) -> int:
        """Maximum sequence number that can be encoded."""
        return (1 << self.sequence_bits) - 1

    @property
    def unused_bits(self) -> int:
        """Number of unused bits in the ID."""
        return self.total_bits - (
            self.timestamp_bits + self.machine_bits + self.datacenter_bits + self.sequence_bits
        )

    @property
    def sequence_shift(self) -> int:
        """Bit shift for sequence component."""
        return 0

    @property
    def datacenter_shift(self) -> int:
        """Bit shift for datacenter component."""
        return self.sequence_bits

    @property
    def machine_shift(self) -> int:
        """Bit shift for machine component."""
        return self.sequence_bits + self.datacenter_bits

    @property
    def timestamp_shift(self) -> int:
        """Bit shift for timestamp component."""
        return self.sequence_bits + self.datacenter_bits + self.machine_bits

    def get_capacity_info(self) -> Dict[str, Any]:
        """Get capacity information for this bit allocation."""
        return {
            "max_machines": self.max_machine_id + 1,
            "max_datacenters": self.max_datacenter_id + 1,
            "ids_per_millisecond": self.max_sequence + 1,
            "total_ids_per_ms": (self.max_machine_id + 1)
            * (self.max_datacenter_id + 1)
            * (self.max_sequence + 1),
            "timestamp_years": (self.max_timestamp / (365.25 * 24 * 60 * 60 * 1000)),
            "unused_bits": self.unused_bits,
        }


def _default_epoch_start() -> int:
    """Get default epoch start time (current time - 1 year)."""
    return int(time.time() * 1000) - (365 * 24 * 60 * 60 * 1000)


@dataclass
class TimeSeedConfig:
    """
    Configuration for TimeSeed ID generation.

    This class provides a flexible configuration system that can be customized
    for different deployment scenarios and requirements.
    """

    # Core bit allocation
    bit_allocation: BitAllocation = field(default_factory=BitAllocation)

    # Epoch configuration (default: Current time - 1 year for tests)
    epoch_start_ms: int = field(default_factory=_default_epoch_start)

    # Machine and datacenter identification
    machine_id: Optional[int] = None
    datacenter_id: Optional[int] = None

    # Clock handling
    clock_backward_tolerance_ms: int = 5000  # 5 seconds
    sequence_overflow_wait: bool = True

    # Performance settings
    enable_threading: bool = True
    cache_time_checks: bool = True

    # Output format preferences
    default_format: IDFormat = IDFormat.INTEGER
    hex_uppercase: bool = True
    base62_alphabet: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate IDs are within range
        if self.machine_id is not None:
            if not (0 <= self.machine_id <= self.bit_allocation.max_machine_id):
                raise ValueError(
                    f"Machine ID {self.machine_id} exceeds maximum "
                    f"{self.bit_allocation.max_machine_id}"
                )

        if self.datacenter_id is not None:
            if not (0 <= self.datacenter_id <= self.bit_allocation.max_datacenter_id):
                raise ValueError(
                    f"Datacenter ID {self.datacenter_id} exceeds maximum "
                    f"{self.bit_allocation.max_datacenter_id}"
                )

        # Validate epoch
        if self.epoch_start_ms <= 0:
            raise ValueError("Epoch start must be positive")

        # Validate base62 alphabet
        if len(set(self.base62_alphabet)) != 62:
            raise ValueError("Base62 alphabet must contain exactly 62 unique characters")

    @classmethod
    def from_environment(cls) -> "TimeSeedConfig":
        """
        Create configuration from environment variables.

        Environment variables:
        - TIMESEED_MACHINE_ID: Machine ID (0-65535)
        - TIMESEED_DATACENTER_ID: Datacenter ID (0-65535)
        - TIMESEED_EPOCH_START: Custom epoch start timestamp (ms)
        - TIMESEED_TIMESTAMP_BITS: Timestamp bit allocation
        - TIMESEED_MACHINE_BITS: Machine ID bit allocation
        - TIMESEED_DATACENTER_BITS: Datacenter ID bit allocation
        - TIMESEED_SEQUENCE_BITS: Sequence bit allocation
        """
        config = cls()

        # Machine and datacenter IDs
        machine_id = os.getenv("TIMESEED_MACHINE_ID")
        if machine_id:
            config.machine_id = int(machine_id)

        datacenter_id = os.getenv("TIMESEED_DATACENTER_ID")
        if datacenter_id:
            config.datacenter_id = int(datacenter_id)

        # Epoch configuration
        epoch_start = os.getenv("TIMESEED_EPOCH_START")
        if epoch_start:
            config.epoch_start_ms = int(epoch_start)

        # Bit allocation (requires reconstruction if any are specified)
        timestamp_bits = os.getenv("TIMESEED_TIMESTAMP_BITS")
        machine_bits = os.getenv("TIMESEED_MACHINE_BITS")
        datacenter_bits = os.getenv("TIMESEED_DATACENTER_BITS")
        sequence_bits = os.getenv("TIMESEED_SEQUENCE_BITS")

        if any([timestamp_bits, machine_bits, datacenter_bits, sequence_bits]):
            config.bit_allocation = BitAllocation(
                timestamp_bits=int(timestamp_bits) if timestamp_bits else 48,
                machine_bits=int(machine_bits) if machine_bits else 16,
                datacenter_bits=int(datacenter_bits) if datacenter_bits else 16,
                sequence_bits=int(sequence_bits) if sequence_bits else 42,
            )

        return config

    @classmethod
    def create_custom(
        cls,
        timestamp_bits: int = 48,
        machine_bits: int = 16,
        datacenter_bits: int = 16,
        sequence_bits: int = 42,
        machine_id: Optional[int] = None,
        datacenter_id: Optional[int] = None,
        epoch_start_ms: Optional[int] = None,
    ) -> "TimeSeedConfig":
        """
        Create a custom configuration with specified bit allocation.

        Args:
            timestamp_bits: Bits allocated for timestamp (default: 48)
            machine_bits: Bits allocated for machine ID (default: 16)
            datacenter_bits: Bits allocated for datacenter ID (default: 16)
            sequence_bits: Bits allocated for sequence (default: 42)
            machine_id: Fixed machine ID
            datacenter_id: Fixed datacenter ID
            epoch_start_ms: Custom epoch start in milliseconds
        """
        bit_allocation = BitAllocation(
            timestamp_bits=timestamp_bits,
            machine_bits=machine_bits,
            datacenter_bits=datacenter_bits,
            sequence_bits=sequence_bits,
        )

        return cls(
            bit_allocation=bit_allocation,
            machine_id=machine_id,
            datacenter_id=datacenter_id,
            epoch_start_ms=epoch_start_ms or _default_epoch_start(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "bit_allocation": {
                "timestamp_bits": self.bit_allocation.timestamp_bits,
                "machine_bits": self.bit_allocation.machine_bits,
                "datacenter_bits": self.bit_allocation.datacenter_bits,
                "sequence_bits": self.bit_allocation.sequence_bits,
                "total_bits": self.bit_allocation.total_bits,
                "unused_bits": self.bit_allocation.unused_bits,
            },
            "epoch_start_ms": self.epoch_start_ms,
            "machine_id": self.machine_id,
            "datacenter_id": self.datacenter_id,
            "clock_backward_tolerance_ms": self.clock_backward_tolerance_ms,
            "sequence_overflow_wait": self.sequence_overflow_wait,
            "enable_threading": self.enable_threading,
            "default_format": self.default_format.value,
            "capacity": self.bit_allocation.get_capacity_info(),
        }


# Predefined configurations for common use cases
class PresetConfigs:
    """Predefined configurations for common scenarios."""

    @staticmethod
    def high_throughput() -> TimeSeedConfig:
        """Configuration optimized for high throughput (more sequence bits)."""
        return TimeSeedConfig.create_custom(
            timestamp_bits=41,  # ~69 years
            machine_bits=10,  # 1024 machines
            datacenter_bits=8,  # 256 datacenters
            sequence_bits=47,  # 140 trillion IDs per millisecond
        )

    @staticmethod
    def long_lifespan() -> TimeSeedConfig:
        """Configuration optimized for long lifespan (more timestamp bits)."""
        return TimeSeedConfig.create_custom(
            timestamp_bits=55,  # ~1140 years
            machine_bits=12,  # 4096 machines
            datacenter_bits=8,  # 256 datacenters
            sequence_bits=31,  # 2 billion IDs per millisecond
        )

    @staticmethod
    def many_datacenters() -> TimeSeedConfig:
        """Configuration optimized for many datacenters."""
        return TimeSeedConfig.create_custom(
            timestamp_bits=45,  # ~36 years
            machine_bits=12,  # 4096 machines
            datacenter_bits=20,  # 1 million datacenters
            sequence_bits=29,  # 500 million IDs per millisecond
        )

    @staticmethod
    def small_scale() -> TimeSeedConfig:
        """Configuration for smaller deployments with more timestamp precision."""
        return TimeSeedConfig.create_custom(
            timestamp_bits=52,  # ~142 years
            machine_bits=8,  # 256 machines
            datacenter_bits=4,  # 16 datacenters
            sequence_bits=42,  # 4 trillion IDs per millisecond
        )


# Default configuration instance
DEFAULT_CONFIG = TimeSeedConfig()
