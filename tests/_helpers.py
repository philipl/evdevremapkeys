from typing import Any, cast

from evdevremapkeys.evdevremapkeys import Device, Remapping


def remapping(**kwargs: Any) -> Remapping:
    """Build a Remapping TypedDict with arbitrary fields."""
    return cast(Remapping, kwargs)


def device(**overrides: Any) -> Device:
    """Build a Device TypedDict with sensible defaults filled in."""
    base: dict[str, Any] = {
        "input_name": None,
        "input_phys": None,
        "input_fn": None,
        "output_name": "",
        "remappings": {},
        "modifier_groups": {},
    }
    base.update(overrides)
    return cast(Device, base)
