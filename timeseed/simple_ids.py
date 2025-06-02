"""
Simple and reliable ID resolution for TimeSeed.

This module provides a clean, predictable approach to machine and datacenter ID
resolution with only three strategies: explicit, environment, and random.
"""

import os
import random
import warnings
from typing import Optional


def resolve_machine_id(explicit_id: Optional[int] = None, max_value: int = 65535) -> int:
    """
    Resolve machine ID using simple, reliable strategy.

    Priority:
    1. Explicit ID parameter (highest priority)
    2. TIMESEED_MACHINE_ID environment variable
    3. Random ID with warning (development only)

    Args:
        explicit_id: Explicitly provided machine ID
        max_value: Maximum allowed machine ID value

    Returns:
        int: Machine ID between 0 and max_value

    Raises:
        ValueError: If explicit_id is out of range
    """
    # 1. Explicit ID (highest priority)
    if explicit_id is not None:
        if not (0 <= explicit_id <= max_value):
            raise ValueError(f"Machine ID {explicit_id} must be between 0 and {max_value}")
        return explicit_id

    # 2. Environment variable
    env_id = os.environ.get("TIMESEED_MACHINE_ID")
    if env_id:
        try:
            machine_id = int(env_id)
            if not (0 <= machine_id <= max_value):
                warnings.warn(
                    f"TIMESEED_MACHINE_ID={machine_id} is out of range [0, {max_value}]. "
                    f"Using {machine_id % (max_value + 1)} instead.",
                    UserWarning,
                )
                return machine_id % (max_value + 1)
            return machine_id
        except ValueError:
            warnings.warn(
                f"TIMESEED_MACHINE_ID='{env_id}' is not a valid integer. Using random machine ID.",
                UserWarning,
            )

    # 3. Random fallback with warning
    machine_id = random.randint(0, max_value)
    warnings.warn(
        f"Using random machine ID ({machine_id}). "
        "For production, set TIMESEED_MACHINE_ID environment variable or "
        "pass machine_id parameter to ensure consistent IDs.",
        UserWarning,
    )
    return machine_id


def resolve_datacenter_id(explicit_id: Optional[int] = None, max_value: int = 65535) -> int:
    """
    Resolve datacenter ID using simple, reliable strategy.

    Priority:
    1. Explicit ID parameter (highest priority)
    2. TIMESEED_DATACENTER_ID environment variable
    3. Random ID with warning (development only)

    Args:
        explicit_id: Explicitly provided datacenter ID
        max_value: Maximum allowed datacenter ID value

    Returns:
        int: Datacenter ID between 0 and max_value

    Raises:
        ValueError: If explicit_id is out of range
    """
    # 1. Explicit ID (highest priority)
    if explicit_id is not None:
        if not (0 <= explicit_id <= max_value):
            raise ValueError(f"Datacenter ID {explicit_id} must be between 0 and {max_value}")
        return explicit_id

    # 2. Environment variable
    env_id = os.environ.get("TIMESEED_DATACENTER_ID")
    if env_id:
        try:
            datacenter_id = int(env_id)
            if not (0 <= datacenter_id <= max_value):
                warnings.warn(
                    f"TIMESEED_DATACENTER_ID={datacenter_id} is out of range [0, {max_value}]. "
                    f"Using {datacenter_id % (max_value + 1)} instead.",
                    UserWarning,
                )
                return datacenter_id % (max_value + 1)
            return datacenter_id
        except ValueError:
            warnings.warn(
                f"TIMESEED_DATACENTER_ID='{env_id}' is not a valid integer. "
                "Using random datacenter ID.",
                UserWarning,
            )

    # 3. Random fallback with warning
    datacenter_id = random.randint(0, max_value)
    warnings.warn(
        f"Using random datacenter ID ({datacenter_id}). "
        "For production, set TIMESEED_DATACENTER_ID environment variable or "
        "pass datacenter_id parameter to ensure consistent IDs.",
        UserWarning,
    )
    return datacenter_id


def validate_production_readiness() -> dict:
    """
    Check if TimeSeed is properly configured for production use.

    Returns:
        dict: Configuration status and recommendations
    """
    status = {"production_ready": True, "warnings": [], "recommendations": []}

    # Check machine ID configuration
    machine_id_set = os.environ.get("TIMESEED_MACHINE_ID") is not None

    if not machine_id_set:
        status["production_ready"] = False
        status["warnings"].append("Machine ID not configured")
        status["recommendations"].append(
            "Set TIMESEED_MACHINE_ID environment variable or pass machine_id parameter"
        )

    # Check datacenter ID configuration
    datacenter_id_set = os.environ.get("TIMESEED_DATACENTER_ID") is not None

    if not datacenter_id_set:
        status["production_ready"] = False
        status["warnings"].append("Datacenter ID not configured")
        status["recommendations"].append(
            "Set TIMESEED_DATACENTER_ID environment variable or pass datacenter_id parameter"
        )

    if status["production_ready"]:
        status["recommendations"].append(
            "Configuration looks good! Both machine and datacenter IDs are set."
        )
    else:
        status["recommendations"].append(
            "Random IDs are fine for development but not recommended for production."
        )

    return status


def get_configuration_examples() -> dict:
    """
    Get examples of how to configure TimeSeed for different environments.

    Returns:
        dict: Configuration examples for various deployment scenarios
    """
    return {
        "development": {
            "description": "Local development - random IDs are OK",
            "setup": ["# No configuration needed", "# TimeSeed will use random IDs with warnings"],
        },
        "production_simple": {
            "description": "Simple production deployment",
            "setup": ["export TIMESEED_MACHINE_ID=1", "export TIMESEED_DATACENTER_ID=1"],
        },
        "production_distributed": {
            "description": "Multi-machine, multi-datacenter deployment",
            "setup": [
                "# Machine 1 in DC 1",
                "export TIMESEED_MACHINE_ID=1",
                "export TIMESEED_DATACENTER_ID=1",
                "",
                "# Machine 2 in DC 1",
                "export TIMESEED_MACHINE_ID=2",
                "export TIMESEED_DATACENTER_ID=1",
                "",
                "# Machine 1 in DC 2",
                "export TIMESEED_MACHINE_ID=1",
                "export TIMESEED_DATACENTER_ID=2",
            ],
        },
        "docker": {
            "description": "Docker deployment with environment variables",
            "setup": [
                "docker run -e TIMESEED_MACHINE_ID=42 \\",
                "           -e TIMESEED_DATACENTER_ID=7 \\",
                "           myapp",
            ],
        },
        "kubernetes": {
            "description": "Kubernetes deployment",
            "setup": [
                "apiVersion: apps/v1",
                "kind: Deployment",
                "metadata:",
                "  name: myapp",
                "spec:",
                "  template:",
                "    spec:",
                "      containers:",
                "      - name: myapp",
                "        env:",
                "        - name: TIMESEED_MACHINE_ID",
                '          value: "42"',
                "        - name: TIMESEED_DATACENTER_ID",
                '          value: "7"',
            ],
        },
        "programmatic": {
            "description": "Set IDs programmatically in code",
            "setup": [
                "from timeseed import TimeSeed",
                "",
                "# Explicit configuration",
                "generator = TimeSeed(machine_id=42, datacenter_id=7)",
                "",
                "# Or configure the default generator",
                "import timeseed",
                "timeseed.configure_default(machine_id=42, datacenter_id=7)",
            ],
        },
    }
