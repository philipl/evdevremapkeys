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


import argparse
import asyncio
import functools
from pathlib import Path
import signal


import daemon
import evdev
from evdev import ecodes, InputDevice, UInput
from xdg import BaseDirectory
import yaml

DEFAULT_RATE = .1  # seconds
DEFAULT_LONG_PRESS_DURATION = .2  # seconds
KEY_DOWN = 1
KEY_UP = 0
repeat_tasks = {}
remapped_tasks = {}
long_press_tasks = {}

@asyncio.coroutine
def handle_events(input, output, remappings):
    while True:
        events = yield from input.async_read()  # noqa
        for event in events:
            if event.type == ecodes.EV_KEY and \
               event.code in remappings:
                remap_event(output, event, remappings)
            else:
                output.write_event(event)
                output.syn()


@asyncio.coroutine
def repeat_event(event, rate, count, codes, values, output):
    if count == 0:
        count = -1
    while count is not 0:
        count -= 1
        write_output(codes, values, event, output)
        yield from asyncio.sleep(rate)

@asyncio.coroutine
def long_press_event(long_press, event, original_code, output):
    long_press_duration = long_press.get('duration', DEFAULT_LONG_PRESS_DURATION)
    long_press_value = long_press.get('value', [KEY_DOWN, KEY_UP])
    long_press_code = long_press.get('code', [])
    if type(long_press_code) is not list:
        long_press_code = [long_press_code]
    long_press_type = long_press.get('type', None)
    repeat = long_press.get('repeat', False)
    rate = long_press.get('rate', DEFAULT_RATE)
    count = 1 if not repeat else long_press.get('count', 0)
    yield from asyncio.sleep(long_press_duration)
    event.type = long_press_type if long_press_type else event.type
    repeat_tasks[original_code] = asyncio.ensure_future(repeat_event(event, rate, count, long_press_code, long_press_value, output))

def write_output(codes, values, event, output):
    for value in values:
        event.value = value
        for code in codes:
            event.code = code
            output.write_event(event)
            output.syn()


def remap_event(output, event, remappings):
    for remapping in remappings[event.code]:
        original_code = event.code
        codes = remapping.get('code', [])
        if type(codes) is not list:
            codes = [codes]
        event.type = remapping.get('type', None) or event.type
        repeat = remapping.get('repeat', False)
        delay = remapping.get('delay', False)
        long_press = remapping.get('long_press', None)
        if not (repeat or delay or long_press):
            values = remapping.get('value', [event.value])
            write_output(codes, values, event, output)
        else:
            is_key_down = event.value is KEY_DOWN
            is_key_up = event.value is KEY_UP

            if not (is_key_up or is_key_down):
                return
            if delay:
                count = remapping.get('count', 0)
                event.code = remapping['code']
                if original_code not in remapped_tasks or remapped_tasks[original_code] == 0:
                    if is_key_down:
                        remapped_tasks[original_code] = count
                else:
                    if is_key_down:
                        remapped_tasks[original_code] -= 1

                if remapped_tasks[original_code] == count:
                    output.write_event(event)
                    output.syn()
            elif long_press:
                if is_key_down:
                    # start long press timer
                    long_press_tasks[original_code] = asyncio.ensure_future(
                        long_press_event(long_press, event, original_code, output))
                if is_key_up:
                    long_press_task = long_press_tasks.get(original_code, None)
                    if long_press_task and long_press_task.done():
                        # long press already handled; just cleanup
                        del long_press_tasks[original_code]
                    if long_press_task and not long_press_task.done():
                        # handle short press
                        long_press_task.cancel()
                        if repeat:
                            rate = remapping.get('rate', DEFAULT_RATE)
                            values = remapping.get('value', [KEY_DOWN, KEY_UP])
                            count = remapping.get('count', 1)
                            asyncio.ensure_future(
                                repeat_event(event, rate, count, codes, values, output))
                            pass
                        else:
                            del long_press_tasks[original_code]
                            write_output(codes, [KEY_DOWN, KEY_UP], event, output) # simulate key press (key_down/key_up)
                    # cleanup any repeating task started during long press handling
                    repeat_task = repeat_tasks.pop(original_code, None)
                    if repeat_task:
                        repeat_task.cancel()

            elif repeat:
                count = remapping.get('count', 0)
                # count > 0  - ignore key-up events
                # count is 0 - repeat until key-up occurs
                ignore_key_up = count > 0

                if ignore_key_up and is_key_up:
                    return
                rate = remapping.get('rate', DEFAULT_RATE)
                repeat_task = repeat_tasks.pop(original_code, None)
                if repeat_task:
                    repeat_task.cancel()
                if is_key_down:
                    values = remapping.get('value', [KEY_DOWN, KEY_UP])
                    repeat_tasks[original_code] = asyncio.ensure_future(
                        repeat_event(event, rate, count, codes, values, output))

# Parses yaml config file and outputs normalized configuration.
# Sample output:
#  'devices': [{
#    'input_fn': '',
#    'input_name': '',
#    'input_phys': '',
#    'output_name': '',
#    'remappings': {
#      42: [{             # Matched key/button code
#        'code': 30,      # Mapped key/button code
#        'type': EV_REL,  # Overrides received event type [optional]
#                         # Defaults to EV_KEY
#        'value': [1, 0], # Overrides received event value [optional].
#                         # If multiple values are specified they will
#                         # be applied in sequence.
#                         # Defaults to the value of received event.
#        'repeat': True,  # Repeat key/button code [optional, default:False]
#        'delay': True,   # Delay key/button output [optional, default:False]
#        'rate': 0.2,     # Repeat rate in seconds [optional, default:0.1]
#        'count': 3       # Repeat/Delay counter [optional, default:0]
#                         # For repeat:
#                         # If count is 0 it will repeat until key/button is depressed
#                         # If count > 0 it will repeat specified number of times
#                         # For delay:
#                         # Will suppress key/button output x times before execution [x = count]
#                         # Ex: count = 1 will execute key press every other time
#      }]
#    }
#  }]
def load_config(config_override):
    conf_path = None
    if config_override is None:
        for dir in BaseDirectory.load_config_paths('evdevremapkeys'):
            conf_path = Path(dir) / 'config.yaml'
            if conf_path.is_file():
                break
        if conf_path is None:
            raise NameError('No config.yaml found')
    else:
        conf_path = Path(config_override)
        if not conf_path.is_file():
            raise NameError('Cannot open %s' % config_override)

    with open(conf_path.as_posix(), 'r') as fd:
        config = yaml.safe_load(fd)
        for device in config['devices']:
            device['remappings'] = normalize_config(device['remappings'])
            device['remappings'] = resolve_ecodes(device['remappings'])

    return config


# Converts general config schema
# {'remappings': {
#     'BTN_EXTRA': [
#         'KEY_Z',
#         'KEY_A',
#         {'code': 'KEY_X', 'value': 1}
#         {'code': 'KEY_Y', 'value': [1,0]]}
#     ]
# }}
# into fixed format
# {'remappings': {
#     'BTN_EXTRA': [
#         {'code': 'KEY_Z'},
#         {'code': 'KEY_A'},
#         {'code': 'KEY_X', 'value': 1}
#         {'code': 'KEY_Y', 'value': [1,0]]}
#     ]
# }}
def normalize_config(remappings):
    norm = {}
    for key, mappings in remappings.items():
        new_mappings = []
        for mapping in mappings:
            if type(mapping) is str:
                new_mappings.append({'code': mapping})
            else:
                new_mappings.append(mapping)
        norm[key] = new_mappings
    return norm

def resolve_ecodes(remappings):
    new_remappings =  {ecodes.ecodes[key]: mappings
            for key, mappings in remappings.items()}
    resolve_inner_ecodes(new_remappings)
    return new_remappings

# Recursively replace ecodes found within nested structure.
def resolve_inner_ecodes(node):
    for node, key in traverse(node):
        value = node[key]
        if key == 'code' and type(value) is list:
            node[key] = [ecodes.ecodes[code] for code in value]
        elif key == 'code' and type(value) is not list:
            node[key] = ecodes.ecodes[value]
        elif key == 'type' and type(value):
            node[key] = ecodes.ecodes[value]
        elif key == 'value' and type(value) is not list:
            node[key] = [value]

def find_input(device):
    name = device.get('input_name', None)
    phys = device.get('input_phys', None)
    fn = device.get('input_fn', None)

    if name is None and phys is None and fn is None:
        raise NameError('Devices must be identified by at least one ' +
                        'of "input_name", "input_phys", or "input_fn"')

    devices = [InputDevice(fn) for fn in evdev.list_devices()]
    for input in devices:
        if name is not None and input.name != name:
            continue
        if phys is not None and input.phys != phys:
            continue
        if fn is not None and input.fn != fn:
            continue
        return input
    return None

# Accumulates list of values found in 'code' elements.
def get_all_codes(node):
    out = set()
    for node, key in traverse(node):
        value = node[key]
        if key == 'code' and type(value) is list:
            out.update(value)
        elif key == 'code' and type(value) is not list:
            out.add(value)
    return out

# Iterates nested structure and emits (node,key) events for each node.
def traverse(node):
    if type(node) is list:
        for item in node:
            yield from traverse(item)
    elif type(node) is dict:
        for key, value in node.items():
            yield (node, key)
            if type(value) in [dict, list]:
                yield from traverse(value)

def register_device(device):
    input = find_input(device)
    if input is None:
        raise NameError("Can't find input device")
    input.grab()

    caps = input.capabilities()
    # EV_SYN is automatically added to uinput devices
    del caps[ecodes.EV_SYN]

    remappings = device['remappings']
    extended = set(caps[ecodes.EV_KEY])

    extended.update(get_all_codes(remappings))
    caps[ecodes.EV_KEY] = list(extended)

    output = UInput(caps, name=device['output_name'])

    asyncio.ensure_future(handle_events(input, output, remappings))


@asyncio.coroutine
def shutdown(loop):
    tasks = [task for task in asyncio.Task.all_tasks() if task is not
             asyncio.tasks.Task.current_task()]
    list(map(lambda task: task.cancel(), tasks))
    yield from asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


def run_loop(args):
    config = load_config(args.config_file)
    for device in config['devices']:
        register_device(device)

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM,
                            functools.partial(asyncio.ensure_future,
                                              shutdown(loop)))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.remove_signal_handler(signal.SIGTERM)
        loop.run_until_complete(asyncio.ensure_future(shutdown(loop)))
    finally:
        loop.close()


def list_devices():
    devices = [InputDevice(fn) for fn in evdev.list_devices()]
    for device in reversed(devices):
        yield [device.fn, device.phys, device.name]

def read_events(req_device):
    for device in list_devices():
        # Look in all 3 identifiers + event number
        if req_device in device or req_device == device[0].replace("/dev/input/event", ""):
            found = evdev.InputDevice(device[0])

    if 'found' not in locals():
        print("Device not found. \nPlease use --list-devices to view a list of available devices.")
        return

    print(found)
    print("To stop, press Ctrl-C")

    for event in found.read_loop():
        try:
            if event.type == evdev.ecodes.EV_KEY:
                categorized = evdev.categorize(event)
                if categorized.keystate == 1:
                    keycode = categorized.keycode if type(categorized.keycode) is str else \
                            " | ".join(categorized.keycode)
                    print("Key pressed: %s (%s)" % (keycode, categorized.scancode))
        except KeyError:
            if event.value:
                print("Unknown key (%s) has been pressed." % event.code)
            else:
                print("Unknown key (%s) has been released." % event.code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Re-bind keys for input devices')
    parser.add_argument('-d', '--daemon',
                        help='Run as a daemon', action='store_true')
    parser.add_argument('-f', '--config-file',
                        help='Config file that overrides default location')
    parser.add_argument('-l', '--list-devices', action='store_true',
                        help='List input devices by name and physical address')
    parser.add_argument('-e', '--read-events', metavar='EVENT_ID',
                        help='Read events from an input device by either name, physical address or number.')

    args = parser.parse_args()
    if args.list_devices:
        print("\n".join(['%s:\t"%s" | "%s' % (fn, phys, name) for (fn, phys, name) in list_devices()]))
    elif args.read_events:
        read_events(args.read_events)
    elif args.daemon:
        with daemon.DaemonContext():
            run_loop(args)
    else:
        run_loop(args)
