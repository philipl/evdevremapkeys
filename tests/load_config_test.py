#!/usr/bin/env python3
#
# Copyright (c) 2017 Philip Langdale
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import io
import os
import sys

import pytest
import yaml
from evdev import ecodes

from evdevremapkeys.evdevremapkeys import parse_config

spec_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append("{}/..".format(spec_dir))

sample_config_data = """
devices:
- input_name: ''
  input_fn: ''
  output_name: ''
  remappings:
    KEY_A:
    - KEY_A
    KEY_B:
    - code: KEY_A
    KEY_C:
    - code: KEY_A
      value: 1
    KEY_D:
    - code: KEY_A
      value: [1,2]
    KEY_E:
    - code: KEY_A
      param1: p1
      param2: p2
    KEY_Z:
    - modifier_group: mod1
  modifier_groups:
    mod1:
      KEY_A:
      - KEY_F
      KEY_B:
      - code: KEY_F
      KEY_C:
      - code: KEY_F
        value: 2
      KEY_D:
      - code: KEY_F
        value: [1,3]
      KEY_E:
      - code: KEY_F
        param3: p1
        param4: p2
"""


@pytest.fixture
def sample_config():
    config = yaml.safe_load(io.StringIO(sample_config_data))
    return parse_config(config)


def remapping(config, code):
    return config["devices"][0]["remappings"].get(code)


def modified_remapping(config, code):
    return config["devices"][0]["modifier_groups"]["mod1"].get(code)


def test_supports_simple_notation(sample_config):
    mapping = remapping(sample_config, ecodes.KEY_A)
    assert [{"code": 30}] == mapping


def test_supports_advanced_notation(sample_config):
    mapping = remapping(sample_config, ecodes.KEY_B)
    assert [{"code": 30}] == mapping


def test_resolves_single_value(sample_config):
    mapping = remapping(sample_config, ecodes.KEY_C)
    assert [{"code": 30, "value": [1]}] == mapping


def test_accepts_multiple_values(sample_config):
    mapping = remapping(sample_config, ecodes.KEY_D)
    assert [{"code": 30, "value": [1, 2]}] == mapping


def test_accepts_other_parameters(sample_config):
    mapping = remapping(sample_config, ecodes.KEY_E)
    assert [{"code": 30, "param1": "p1", "param2": "p2"}] == mapping


def test_accepts_modifier(sample_config):
    mapping = remapping(sample_config, ecodes.KEY_Z)
    assert [{"modifier_group": "mod1"}] == mapping


def test_mod_group_supports_simple_notation(sample_config):
    mapping = modified_remapping(sample_config, ecodes.KEY_A)
    assert [{"code": 33}] == mapping


def test_mod_group_supports_advanced_notation(sample_config):
    mapping = modified_remapping(sample_config, ecodes.KEY_B)
    assert [{"code": 33}] == mapping


def test_mod_group_resolves_single_value(sample_config):
    mapping = modified_remapping(sample_config, ecodes.KEY_C)
    assert [{"code": 33, "value": [2]}] == mapping


def test_mod_group_accepts_multiple_values(sample_config):
    mapping = modified_remapping(sample_config, ecodes.KEY_D)
    assert [{"code": 33, "value": [1, 3]}] == mapping


def test_mod_group_accepts_other_parameters(sample_config):
    mapping = modified_remapping(sample_config, ecodes.KEY_E)
    assert [{"code": 33, "param3": "p1", "param4": "p2"}] == mapping
