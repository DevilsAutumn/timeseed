"""
Custom exceptions for TimeSeed operations.

This module defines all exception types that can be raised during ID generation
and related operations.
"""


class TimeSeedError(Exception):
    """Base exception for all TimeSeed-related errors."""

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__


class ConfigurationError(TimeSeedError):
    """Raised when there are configuration-related errors."""

    pass


class BitAllocationError(ConfigurationError):
    """Raised when bit allocation is invalid."""

    pass


class ClockError(TimeSeedError):
    """Base class for clock-related errors."""

    pass


class ClockBackwardError(ClockError):
    """
    Raised when the system clock moves backward significantly.

    This can happen due to:
    - System clock adjustment
    - NTP synchronization
    - Virtual machine migration
    - Hardware issues
    """

    def __init__(self, message: str, backward_ms: int):
        super().__init__(message)
        self.backward_ms = backward_ms


class SequenceOverflowError(TimeSeedError):
    """
    Raised when sequence number overflows within the same millisecond.

    This indicates extremely high throughput that exceeds the configured
    sequence bit capacity.
    """

    def __init__(self, message: str, timestamp_ms: int, max_sequence: int):
        super().__init__(message)
        self.timestamp_ms = timestamp_ms
        self.max_sequence = max_sequence


class MachineIdError(ConfigurationError):
    """Raised when machine ID is invalid or cannot be determined."""

    pass


class DatacenterIdError(ConfigurationError):
    """Raised when datacenter ID is invalid or cannot be determined."""

    pass


class DecodingError(TimeSeedError):
    """Raised when ID decoding fails."""

    pass


class FormatError(TimeSeedError):
    """Raised when ID format conversion fails."""

    pass


class ValidationError(TimeSeedError):
    """Raised when ID validation fails."""

    pass


class NetworkError(TimeSeedError):
    """Raised when network-related operations fail during ID generation."""

    pass


class ThreadSafetyError(TimeSeedError):
    """Raised when thread safety is compromised."""

    pass


# Error codes for programmatic handling
class ErrorCodes:
    """Standard error codes for TimeSeed exceptions."""

    # Configuration errors
    INVALID_BIT_ALLOCATION = "INVALID_BIT_ALLOCATION"
    INVALID_MACHINE_ID = "INVALID_MACHINE_ID"
    INVALID_DATACENTER_ID = "INVALID_DATACENTER_ID"
    INVALID_EPOCH = "INVALID_EPOCH"

    # Clock errors
    CLOCK_BACKWARD = "CLOCK_BACKWARD"
    CLOCK_FORWARD_JUMP = "CLOCK_FORWARD_JUMP"

    # Sequence errors
    SEQUENCE_OVERFLOW = "SEQUENCE_OVERFLOW"
    SEQUENCE_EXHAUSTED = "SEQUENCE_EXHAUSTED"

    # Format errors
    INVALID_FORMAT = "INVALID_FORMAT"
    DECODING_FAILED = "DECODING_FAILED"
    ENCODING_FAILED = "ENCODING_FAILED"

    # Network errors
    HOSTNAME_RESOLUTION_FAILED = "HOSTNAME_RESOLUTION_FAILED"
    NETWORK_INTERFACE_ERROR = "NETWORK_INTERFACE_ERROR"

    # Thread safety errors
    CONCURRENT_ACCESS = "CONCURRENT_ACCESS"
    LOCK_TIMEOUT = "LOCK_TIMEOUT"


def create_clock_backward_error(backward_ms: int, tolerance_ms: int) -> ClockBackwardError:
    """Create a standardized clock backward error."""
    return ClockBackwardError(
        f"Clock moved backward by {backward_ms}ms, exceeding tolerance of {tolerance_ms}ms. "
        f"This may indicate system clock adjustment or hardware issues.",
        backward_ms=backward_ms,
    )


def create_sequence_overflow_error(timestamp_ms: int, max_sequence: int) -> SequenceOverflowError:
    """Create a standardized sequence overflow error."""
    return SequenceOverflowError(
        f"Sequence number exceeded maximum value of {max_sequence} at timestamp {timestamp_ms}ms. "
        f"Consider increasing sequence bits or implementing load balancing.",
        timestamp_ms=timestamp_ms,
        max_sequence=max_sequence,
    )


def create_machine_id_error(machine_id: int, max_machine_id: int) -> MachineIdError:
    """Create a standardized machine ID error."""
    return MachineIdError(
        f"Machine ID {machine_id} exceeds maximum allowed value of {max_machine_id}. "
        f"Check bit allocation or use a different machine ID.",
        error_code=ErrorCodes.INVALID_MACHINE_ID,
    )


def create_datacenter_id_error(datacenter_id: int, max_datacenter_id: int) -> DatacenterIdError:
    """Create a standardized datacenter ID error."""
    return DatacenterIdError(
        f"Datacenter ID {datacenter_id} exceeds maximum allowed value of {max_datacenter_id}. "
        f"Check bit allocation or use a different datacenter ID.",
        error_code=ErrorCodes.INVALID_DATACENTER_ID,
    )
