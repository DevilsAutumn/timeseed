# TimeSeed Documentation

**High-performance chronologically ordered unique ID generator for distributed systems**

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/devilsautumn/timeseed)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/devilsautumn/timeseed/blob/main/LICENSE)

## What is TimeSeed?

TimeSeed generates 128-bit unique identifiers with **guaranteed chronological ordering**. Unlike UUID4 or other random ID generators, TimeSeed IDs are always ordered by time, making them perfect for database primary keys and distributed systems.

## Key Features

- **Chronologically ordered** - IDs are always sorted by generation time
- **Multiple formats** - Integer, hex, base62, base32, and binary output
- **High performance** - Thread-safe with optimized algorithms
- **Zero dependencies** - Pure Python with no external requirements
- **Configurable** - Adjust bit allocation for your specific needs

## Quick Example

```python
import timeseed

# Generate IDs - they're always chronologically ordered
id1 = timeseed.generate()              # 128-bit integer
id2 = timeseed.generate_hex()          # 32-char hex string  
id3 = timeseed.generate_base62()       # 22-char URL-safe string

assert id1 < timeseed.generate()  # Always true!

# Decode IDs to see components
components = timeseed.decode(id1)
print(f"Generated at: {components.generated_at}")
print(f"Machine: {components.machine_id}")
```

## ID Structure

TimeSeed uses a 128-bit structure with sensible defaults:

```
┌─────────────┬──────────────┬──────────────┬─────────────┬──────────┐
│ Timestamp   │ Machine ID   │ Datacenter   │ Sequence    │ Reserved │
│ 48 bits     │ 16 bits      │ 16 bits      │ 42 bits     │ 6 bits   │
│ (878 years) │ (65K machines)│ (65K DCs)   │ (4.4T/ms)   │ (future) │
└─────────────┴──────────────┴──────────────┴─────────────┴──────────┘
```

This provides 878 years of range with 4.4 trillion IDs per millisecond per machine.

## Installation

```bash
pip install timeseed
```

## Perfect For

- Database primary keys that need temporal ordering
- Distributed systems requiring coordination-free ID generation
- Event sourcing and audit logs
- URL-safe identifiers with time-based sorting
- Migration from auto-increment IDs while preserving order

---

**Version**: 0.1.1 | **Author**: Bhuvnesh Sharma | **License**: MIT
