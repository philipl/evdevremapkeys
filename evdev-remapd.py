#!/usr/bin/env python3
#
# MIT License
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


import asyncio
from pathlib import Path


from evdev import InputDevice, categorize, ecodes
import uinput


@asyncio.coroutine
def handle_events(device, udev):
    while True:
        events = yield from device.async_read()
        for event in events:
            if event.type == ecodes.EV_KEY and \
               event.code == ecodes.BTN_RIGHT and \
               event.value == 1:
                do_raise(udev)
            elif event.type == ecodes.EV_KEY and \
                event.code == ecodes.BTN_EXTRA and \
                event.value == 1:
                do_lower(udev)
            elif event.type == ecodes.EV_KEY and \
                event.code == ecodes.BTN_FORWARD and \
                event.value == 1:
                do_scale(udev)


def do_raise(udev):
    udev.emit_combo([
        uinput.KEY_LEFTMETA,
        uinput.KEY_A,
    ])


def do_lower(udev):
    udev.emit_combo([
        uinput.KEY_LEFTMETA,
        uinput.KEY_Z,
    ])


def do_scale(udev):
    udev.emit_combo([
        uinput.KEY_LEFTMETA,
        uinput.KEY_S,
    ])


def find_mouse():
    p = Path('/dev/input')
    for d in p.glob('event*'):
        device = InputDevice(d.as_posix())
        if device.name == 'Kingsis Peripherals Evoluent VerticalMouse 4':
            return device
    return None


def run_loop():
    device = find_mouse()
    if device is None:
        print("Can't find mouse")
        return
    device.grab()

    udev = uinput.Device([
        uinput.KEY_A,
        uinput.KEY_S,
        uinput.KEY_Z,
        uinput.KEY_LEFTMETA,
    ])

    asyncio.async(handle_events(device, udev))
    loop = asyncio.get_event_loop()
    loop.run_forever()


if __name__ == '__main__':
    run_loop()
