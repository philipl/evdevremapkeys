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

## libinput's lua plugin based future?

In the years since I first wrote `evdevremapkeys`, there wasn'tt been any real
movement towards exposing a meaningful remapping capability from libinput. In
2025, they started development of a
[lua](https://gitlab.freedesktop.org/libinput/libinput/-/merge_requests/1192)
plugin framework, which might turn out to be a real solution. When that lands,
and as long as it doesn't depend on the Wayland compositor to expose access to
it, it might turn out to be a better long term approach. But it's too early to
say right now.