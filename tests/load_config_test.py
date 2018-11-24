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


import unittest
import os
import sys
from evdev import ecodes
import pprint

spec_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append('{}/..'.format(spec_dir))
from evdevremapkeys import load_config

class TestLoadConfig(unittest.TestCase):
    def test_supports_simple_notation(self):
        mapping = remapping('config.yaml', ecodes.KEY_A)
        self.assertEqual("[{'code': 30}]", str(mapping))
    def test_supports_advanced_notation(self):
        mapping = remapping('config.yaml', ecodes.KEY_B)
        self.assertEqual("[{'code': 30}]", str(mapping))
    def test_resolves_single_value(self):
        mapping = remapping('config.yaml', ecodes.KEY_C)
        self.assertEqual("[{code: 30,value: [1]}]", pretty(mapping))
    def test_accepts_multiple_values(self):
        mapping = remapping('config.yaml', ecodes.KEY_D)
        self.assertEqual("[{code: 30,value: [1, 2]}]", pretty(mapping))
    def test_accepts_other_parameters(self):
        mapping = remapping('config.yaml', ecodes.KEY_E)
        self.assertEqual("[{code: 30,param1: p1,param2: p2}]", pretty(mapping))
    def test_accepts_complex_parameters(self):
        mapping = remapping('config.yaml', ecodes.KEY_F)
        self.assertEqual("[{code: 30,complex_param: {'duration': 0.2, 'value': [1], "
                         "'complex_param2': {'duration': 0.2, 'value': [1], 'code': [272, 273], "
                         "'repeat': True, 'type': 2}, 'code': 272, 'repeat': True, "
                         "'type': 2},type: 2}]", pretty(mapping))

def remapping(config_name, code):
    config_path = '{}/{}'.format(spec_dir, config_name)
    config = load_config(config_path)
    return config['devices'][0]['remappings'].get(code)

def pretty(mappings):
    def prettymapping(mapping):
        return '{'+','.join(['{}: {}'.format(key, mapping[key]) for key in sorted(mapping.keys())])+'}'
    return '['+','.join([prettymapping(mapping) for mapping in mappings])+']'

suite = unittest.TestLoader().loadTestsFromTestCase(TestLoadConfig)
unittest.TextTestRunner(verbosity=2).run(suite)
