import os
import tempfile
from unittest.mock import patch

import pytest
from evdev import ecodes

from evdevremapkeys.evdevremapkeys import load_config


def test_valid_config_file_via_override():
    config_content = """
devices:
- input_name: 'test'
  input_fn: '/dev/input/event0'
  output_name: 'remap-test'
  remappings:
    KEY_A:
    - KEY_B
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        try:
            config = load_config(f.name)
            assert len(config["devices"]) == 1
            assert ecodes.KEY_A in config["devices"][0]["remappings"]
        finally:
            os.unlink(f.name)


def test_override_path_does_not_exist():
    with pytest.raises(NameError, match="Cannot open"):
        load_config("/nonexistent/path/config.yaml")


def test_no_override_no_xdg_config():
    with patch(
        "evdevremapkeys.evdevremapkeys.BaseDirectory.load_config_paths",
        return_value=iter([]),
    ):
        with pytest.raises(NameError, match="No config.yaml found"):
            load_config(None)
