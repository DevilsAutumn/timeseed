"""
TimeSeed - High-performance chronologically ordered unique ID generator for distributed systems.

TimeSeed provides configurable generation of 128-bit unique identifiers
with guaranteed chronological ordering. Features flexible bit allocation for
timestamp precision, machine/datacenter identification, and sequence capacity.

Key Features:
- Strict chronological ordering (not just "roughly ordered")
- Configurable bit allocation for different use cases
- Both machine and datacenter ID support for distributed systems
- Multiple output formats (int, hex, base62, base32, binary)
- Thread-safe with high-throughput performance
- Zero external dependencies
- Comprehensive error handling and monitoring

Basic Usage:
    import timeseed

    # Generate IDs using default configuration
    id1 = timeseed.generate()              # 128-bit integer
    id2 = timeseed.generate_hex()          # Hex string
    id3 = timeseed.generate_base62()       # URL-safe base62

    # Decode IDs
    components = timeseed.decode(id1)
    print(f"Generated at: {components.generated_at}")

Advanced Usage:
    from timeseed import TimeSeed, TimeSeedConfig

    # Custom configuration
    config = TimeSeedConfig.create_custom(
        timestamp_bits=50,
        machine_bits=10,
        datacenter_bits=8,
        sequence_bits=48
    )
    generator = TimeSeed(config, machine_id=42, datacenter_id=7)

    # Generate with custom generator
    custom_id = generator.generate()

Perfect for:
- Database primary keys that need temporal ordering
- Distributed systems requiring coordination-free ID generation
- Event sourcing and audit logs
- URL-safe identifiers with time-based sorting
"""

__version__ = "0.1.2a1"
__author__ = "Bhuvnesh Sharma"
__email__ = "bhuvnesh875@gmail.com"
__description__ = (
    "High-performance chronologically ordered unique ID generator with "
    "configurable bit allocation for distributed systems."
)
__url__ = "https://github.com/devilsautumn/timeseed"
__license__ = "MIT"

# Global default generator instance for convenience functions
import threading

from .config import DEFAULT_CONFIG, BitAllocation, IDFormat, PresetConfigs, TimeSeedConfig
from .exceptions import (
    BitAllocationError,
    ClockBackwardError,
    ClockError,
    ConfigurationError,
    DatacenterIdError,
    DecodingError,
    FormatError,
    MachineIdError,
    SequenceOverflowError,
    TimeSeedError,
    ValidationError,
)

# Core exports - Main classes and functions users will import
from .generator import TimeSeed, TimeSeedComponents

# Utility exports for advanced users
from .utils import FormatUtils, TimeUtils, ValidationUtils

_default_generator = None
_generator_lock = threading.Lock()


def _get_default_generator() -> TimeSeed:
    """
    Get or create the default TimeSeed generator.

    This creates a singleton instance that's used by the convenience functions.
    The generator uses machine and datacenter IDs.
    """
    global _default_generator

    if _default_generator is None:
        with _generator_lock:
            if _default_generator is None:
                _default_generator = TimeSeed()

    return _default_generator


def configure_default(
    config: TimeSeedConfig = None, machine_id: int = None, datacenter_id: int = None
) -> None:
    """
    Configure the default TimeSeed generator.

    This allows customization of the global generator used by convenience functions.
    Call this early in your application startup to set custom configuration.

    Args:
        config: Custom configuration. Uses default if None.
        machine_id: Machine ID override
        datacenter_id: Datacenter ID override

    Example:
        import timeseed

        # Configure for high throughput
        config = timeseed.PresetConfigs.high_throughput()
        timeseed.configure_default(config, machine_id=42, datacenter_id=7)

        # Now all convenience functions use this configuration
        id1 = timeseed.generate()
    """
    global _default_generator

    with _generator_lock:
        _default_generator = TimeSeed(config, machine_id, datacenter_id)


def reset_default() -> None:
    """
    Reset the default generator to initial state.

    This forces recreation of the default generator on next use,
    useful for testing or configuration changes.
    """
    global _default_generator

    with _generator_lock:
        _default_generator = None


# Convenience functions using default generator
def generate() -> int:
    """
    Generate a TimeSeed ID using the default generator.

    Returns:
        int: 128-bit unique identifier

    Example:
        id1 = timeseed.generate()
        id2 = timeseed.generate()
        assert id1 < id2  # Chronologically ordered
    """
    return _get_default_generator().generate()


def generate_hex(uppercase: bool = None) -> str:
    """
    Generate a TimeSeed ID as hexadecimal string.

    Args:
        uppercase: Force uppercase/lowercase. Uses config default if None.

    Returns:
        str: 32-character hexadecimal string

    Example:
        hex_id = timeseed.generate_hex()
        # Returns: "A1B2C3D4E5F6789012345678ABCDEF01"
    """
    return _get_default_generator().generate_hex(uppercase)


def generate_base62() -> str:
    """
    Generate a TimeSeed ID as URL-safe base62 string.

    Returns:
        str: 22-character base62 string

    Example:
        b62_id = timeseed.generate_base62()
        # Returns: "2jk3Nm5pQ8rS1tU7vW9xYz"
    """
    return _get_default_generator().generate_base62()


def generate_base32() -> str:
    """
    Generate a TimeSeed ID as Crockford base32 string.

    Returns:
        str: 26-character base32 string

    Example:
        b32_id = timeseed.generate_base32()
        # Returns: "A1B2C3D4E5F6G7H8J9K0M1N2P3"
    """
    return _get_default_generator().generate_base32()


def generate_binary() -> str:
    """
    Generate a TimeSeed ID as binary string.

    Returns:
        str: 128-character binary string

    Example:
        bin_id = timeseed.generate_binary()
        # Returns: "101010001011001100110100..."
    """
    return _get_default_generator().generate_binary()


def generate_batch(count: int, format_type: str = "integer") -> list:
    """
    Generate multiple TimeSeed IDs efficiently.

    Args:
        count: Number of IDs to generate
        format_type: Output format for all IDs

    Returns:
        list: List of generated IDs

    Example:
        ids = timeseed.generate_batch(1000, "hex")
        assert len(ids) == 1000
        assert all(isinstance(id_val, str) for id_val in ids)
    """
    generator = _get_default_generator()

    if format_type == "integer":
        return [generator.generate() for _ in range(count)]
    else:
        return [generator.convert_format(generator.generate(), format_type) for _ in range(count)]


def decode(id_value: int) -> TimeSeedComponents:
    """
    Decode a TimeSeed ID into its components.

    Args:
        id_value: TimeSeed ID to decode

    Returns:
        TimeSeedComponents: Decoded components with timestamp, machine_id, etc.

    Example:
        id_val = timeseed.generate()
        components = timeseed.decode(id_val)
        print(f"Generated at: {components.generated_at}")
        print(f"Machine: {components.machine_id}")
        print(f"Datacenter: {components.datacenter_id}")
        print(f"Sequence: {components.sequence}")
    """
    return _get_default_generator().decode(id_value)


def decode_hex(hex_str: str) -> TimeSeedComponents:
    """
    Decode a hexadecimal TimeSeed ID.

    Args:
        hex_str: Hexadecimal ID string

    Returns:
        TimeSeedComponents: Decoded components

    Example:
        hex_id = timeseed.generate_hex()
        components = timeseed.decode_hex(hex_id)
    """
    return _get_default_generator().decode_hex(hex_str)


def decode_base62(base62_str: str) -> TimeSeedComponents:
    """
    Decode a base62 TimeSeed ID.

    Args:
        base62_str: Base62 ID string

    Returns:
        TimeSeedComponents: Decoded components

    Example:
        b62_id = timeseed.generate_base62()
        components = timeseed.decode_base62(b62_id)
    """
    return _get_default_generator().decode_base62(base62_str)


def decode_base32(base32_str: str) -> TimeSeedComponents:
    """
    Decode a base32 TimeSeed ID.

    Args:
        base32_str: Base32 ID string

    Returns:
        TimeSeedComponents: Decoded components

    Example:
        b32_id = timeseed.generate_base32()
        components = timeseed.decode_base32(b32_id)
    """
    return _get_default_generator().decode_base32(base32_str)


def validate_id(id_value: int) -> bool:
    """
    Validate that an ID could have been generated by the current configuration.

    Args:
        id_value: ID to validate

    Returns:
        bool: True if ID structure is valid

    Example:
        id_val = timeseed.generate()
        assert timeseed.validate_id(id_val) == True
        assert timeseed.validate_id(12345) == False  # Invalid structure
    """
    return _get_default_generator().validate_id(id_value)


def get_info() -> dict:
    """
    Get comprehensive information about the default generator.

    Returns:
        dict: Generator configuration, performance stats, capacity info

    Example:
        info = timeseed.get_info()
        print(f"Machine ID: {info['machine_id']}")
        print(f"IDs generated: {info['performance_stats']['ids_generated']}")
    """
    return _get_default_generator().get_info()


def get_performance_stats() -> dict:
    """
    Get performance statistics for the default generator.

    Returns:
        dict: Performance metrics including generation times and rates

    Example:
        stats = timeseed.get_performance_stats()
        print(f"Average generation time: {stats['avg_generation_time']:.3f}ms")
        print(f"IDs generated: {stats['ids_generated']}")
    """
    return _get_default_generator().get_performance_stats()


def reset_performance_stats() -> None:
    """
    Reset performance statistics for the default generator.

    Example:
        timeseed.reset_performance_stats()
        # Start fresh performance monitoring
    """
    return _get_default_generator().reset_performance_stats()


# Create convenience aliases for common preset configurations
def create_high_throughput_generator() -> TimeSeed:
    """Create a generator optimized for high throughput scenarios."""
    return TimeSeed(PresetConfigs.high_throughput())


def create_long_lifespan_generator() -> TimeSeed:
    """Create a generator optimized for long lifespan (more timestamp bits)."""
    return TimeSeed(PresetConfigs.long_lifespan())


def create_many_datacenters_generator() -> TimeSeed:
    """Create a generator optimized for many datacenters."""
    return TimeSeed(PresetConfigs.many_datacenters())


def create_small_scale_generator() -> TimeSeed:
    """Create a generator optimized for smaller deployments."""
    return TimeSeed(PresetConfigs.small_scale())


# Package metadata for introspection
def version() -> str:
    """Get the package version."""
    return __version__


def author() -> str:
    """Get the package author."""
    return __author__


def description() -> str:
    """Get the package description."""
    return __description__


# Define what gets exported with "from timeseed import *"
__all__ = [
    # Core classes
    "TimeSeed",
    "TimeSeedComponents",
    "TimeSeedConfig",
    "BitAllocation",
    "IDFormat",
    "PresetConfigs",
    # Exceptions
    "TimeSeedError",
    "ConfigurationError",
    "ClockBackwardError",
    "SequenceOverflowError",
    "MachineIdError",
    "DatacenterIdError",
    "DecodingError",
    "FormatError",
    "ValidationError",
    # Configuration functions
    "configure_default",
    "reset_default",
    # Generation functions
    "generate",
    "generate_hex",
    "generate_base62",
    "generate_base32",
    "generate_binary",
    "generate_batch",
    # Decoding functions
    "decode",
    "decode_hex",
    "decode_base62",
    "decode_base32",
    # Utility functions
    "validate_id",
    "get_info",
    "get_performance_stats",
    "reset_performance_stats",
    # Preset generators
    "create_high_throughput_generator",
    "create_long_lifespan_generator",
    "create_many_datacenters_generator",
    "create_small_scale_generator",
    # Utility classes (for advanced users)
    "FormatUtils",
    "TimeUtils",
    "ValidationUtils",
    # Metadata
    "version",
    "author",
    "description",
]
