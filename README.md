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

# Software Setup

## Install from PyPI

The recommended way to install the program is to use `pipx`.

```bash
$ pipx install evdevremapkeys
```

You can also use `pip`, but on modern distros, `pipx` is a far better experience.

## Create a configuration

You will need to create an initial configuration file for the program to be
able to run and doing anything useful.

It's recommended to start from one of the
[example](https://github.com/philipl/evdevremapkeys/tree/master/examples) config
files and adapt it for your hardware and the remapping you need.

Place your final file at: `~/.config/evdevremapkeys/config.yml`

## Run the program

```bash
evdevremapkeys
```

## More details

See [RUNNING.md](https://github.com/philipl/evdevremapkeys/blob/master/RUNNING.md) for
more details.
