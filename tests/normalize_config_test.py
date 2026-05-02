from __future__ import annotations

import io
from typing import Any

import yaml
from evdev import ecodes

from evdevremapkeys.evdevremapkeys import (
    normalize_config,
    normalize_value,
    parse_config,
    resolve_ecodes,
)


def test_mixed_simple_and_advanced_mappings() -> None:
    remappings: dict[str | int, list[str | int | dict[str, Any]]] = {
        "KEY_A": ["KEY_B", {"code": "KEY_C", "value": [1, 0]}]
    }
    result = normalize_config(remappings)
    assert result == {"KEY_A": [{"code": "KEY_B"}, {"code": "KEY_C", "value": [1, 0]}]}


def test_integer_key_codes_in_input() -> None:
    remappings: dict[str | int, list[str | int | dict[str, Any]]] = {42: [30]}
    result = normalize_config(remappings)
    assert result == {42: [{"code": 30}]}


def test_integer_key_codes_resolve() -> None:
    remappings: dict[str | int, list[dict[str, Any]]] = {42: [{"code": 30}]}
    result = resolve_ecodes(remappings)
    assert result == {42: [{"code": 30}]}


def test_empty_remappings():
    config = yaml.safe_load(
        io.StringIO(
            """
devices:
- input_name: ''
  input_fn: ''
  output_name: ''
  remappings: {}
"""
        )
    )
    result = parse_config(config)
    assert result["devices"][0]["remappings"] == {}


def test_normalize_value_already_list():
    mapping = {"code": "KEY_A", "value": [1, 2]}
    normalize_value(mapping)
    assert mapping["value"] == [1, 2]


def test_normalize_value_single_integer():
    mapping = {"code": "KEY_A", "value": 1}
    normalize_value(mapping)
    assert mapping["value"] == [1]


def test_normalize_value_absent():
    mapping = {"code": "KEY_A"}
    normalize_value(mapping)
    assert "value" not in mapping


def test_resolve_ecodes_type_override() -> None:
    remappings: dict[str | int, list[str | int | dict[str, Any]]] = {
        "KEY_A": [{"code": "KEY_B", "type": "EV_REL"}]
    }
    result = resolve_ecodes(normalize_config(remappings))
    assert result[ecodes.KEY_A] == [{"code": ecodes.KEY_B, "type": ecodes.EV_REL}]


def test_resolve_ecodes_unknown_code() -> None:
    remappings: dict[str | int, list[str | int | dict[str, Any]]] = {
        "KEY_A": [{"code": "KEY_NONEXISTENT"}]
    }
    try:
        resolve_ecodes(normalize_config(remappings))
        assert False, "Should have raised KeyError"
    except KeyError:
        pass


def test_parse_config_no_modifier_groups():
    config = yaml.safe_load(
        io.StringIO(
            """
devices:
- input_name: ''
  input_fn: ''
  output_name: ''
  remappings:
    KEY_A:
    - KEY_B
"""
        )
    )
    result = parse_config(config)
    remappings = result["devices"][0]["remappings"]
    assert remappings == {ecodes.KEY_A: [{"code": ecodes.KEY_B}]}


def test_parse_config_multiple_devices():
    config = yaml.safe_load(
        io.StringIO(
            """
devices:
- input_name: 'dev1'
  input_fn: ''
  output_name: ''
  remappings:
    KEY_A:
    - KEY_B
- input_name: 'dev2'
  input_fn: ''
  output_name: ''
  remappings:
    KEY_C:
    - KEY_D
"""
        )
    )
    result = parse_config(config)
    assert ecodes.KEY_A in result["devices"][0]["remappings"]
    assert ecodes.KEY_C in result["devices"][1]["remappings"]
    assert ecodes.KEY_A not in result["devices"][1]["remappings"]
    assert ecodes.KEY_C not in result["devices"][0]["remappings"]
