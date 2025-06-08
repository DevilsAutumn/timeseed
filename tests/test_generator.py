import time
from datetime import datetime

import pytest

from tests import (
    TEST_DATACENTER_ID,
    TEST_MACHINE_ID,
    assert_chronological_order,
    assert_no_duplicates,
    assert_valid_base62_format,
    assert_valid_hex_format,
    suppress_warnings,
)
from timeseed import TimeSeed, TimeSeedComponents, TimeSeedConfig
from timeseed.exceptions import (
    DecodingError,
)
from timeseed.utils import FormatUtils


@pytest.mark.generator
class TestTimeSeedGeneration:
    def setup_method(self):
        suppress_warnings()
        self.generator = TimeSeed(machine_id=TEST_MACHINE_ID, datacenter_id=TEST_DATACENTER_ID)

    def test_basic_generation(self):
        id1 = self.generator.generate()
        id2 = self.generator.generate()

        assert isinstance(id1, int)
        assert isinstance(id2, int)
        assert id1 != id2
        assert id1 < id2  # Chronological ordering

    def test_chronological_ordering(self):
        ids = [self.generator.generate() for _ in range(100)]
        assert_chronological_order(ids)

    def test_no_duplicates(self):
        ids = [self.generator.generate() for _ in range(10000)]
        assert_no_duplicates(ids)

    def test_generation_speed_baseline(self):
        start = time.time()
        count = 10000

        for _ in range(count):
            self.generator.generate()

        duration = time.time() - start
        rate = count / duration

        # Should generate at least 10K IDs per second
        assert rate > 10000, f"Generation rate {rate:.0f} IDs/sec too slow"

    def test_id_range_validation(self):
        max_128_bit = (1 << 128) - 1

        for _ in range(100):
            id_val = self.generator.generate()
            assert 0 <= id_val <= max_128_bit

    def test_machine_datacenter_ids_in_generated_ids(self):
        for _ in range(10):
            id_val = self.generator.generate()
            components = self.generator.decode(id_val)

            assert components.machine_id == TEST_MACHINE_ID
            assert components.datacenter_id == TEST_DATACENTER_ID


@pytest.mark.generator
class TestTimeSeedFormats:
    def setup_method(self):
        suppress_warnings()
        self.generator = TimeSeed(machine_id=TEST_MACHINE_ID, datacenter_id=TEST_DATACENTER_ID)

    def test_hex_format(self):
        hex_id = self.generator.generate_hex()
        assert_valid_hex_format(hex_id, 32)

        # Test uppercase/lowercase
        hex_upper = self.generator.generate_hex(uppercase=True)
        hex_lower = self.generator.generate_hex(uppercase=False)

        assert hex_upper.isupper()
        assert hex_lower.islower()

    def test_base62_format(self):
        b62_id = self.generator.generate_base62()
        assert_valid_base62_format(b62_id)

    def test_base32_format(self):
        b32_id = self.generator.generate_base32()
        alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

        assert all(c in alphabet for c in b32_id)
        assert len(b32_id) <= 26

    def test_binary_format(self):
        bin_id = self.generator.generate_binary()

        assert all(c in "01" for c in bin_id)
        assert len(bin_id) == 128

    def test_format_consistency(self):
        id_int = self.generator.generate()

        hex_from_int = self.generator._format_as_hex(id_int)
        b62_from_int = self.generator._format_as_base62(id_int)

        int_from_hex = int(hex_from_int, 16)
        int_from_b62 = FormatUtils.base62_to_int(b62_from_int)

        assert id_int == int_from_hex
        assert id_int == int_from_b62


@pytest.mark.generator
class TestTimeSeedDecoding:
    def setup_method(self):
        suppress_warnings()
        self.generator = TimeSeed(machine_id=TEST_MACHINE_ID, datacenter_id=TEST_DATACENTER_ID)

    def test_basic_decoding(self):
        id_val = self.generator.generate()
        components = self.generator.decode(id_val)

        assert isinstance(components, TimeSeedComponents)
        assert components.machine_id == TEST_MACHINE_ID
        assert components.datacenter_id == TEST_DATACENTER_ID
        assert isinstance(components.timestamp, int)
        assert isinstance(components.sequence, int)
        assert isinstance(components.generated_at, datetime)

    def test_decode_hex(self):
        hex_id = self.generator.generate_hex()
        components = self.generator.decode_hex(hex_id)

        assert components.machine_id == TEST_MACHINE_ID
        assert components.datacenter_id == TEST_DATACENTER_ID

    def test_decode_base62(self):
        b62_id = self.generator.generate_base62()
        components = self.generator.decode_base62(b62_id)

        assert components.machine_id == TEST_MACHINE_ID
        assert components.datacenter_id == TEST_DATACENTER_ID

    def test_decode_base32(self):
        b32_id = self.generator.generate_base32()
        components = self.generator.decode_base32(b32_id)

        assert components.machine_id == TEST_MACHINE_ID
        assert components.datacenter_id == TEST_DATACENTER_ID

    def test_round_trip_consistency(self):
        original_id = self.generator.generate()

        self.generator.decode(original_id)
        # Note: We can't perfectly round-trip due to epoch offset

        # Test hex round trip
        hex_id = self.generator.generate_hex()
        hex_decoded = self.generator.decode_hex(hex_id)
        int_from_hex = int(hex_id, 16)
        int_decoded = self.generator.decode(int_from_hex)

        assert hex_decoded.machine_id == int_decoded.machine_id
        assert hex_decoded.datacenter_id == int_decoded.datacenter_id
        assert hex_decoded.sequence == int_decoded.sequence

    def test_decode_invalid_id(self):
        with pytest.raises(DecodingError):
            self.generator.decode_hex("invalid_hex")

        with pytest.raises(DecodingError):
            self.generator.decode_base62("invalid@base62")

        with pytest.raises(DecodingError):
            self.generator.decode_base32("invalid@base32")

    def test_components_to_dict(self):
        id_val = self.generator.generate()
        components = self.generator.decode(id_val)

        data = components.to_dict()

        assert isinstance(data, dict)
        assert "timestamp" in data
        assert "machine_id" in data
        assert "datacenter_id" in data
        assert "sequence" in data
        assert "generated_at" in data
        assert "epoch_offset_ms" in data


@pytest.mark.generator
class TestTimeSeedValidation:
    def setup_method(self):
        suppress_warnings()
        self.generator = TimeSeed(machine_id=TEST_MACHINE_ID, datacenter_id=TEST_DATACENTER_ID)

    def test_validate_generated_id(self):
        for _ in range(10):
            id_val = self.generator.generate()
            assert self.generator.validate_id(id_val)

    def test_validate_invalid_id(self):
        assert not self.generator.validate_id(-1)
        assert not self.generator.validate_id(2**129)

        max_128_bit = (1 << 128) - 1
        assert not self.generator.validate_id(max_128_bit)


@pytest.mark.generator
class TestTimeSeedConfiguration:
    def test_custom_bit_allocation(self):
        config = TimeSeedConfig.create_custom(
            timestamp_bits=50, machine_bits=10, datacenter_bits=8, sequence_bits=48
        )

        generator = TimeSeed(config, machine_id=100, datacenter_id=50)

        id_val = generator.generate()
        components = generator.decode(id_val)

        assert components.machine_id == 100
        assert components.datacenter_id == 50

        # Test bit allocation limits
        assert generator.config.bit_allocation.max_machine_id == (1 << 10) - 1
        assert generator.config.bit_allocation.max_datacenter_id == (1 << 8) - 1

    def test_invalid_machine_id(self):
        with pytest.raises(ValueError, match="Machine ID.*must be between"):
            TimeSeed(machine_id=70000)

    def test_invalid_datacenter_id(self):
        with pytest.raises(ValueError, match="Datacenter ID.*must be between"):
            TimeSeed(datacenter_id=70000)

    def test_preset_configurations(self):
        from timeseed.config import PresetConfigs

        presets = [
            PresetConfigs.high_throughput(),
            PresetConfigs.long_lifespan(),
            PresetConfigs.many_datacenters(),
            PresetConfigs.small_scale(),
        ]

        for config in presets:
            generator = TimeSeed(config, machine_id=1, datacenter_id=1)
            id_val = generator.generate()
            assert isinstance(id_val, int)


@pytest.mark.generator
class TestTimeSeedInfo:
    def setup_method(self):
        suppress_warnings()
        self.generator = TimeSeed(machine_id=TEST_MACHINE_ID, datacenter_id=TEST_DATACENTER_ID)

    def test_get_info(self):
        info = self.generator.get_info()

        assert isinstance(info, dict)
        assert "generator_config" in info
        assert "machine_id" in info
        assert "datacenter_id" in info
        assert "performance_stats" in info
        assert "capacity_info" in info

        assert info["machine_id"] == TEST_MACHINE_ID
        assert info["datacenter_id"] == TEST_DATACENTER_ID

    def test_performance_stats(self):
        for _ in range(10):
            self.generator.generate()

        stats = self.generator.get_performance_stats()

        assert isinstance(stats, dict)
        assert stats["ids_generated"] == 10
        assert "avg_generation_time" in stats
        assert "generation_times" in stats

    def test_reset_performance_stats(self):
        for _ in range(5):
            self.generator.generate()
        stats_before = self.generator.get_performance_stats()
        assert stats_before["ids_generated"] == 5

        # Reset and check
        self.generator.reset_performance_stats()
        stats_after = self.generator.get_performance_stats()
        assert stats_after["ids_generated"] == 0


@pytest.mark.generator
class TestTimeSeedRepr:
    def test_generator_repr(self):
        suppress_warnings()
        generator = TimeSeed(machine_id=42, datacenter_id=7)
        repr_str = repr(generator)

        assert "TimeSeed" in repr_str
        assert "42" in repr_str
        assert "7" in repr_str
        assert "bits=" in repr_str


def _format_as_hex(self, id_val: int) -> str:
    from timeseed.utils import FormatUtils

    return FormatUtils.int_to_hex(id_val, uppercase=True, min_length=32)


def _format_as_base62(self, id_val: int) -> str:
    from timeseed.utils import FormatUtils

    return FormatUtils.int_to_base62(id_val, min_length=22)


# Monkey patch for testing
TimeSeed._format_as_hex = _format_as_hex
TimeSeed._format_as_base62 = _format_as_base62
