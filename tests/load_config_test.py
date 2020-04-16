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


from evdev import ecodes
from evdevremapkeys.evdevremapkeys import load_config


def test_supports_simple_notation():
    mapping = remapping('config.yaml', ecodes.KEY_A)
    assert [{'code': 30}] == mapping


def test_supports_advanced_notation():
    mapping = remapping('config.yaml', ecodes.KEY_B)
    assert [{'code': 30}] == mapping


def test_resolves_single_value():
    mapping = remapping('config.yaml', ecodes.KEY_C)
    assert [{'code': 30, 'value': [1]}] == mapping


def test_accepts_multiple_values():
    mapping = remapping('config.yaml', ecodes.KEY_D)
    assert [{'code': 30, 'value': [1, 2]}] == mapping


def test_accepts_other_parameters():
    mapping = remapping('config.yaml', ecodes.KEY_E)
    assert [{'code': 30, 'param1': 'p1', 'param2': 'p2'}] == mapping


def test_accepts_modifier():
    mapping = remapping('config.yaml', ecodes.KEY_Z)
    assert [{'modifier_group': 'mod1'}] == mapping


def test_mod_group_supports_simple_notation():
    mapping = modified_remapping('config.yaml', ecodes.KEY_A)
    assert [{'code': 33}] == mapping


def test_mod_group_supports_advanced_notation():
    mapping = modified_remapping('config.yaml', ecodes.KEY_B)
    assert [{'code': 33}] == mapping


def test_mod_group_resolves_single_value():
    mapping = modified_remapping('config.yaml', ecodes.KEY_C)
    assert [{'code': 33, 'value': [2]}] == mapping


def test_mod_group_accepts_multiple_values():
    mapping = modified_remapping('config.yaml', ecodes.KEY_D)
    [{'code': 33, 'value': [1, 3]}] == mapping


def test_mod_group_accepts_other_parameters():
    mapping = modified_remapping('config.yaml', ecodes.KEY_E)
    assert [{'code': 33, 'param3': 'p1', 'param4': 'p2'}] == mapping


def remapping(config_name, code):
    config_path = '{}/{}'.format('tests', config_name)
    config = load_config(config_path)
    return config['devices'][0]['remappings'].get(code)


def modified_remapping(config_name, code):
    config_path = '{}/{}'.format('tests', config_name)
    config = load_config(config_path)
    return config['devices'][0]['modifier_groups']['mod1'].get(code)
