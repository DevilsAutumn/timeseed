# TimeSeed 🌱⏰
[![PyPI Downloads](https://static.pepy.tech/badge/timeseed)](https://pepy.tech/projects/timeseed)
[![Version](https://img.shields.io/badge/version-0.1.1-blue.svg)](https://github.com/devilsautumn/timeseed)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/devilsautumn/timeseed/blob/main/LICENSE)

TimeSeed is a high-performance Python library and CLI tool for generating chronologically ordered unique identifiers with guaranteed ordering and configurable bit allocation. Unlike fixed-format ID generators, TimeSeed lets you balance timestamp precision, sequence capacity, and randomness based on your specific needs.

## Why TimeSeed?

- **Strict Chronological Order**: TimeSeed guarantees perfect chronological ordering
- **Multiple Output Formats**: Generate IDs as integers, hex, base62, base32, or binary strings  
- **Configurable Architecture**: Adjust timestamp precision, sequence bits, and randomness to fit your use case
- **High Performance**: Thread-safe with optimized algorithm for high-throughput scenarios
- **Comprehensive CLI**: Full command-line interface for generation, decoding, benchmarking, and format conversion
- **Zero Dependencies**: Pure Python with no external requirements

## Perfect For:
- Database primary keys that need temporal ordering
- Distributed systems requiring coordination-free ID generation  
- Event sourcing and audit logs
- URL-safe identifiers with time-based sorting
- Migration from auto-increment IDs while preserving order

## Fun facts about TimeSeed

With default configuration:

- **128-bit ID space** supports 4.3 billion machines (2^32) each generating 4.4 trillion IDs per millisecond
- **Generation rate** of 10 million IDs/second would take 10^23 years to exhaust - that's 7 trillion times the universe's age
- **Sequence space per millisecond** (2^42) exceeds total IPv4 address space (2^32) by a factor of 1,024
- **Generated 1 billion IDs?** You've used only 0.00000000000000000000000000029% of the total capacity


## Installation

```bash
pip install timeseed
```

## Quick Start

### Python Library

```python
import timeseed

# Generate IDs in different formats
id_int = timeseed.generate()                    # 128-bit integer
id_hex = timeseed.generate_hex()                # 32-char hex string
id_b62 = timeseed.generate_base62()             # 22-char URL-safe base62
id_b32 = timeseed.generate_base32()             # 26-char base32
id_bin = timeseed.generate_binary()             # 128-char binary string

# Decode IDs to see components
components = timeseed.decode(id_int)
print(f"Generated at: {components.generated_at}")
print(f"Machine: {components.machine_id}")
print(f"Datacenter: {components.datacenter_id}")
print(f"Sequence: {components.sequence}")

# Advanced configuration
from timeseed import TimeSeed, TimeSeedConfig

config = TimeSeedConfig.create_custom(
    timestamp_bits=50,
    machine_bits=10, 
    datacenter_bits=8,
    sequence_bits=48
)
generator = TimeSeed(config, machine_id=42, datacenter_id=7)
custom_id = generator.generate()
```

### Command Line Interface

```bash
# Generate single ID
timeseed generate

# Generate multiple IDs in different formats
timeseed generate -n 1000 --format hex
timeseed generate -n 100 --format base62 -o ids.txt

# Convert between formats by decoding and re-encoding
timeseed decode 12345678901234567890

# Get ID components in JSON format
timeseed decode --output-format json 12345678901234567890

# System information and configuration
timeseed info
timeseed check --examples

# Performance benchmarking
timeseed benchmark -d 30 -t 4    # 30 seconds, 4 threads
timeseed benchmark --format hex  # Test hex generation speed

# Custom configuration
timeseed --machine-id 42 --datacenter-id 7 generate
timeseed --preset high-throughput generate -n 1000

# Custom bit allocation
timeseed --timestamp-bits 50 --machine-bits 10 \
         --datacenter-bits 8 --sequence-bits 48 \
         generate --format base62
```

## Format Conversion Capabilities

TimeSeed supports conversion between multiple formats both through the Python API and CLI:

### Supported Formats
- **Integer**: 128-bit integer (default)
- **Hex**: 32-character hexadecimal string (uppercase/lowercase)
- **Base62**: 22-character URL-safe string (0-9, A-Z, a-z)
- **Base32**: 26-character Crockford base32 string
- **Binary**: 128-character binary string (0s and 1s)

### CLI Format Conversion Examples

```bash
# Generate in different formats
timeseed generate --format integer    # 123456789012345678901234567890
timeseed generate --format hex        # A1B2C3D4E5F6789012345678ABCDEF01  
timeseed generate --format base62     # 2jk3Nm5pQ8rS1tU7vW9xYz
timeseed generate --format base32     # A1B2C3D4E5F6G7H8J9K0M1N2P3
timeseed generate --format binary     # 10101000101100110011010...

# Decode any format (auto-detection)
timeseed decode 123456789012345678901234567890
timeseed decode A1B2C3D4E5F6789012345678ABCDEF01
timeseed decode 2jk3Nm5pQ8rS1tU7vW9xYz

# Specify input format explicitly
timeseed decode --input-format hex A1B2C3D4E5F6789012345678ABCDEF01
timeseed decode --input-format base62 2jk3Nm5pQ8rS1tU7vW9xYz

# Get all format representations via Python API
python -c "
import timeseed
id_val = timeseed.generate()
generator = timeseed.TimeSeed()
formats = generator.get_all_formats(id_val)
for fmt, value in formats.items():
    print(f'{fmt}: {value}')
"
```

## Configuration Examples

### Environment Variables

```bash
# Set machine and datacenter IDs
export TIMESEED_MACHINE_ID=42
export TIMESEED_DATACENTER_ID=7

# Custom bit allocation
export TIMESEED_TIMESTAMP_BITS=50
export TIMESEED_MACHINE_BITS=10
export TIMESEED_DATACENTER_BITS=8
export TIMESEED_SEQUENCE_BITS=48

# Then use CLI normally
timeseed generate -n 100 --format hex
```

### Preset Configurations

```bash
# High throughput (more sequence bits)
timeseed --preset high-throughput generate

# Long lifespan (more timestamp bits)  
timeseed --preset long-lifespan generate

# Many datacenters (more datacenter bits)
timeseed --preset many-datacenters generate

# Small scale (balanced for smaller deployments)
timeseed --preset small-scale generate
```

## Default Bit Allocation

- **48 bits**: Timestamp (~8920 years from epoch)
- **16 bits**: Machine ID (65,536 machines)  
- **16 bits**: Datacenter ID (65,536 datacenters)
- **42 bits**: Sequence (4.4 trillion IDs per millisecond)
- **6 bits**: Reserved for future use

Total: 128 bits

## Development

To set up the development environment:

```bash
# Fork and Clone the repository
git clone https://github.com/<your-username>/timeseed.git
cd timeseed

# Install in development mode
pip install -e ".[dev]"

# Check production readiness
python -m timeseed.cli check --examples

# Pre-commit hooks
pre-commit install  
```

## CLI Help

```bash
# Get comprehensive help
timeseed --help

# Command-specific help
timeseed generate --help
timeseed decode --help
timeseed benchmark --help
timeseed info --help
```

## Performance

TimeSeed is designed for high-performance ID generation:

- Thread-safe with minimal locking
- Optimized bit operations
- Configurable sequence overflow handling
- Built-in performance monitoring
- Benchmarking tools included

Run benchmarks to test on your system:

```bash
timeseed benchmark -d 10 -t 4  # 10 seconds, 4 threads
```

## Contributing

Contributions are welcome! Please feel free to [open an issue](https://github.com/DevilsAutumn/timeseed/issues/new) or submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/DevilsAutumn/timeseed/blob/main/LICENSE) file for details.
