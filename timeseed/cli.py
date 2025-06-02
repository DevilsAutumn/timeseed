"""
Command Line Interface for TimeSeed.

This module provides a comprehensive CLI for generating, decoding, benchmarking,
and configuring TimeSeed IDs from the command line.
"""

import argparse
import json
import os
import sys
import threading
import time
from typing import List

# Import TimeSeed components
try:
    from timeseed import (  # noqa: F401
        PresetConfigs,
        TimeSeed,
        TimeSeedComponents,
        TimeSeedConfig,
        __author__,
        __description__,
        __version__,
        decode,
        decode_base32,
        decode_base62,
        decode_hex,
        generate,
        generate_base32,
        generate_base62,
        generate_binary,
        generate_hex,
        get_info,
        get_performance_stats,
    )
    from timeseed.exceptions import DecodingError, TimeSeedError  # noqa: F401
    from timeseed.utils import FormatUtils  # noqa: F401
except ImportError as e:
    print(f"Error: Unable to import TimeSeed: {e}")
    print("Make sure TimeSeed is properly installed.")
    sys.exit(1)


class CLIError(Exception):
    """Custom exception for CLI-specific errors."""

    pass


def print_success(message: str) -> None:
    """Print success message with green checkmark."""
    print(f"✅ {message}")


def print_error(message: str) -> None:
    """Print error message with red X."""
    print(f"❌ {message}", file=sys.stderr)


def print_info(message: str) -> None:
    """Print info message with blue info icon."""
    print(f"ℹ️  {message}")


def print_warning(message: str) -> None:
    """Print warning message with yellow warning icon."""
    print(f"⚠️  {message}")


def format_large_number(num: int) -> str:
    """Format large numbers with commas for readability."""
    return f"{num:,}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def create_generator_from_args(args) -> TimeSeed:
    """Create TimeSeed generator from command line arguments."""
    config = None

    # Check for preset configurations
    if hasattr(args, "preset") and args.preset:
        preset_map = {
            "high-throughput": PresetConfigs.high_throughput,
            "long-lifespan": PresetConfigs.long_lifespan,
            "many-datacenters": PresetConfigs.many_datacenters,
            "small-scale": PresetConfigs.small_scale,
        }

        if args.preset in preset_map:
            config = preset_map[args.preset]()
        else:
            raise CLIError(f"Unknown preset: {args.preset}")

    # Check for custom bit allocation
    elif hasattr(args, "timestamp_bits") and any(
        [
            getattr(args, "timestamp_bits", None),
            getattr(args, "machine_bits", None),
            getattr(args, "datacenter_bits", None),
            getattr(args, "sequence_bits", None),
        ]
    ):
        config = TimeSeedConfig.create_custom(
            timestamp_bits=getattr(args, "timestamp_bits", 48),
            machine_bits=getattr(args, "machine_bits", 16),
            datacenter_bits=getattr(args, "datacenter_bits", 16),
            sequence_bits=getattr(args, "sequence_bits", 42),
        )

    # Create generator with optional machine/datacenter IDs
    machine_id = getattr(args, "machine_id", None)
    datacenter_id = getattr(args, "datacenter_id", None)

    return TimeSeed(config, machine_id, datacenter_id)


def cmd_generate(args) -> int:
    """Generate TimeSeed IDs."""
    try:
        generator = create_generator_from_args(args)

        count = getattr(args, "count", 1)
        format_type = getattr(args, "format", "integer")
        output_file = getattr(args, "output", None)

        # Validate format
        valid_formats = ["integer", "hex", "base62", "base32", "binary"]
        if format_type not in valid_formats:
            raise CLIError(
                f"Invalid format '{format_type}'. Valid formats: {', '.join(valid_formats)}"
            )

        print_info(f"Generating {format_large_number(count)} ID(s) in {format_type} format...")

        # Generate IDs
        start_time = time.time()
        ids = []

        for i in range(count):
            if format_type == "integer":
                id_value = generator.generate()
            elif format_type == "hex":
                id_value = generator.generate_hex()
            elif format_type == "base62":
                id_value = generator.generate_base62()
            elif format_type == "base32":
                id_value = generator.generate_base32()
            elif format_type == "binary":
                id_value = generator.generate_binary()

            ids.append(str(id_value))

            # Progress indicator for large batches
            if count > 1000 and (i + 1) % 1000 == 0:
                print(f"Progress: {i + 1:,}/{count:,} ({(i + 1) / count * 100:.1f}%)")

        generation_time = time.time() - start_time

        # Output results
        if output_file:
            with open(output_file, "w") as f:
                for id_value in ids:
                    f.write(f"{id_value}\n")
            print_success(f"Generated {format_large_number(count)} IDs written to {output_file}")
        else:
            for id_value in ids:
                print(id_value)

        # Performance summary
        if count > 1:
            rate = count / generation_time if generation_time > 0 else float("inf")
            print_info(
                f"Generated {format_large_number(count)} IDs in {format_duration(generation_time)} "
                f"({format_large_number(int(rate))} IDs/second)"
            )

        return 0

    except Exception as e:
        print_error(f"Generation failed: {e}")
        return 1


def cmd_decode(args) -> int:
    """Decode TimeSeed IDs."""
    try:
        generator = create_generator_from_args(args)

        ids = args.ids
        input_format = getattr(args, "input_format", "auto")
        output_format = getattr(args, "output_format", "table")

        results = []

        for id_str in ids:
            try:
                # Auto-detect or use specified format
                if input_format == "auto":
                    # Try to detect format based on content
                    if id_str.isdigit():
                        components = generator.decode(int(id_str))
                    elif all(c in "0123456789ABCDEFabcdef" for c in id_str):
                        components = generator.decode_hex(id_str)
                    else:
                        # Try base62 first, then base32
                        try:
                            components = generator.decode_base62(id_str)
                        except DecodingError:
                            components = generator.decode_base32(id_str)
                elif input_format == "integer":
                    components = generator.decode(int(id_str))
                elif input_format == "hex":
                    components = generator.decode_hex(id_str)
                elif input_format == "base62":
                    components = generator.decode_base62(id_str)
                elif input_format == "base32":
                    components = generator.decode_base32(id_str)
                else:
                    raise CLIError(f"Invalid input format: {input_format}")

                results.append((id_str, components))

            except Exception as e:
                print_error(f"Failed to decode '{id_str}': {e}")
                results.append((id_str, None))

        # Output results
        if output_format == "json":
            output = []
            for id_str, components in results:
                if components:
                    output.append({"input": id_str, "components": components.to_dict()})
                else:
                    output.append({"input": id_str, "error": "Failed to decode"})
            print(json.dumps(output, indent=2, default=str))

        else:  # table format
            for id_str, components in results:
                if components:
                    print(f"\nID: {id_str}")
                    print(f"  Timestamp:    {components.timestamp}")
                    print(f"  Generated At: {components.generated_at}")
                    print(f"  Machine ID:   {components.machine_id}")
                    print(f"  Datacenter:   {components.datacenter_id}")
                    print(f"  Sequence:     {components.sequence}")
                else:
                    print(f"\nID: {id_str}")
                    print("  ❌ Failed to decode")

        return 0

    except Exception as e:
        print_error(f"Decoding failed: {e}")
        return 1


def cmd_benchmark(args) -> int:
    """Run performance benchmarks."""
    try:
        generator = create_generator_from_args(args)

        duration = getattr(args, "duration", 10)  # seconds
        threads = getattr(args, "threads", 1)
        format_type = getattr(args, "format", "integer")

        print_info(
            f"Starting benchmark: {duration}s duration, {threads} thread(s), {format_type} format"
        )

        # Benchmark function
        def benchmark_thread(results: List[int], thread_id: int):
            count = 0
            start_time = time.time()
            end_time = start_time + duration

            while time.time() < end_time:
                try:
                    if format_type == "integer":
                        generator.generate()
                    elif format_type == "hex":
                        generator.generate_hex()
                    elif format_type == "base62":
                        generator.generate_base62()
                    elif format_type == "base32":
                        generator.generate_base32()
                    elif format_type == "binary":
                        generator.generate_binary()

                    count += 1

                    # Progress update every second
                    if count % 10000 == 0:
                        elapsed = time.time() - start_time
                        if elapsed >= 1.0:
                            rate = count / elapsed
                            print(f"Thread {thread_id}: {format_large_number(int(rate))} IDs/sec")

                except Exception as e:
                    print_error(f"Thread {thread_id} error: {e}")
                    break

            results[thread_id] = count

        # Run benchmark
        results = [0] * threads
        thread_list = []

        start_time = time.time()

        for i in range(threads):
            thread = threading.Thread(target=benchmark_thread, args=(results, i))
            thread_list.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in thread_list:
            thread.join()

        actual_duration = time.time() - start_time
        total_count = sum(results)

        # Results
        print("\n" + "=" * 50)
        print("BENCHMARK RESULTS")
        print("=" * 50)

        print(f"Duration:     {format_duration(actual_duration)}")
        print(f"Threads:      {threads}")
        print(f"Format:       {format_type}")
        print(f"Total IDs:    {format_large_number(total_count)}")

        if actual_duration > 0:
            total_rate = total_count / actual_duration
            per_thread_rate = total_rate / threads if threads > 0 else 0

            print(f"Total Rate:   {format_large_number(int(total_rate))} IDs/sec")
            print(f"Per Thread:   {format_large_number(int(per_thread_rate))} IDs/sec")

        # Thread breakdown
        if threads > 1:
            print("\nPer-thread results:")
            for i, count in enumerate(results):
                rate = count / actual_duration if actual_duration > 0 else 0
                count_str = format_large_number(count)
                rate_str = format_large_number(int(rate))
                print(f"  Thread {i}: {count_str} IDs ({rate_str} IDs/sec)")

        # Performance stats from generator
        stats = generator.get_performance_stats()
        if stats["ids_generated"] > 0:
            print("\nGenerator stats:")
            print(f"  Average generation time: {stats.get('avg_generation_time', 0):.3f}ms")
            print(f"  Sequence overflows: {stats.get('sequence_overflows', 0)}")
            print(f"  Clock backward events: {stats.get('clock_backward_events', 0)}")

        return 0

    except Exception as e:
        print_error(f"Benchmark failed: {e}")
        return 1


def cmd_info(args) -> int:
    """Display TimeSeed configuration and system information."""
    try:
        generator = create_generator_from_args(args)

        output_format = getattr(args, "format", "table")

        # Get comprehensive info
        info = generator.get_info()

        if output_format == "json":
            print(json.dumps(info, indent=2, default=str))
        else:
            print("TIMESEED CONFIGURATION")
            print("=" * 50)

            # Basic info
            print(f"Version:      {__version__}")
            print(f"Machine ID:   {info['machine_id']}")
            print(f"Datacenter:   {info['datacenter_id']}")

            # Bit allocation
            bit_alloc = info["generator_config"]["bit_allocation"]
            print("\nBit Allocation:")
            print(f"  Timestamp:  {bit_alloc['timestamp_bits']} bits")
            print(f"  Machine:    {bit_alloc['machine_bits']} bits")
            print(f"  Datacenter: {bit_alloc['datacenter_bits']} bits")
            print(f"  Sequence:   {bit_alloc['sequence_bits']} bits")
            print(f"  Total:      {bit_alloc['total_bits']} bits")
            print(f"  Unused:     {bit_alloc['unused_bits']} bits")

            # Capacity
            capacity = info["capacity_info"]
            print("\nCapacity:")
            print(f"  Max machines:     {format_large_number(capacity['max_machines'])}")
            print(f"  Max datacenters:  {format_large_number(capacity['max_datacenters'])}")
            print(f"  IDs per ms:       {format_large_number(capacity['ids_per_millisecond'])}")
            print(f"  Total IDs/ms:     {format_large_number(capacity['total_ids_per_ms'])}")
            print(f"  Timestamp years:  {capacity['timestamp_years']:.1f}")

            # Performance stats
            stats = info["performance_stats"]
            if stats["ids_generated"] > 0:
                print("\nPerformance Stats:")
                print(f"  IDs generated:    {format_large_number(stats['ids_generated'])}")
                print(f"  Avg gen time:     {stats.get('avg_generation_time', 0):.3f}ms")
                print(f"  Sequence overflows: {stats.get('sequence_overflows', 0)}")
                print(f"  Clock events:     {stats.get('clock_backward_events', 0)}")

            # System info
            print("\nSystem Information:")
            try:
                import socket

                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                print(f"  Hostname:     {hostname}")
                print(f"  IP Address:   {ip}")
            except Exception:
                print("  Hostname:     Unable to detect")
                print("  IP Address:   Unable to detect")

        return 0

    except Exception as e:
        print_error(f"Info command failed: {e}")
        return 1


def cmd_config(args) -> int:
    """Configure TimeSeed settings."""
    print_info("Configuration management")

    # Show current environment variables
    env_vars = [
        "TIMESEED_MACHINE_ID",
        "TIMESEED_DATACENTER_ID",
        "TIMESEED_EPOCH_START",
        "TIMESEED_TIMESTAMP_BITS",
        "TIMESEED_MACHINE_BITS",
        "TIMESEED_DATACENTER_BITS",
        "TIMESEED_SEQUENCE_BITS",
    ]

    print("\nEnvironment Variables:")
    for var in env_vars:
        value = os.environ.get(var, "Not set")
        print(f"  {var}: {value}")

    print("\nTo configure TimeSeed, set environment variables:")
    print("  export TIMESEED_MACHINE_ID=42")
    print("  export TIMESEED_DATACENTER_ID=7")

    return 0


def cmd_check(args) -> int:
    """Check if TimeSeed is properly configured for production."""
    try:
        from timeseed.simple_ids import get_configuration_examples, validate_production_readiness

        status = validate_production_readiness()

        print("TIMESEED PRODUCTION READINESS CHECK")
        print("=" * 50)

        if status["production_ready"]:
            print_success("Configuration is production-ready!")
        else:
            print_warning("Configuration needs attention for production use")

        # Show warnings
        if status["warnings"]:
            print("\nIssues found:")
            for warning in status["warnings"]:
                print_warning(warning)

        # Show recommendations
        if status["recommendations"]:
            print("\nRecommendations:")
            for rec in status["recommendations"]:
                print_info(rec)

        # Show current environment
        machine_id = os.environ.get("TIMESEED_MACHINE_ID", "Not set")
        datacenter_id = os.environ.get("TIMESEED_DATACENTER_ID", "Not set")

        print("\nCurrent Environment:")
        print(f"  TIMESEED_MACHINE_ID:    {machine_id}")
        print(f"  TIMESEED_DATACENTER_ID: {datacenter_id}")

        # Show examples if requested
        if getattr(args, "examples", False):
            examples = get_configuration_examples()
            print("\nConfiguration Examples:")
            for _, config in examples.items():
                print(f"\n{config['description']}:")
                for line in config["setup"]:
                    print(f"  {line}")

        return 0 if status["production_ready"] else 1

    except Exception as e:
        print_error(f"Check failed: {e}")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="timeseed",
        description="TimeSeed - High-performance chronologically ordered unique ID generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  timeseed generate                           # Generate single ID
  timeseed generate -n 1000 --format hex     # Generate 1000 hex IDs
  timeseed decode 123456789                   # Decode an ID
  timeseed benchmark -d 30 -t 4               # 30-second benchmark with 4 threads
  timeseed info                               # Show configuration
  
Version: {__version__}
Author: {__author__}
        """,
    )

    parser.add_argument("--version", action="version", version=f"timeseed {__version__}")

    # Global options for generator configuration
    parser.add_argument("--machine-id", type=int, help="Machine ID (0-65535 for default config)")

    parser.add_argument(
        "--datacenter-id", type=int, help="Datacenter ID (0-65535 for default config)"
    )

    parser.add_argument(
        "--preset",
        choices=["high-throughput", "long-lifespan", "many-datacenters", "small-scale"],
        help="Use preset configuration",
    )

    # Custom bit allocation
    parser.add_argument("--timestamp-bits", type=int, help="Timestamp bits")
    parser.add_argument("--machine-bits", type=int, help="Machine ID bits")
    parser.add_argument("--datacenter-bits", type=int, help="Datacenter ID bits")
    parser.add_argument("--sequence-bits", type=int, help="Sequence bits")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate TimeSeed IDs")
    gen_parser.add_argument("-n", "--count", type=int, default=1, help="Number of IDs to generate")
    gen_parser.add_argument(
        "-f",
        "--format",
        choices=["integer", "hex", "base62", "base32", "binary"],
        default="integer",
        help="Output format",
    )
    gen_parser.add_argument("-o", "--output", help="Output file (default: stdout)")

    # Decode command
    decode_parser = subparsers.add_parser("decode", help="Decode TimeSeed IDs")
    decode_parser.add_argument("ids", nargs="+", help="IDs to decode")
    decode_parser.add_argument(
        "--input-format",
        choices=["auto", "integer", "hex", "base62", "base32"],
        default="auto",
        help="Input format (auto-detect by default)",
    )
    decode_parser.add_argument(
        "--output-format", choices=["table", "json"], default="table", help="Output format"
    )

    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run performance benchmarks")
    bench_parser.add_argument(
        "-d", "--duration", type=int, default=10, help="Benchmark duration in seconds"
    )
    bench_parser.add_argument("-t", "--threads", type=int, default=1, help="Number of threads")
    bench_parser.add_argument(
        "-f",
        "--format",
        choices=["integer", "hex", "base62", "base32", "binary"],
        default="integer",
        help="ID format to benchmark",
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show configuration and system information")
    info_parser.add_argument(
        "-f", "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Show configuration options")  # noqa: F841

    # Check command
    check_parser = subparsers.add_parser("check", help="Check production readiness")
    check_parser.add_argument("--examples", action="store_true", help="Show configuration examples")

    return parser


def main() -> int:
    """Main CLI entry point."""
    try:
        parser = create_parser()
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return 0

        # Route to appropriate command handler
        if args.command == "generate":
            return cmd_generate(args)
        elif args.command == "decode":
            return cmd_decode(args)
        elif args.command == "benchmark":
            return cmd_benchmark(args)
        elif args.command == "info":
            return cmd_info(args)
        elif args.command == "config":
            return cmd_config(args)
        elif args.command == "check":
            return cmd_check(args)
        else:
            print_error(f"Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        print_error("Interrupted by user")
        return 130
    except CLIError as e:
        print_error(str(e))
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
