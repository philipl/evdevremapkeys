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
from concurrent.futures import CancelledError
import functools
from pathlib import Path
import signal


from evdev import InputDevice, UInput, categorize, ecodes

remappings = {
    ecodes.BTN_RIGHT: [ecodes.KEY_LEFTMETA, ecodes.KEY_A],
    ecodes.BTN_EXTRA: [ecodes.KEY_LEFTMETA, ecodes.KEY_Z],
    ecodes.BTN_FORWARD: [ecodes.KEY_LEFTMETA, ecodes.KEY_W],
    ecodes.BTN_MIDDLE: [ecodes.BTN_RIGHT],
    ecodes.BTN_SIDE: [ecodes.BTN_MIDDLE],
}


@asyncio.coroutine
def handle_events(device, remap_dev):
    while True:
        events = yield from device.async_read()  # noqa
        for event in events:
            if event.type == ecodes.EV_KEY and \
               event.code in remappings:
                remap_event(remap_dev, event)
            else:
                remap_dev.write_event(event)
                remap_dev.syn()


def remap_event(remap_dev, event):
    for code in remappings[event.code]:
        event.code = code
        remap_dev.write_event(event)
    remap_dev.syn()


def find_mouse():
    p = Path('/dev/input')
    for d in p.glob('event*'):
        device = InputDevice(d.as_posix())
        if device.name == 'Kingsis Peripherals Evoluent VerticalMouse 4':
            return device
    return None


@asyncio.coroutine
def shutdown(loop):
    tasks = [task for task in asyncio.Task.all_tasks() if task is not
             asyncio.tasks.Task.current_task()]
    list(map(lambda task: task.cancel(), tasks))
    results = yield from asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


def run_loop():
    mouse = find_mouse()
    if mouse is None:
        print("Can't find mouse")
        return
    mouse.grab()

    caps = mouse.capabilities()
    # EV_SYN is automatically added to uinput devices
    del caps[ecodes.EV_SYN]

    extended = set(caps[ecodes.EV_KEY])
    [extended.update(keys) for keys in remappings.values()]
    caps[ecodes.EV_KEY] = list(extended)

    remap_dev = UInput(caps, name='remap-mouse')

    asyncio.ensure_future(handle_events(mouse, remap_dev))
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
        mouse.ungrab()


if __name__ == '__main__':
    run_loop()
