# evdevremapkeys

A daemon to remap key events on linux input devices

## Motivation

The remapping of input key events is an problem, and one that has been solved
at many levels over the years. On a traditional X11 desktop, the usual way
to do this is with xbindkeys; it's simple and effective and you shouldn't
try and write something different.

However, with the shift to [Wayland](https://wayland.freedesktop.org/), we
have a problem. Wayland obviously isn't [X11](https://www.x.org) so any X11
based remapping utility isn't going to work. Wayland compositors typically use
[libinput](https://www.freedesktop.org/wiki/Software/libinput/) to manage
input events, but while libinput supports remapping conceptually, it does not
expose any mechanism to configure it. This is left as an exercise to the
compositor and neither [Weston](https://github.com/wayland-project/weston)
nor [Mutter](https://github.com/GNOME/mutter) expose remapping.

So where does this leave us? If we are to provide a remapping mechanism that
is not dependent on the compositor, it must run below libinput, which means
it must work with the linux input subsystem. And so, here we are.

## Technical approach

There's only one real sane approach to doing event remapping at the
[input](https://www.kernel.org/doc/html/latest/input/input.html) subsystem
level: Read events from physical input devices, and then generate new input
events on a virtual device managed through
[uinput](https://www.kernel.org/doc/html/latest/input/uinput.html).

One legitimate question is whether the virtual device attempts to fully
replicate the original physical device, just with remapped events, or whether
it's a dedicate device that only emits the new events which leaving the
physical device free to send events directly to other clients.

Depending on your exact use-case, you might be able to leave the original
physical device as-is, but for me, it turned out that I had to swallow the
original events because they will be picked up by libinput and then trigger
actions in my desktop environment.

To avoid this, you have to take a grab on the physical device, so no other
client receives events, and then forward all un-modified events through
your virtual device. It's annoying but unavoidable - you can't hide individual
events from other clients.

## Why not evmapd

There is an existing project called [evmapd](https://github.com/thkala/evmapd)
which is, obstentibly, exactly what we're looking for - a daemon that will
take input events from one device, and then generate new events on a different
uinput based device. I made a serious attempt at using it but ultimately found
it too limiting to rely on:
* It doesn't support 1:N mappings, which I particularly care about
  * eg: Mapping a mouse button to a key combination like `Super+A`
* It relies on an obscure and hard to obtain library for command line
  argument handling (libcfg+)
* It's written in C, which I will always respect, but which doesn't add much
  value to this kind of program
* It's doesn't look actively maintained; it solved whatever problem the author
  originally had, and that was it.

Having said all that, it has a set of capabilities to handle remappings that
are not from keys to other keys - particuarly creating virtual joystick axes
from key events. If you care about those capabilities, you should use evmapd.
I'm not going to expand beyond key to key remappings.

## Requirements

* Python >= 3.4 (for [asyncio](https://docs.python.org/3/library/asyncio.html))
* [Python evdev binding](https://pypi.python.org/pypi/evdev) >= 0.7.0

## Limitations

* Obviously, it's currently completely hard-coded for my specific use-case,
  which means hard-coded device detection and remapped events.

## TODO

* Generic remapping
* Proper setup.py support
* Proper daemon behaviour
