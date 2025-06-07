# Hardware Setup

## Proper Device Permissions with evdev

Normally devices managed by uinput are readable only by root. You can change this with some special
udev magic.

/etc/udev/rules.d/71-tablet-uaccess.rules

```
# XP-Pen 13
SUBSYSTEMS=="usb", ATTRS{idVendor}=="28bd", ATTRS{idProduct}=="000b", TAG+="uaccess"
```
The magic is the `TAG+="uaccess` line which means that the device will be created with permissions
to be accessible to the currently logged in user.

Change the idVendor and idProduct to match your tablet or other device.

Restart udev
```
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Now remove and plug your tablet back in.

`evdevremapkeys -l` should now show the uinput devices for your tablet or other hardware.

Using uaccess, when someone else sits down at the computer and logs in, then they will have
permission to use the tablet, and the permission of your inactive account will disabled. This
is all handled by logind/systemd/X automatically.

# Software Setup

## Install from PyPI

The recommended way to install the program is to use `pipx`.

```bash
$ pipx install evdevremapkeys
```

You can also use `pip`, but on modern distros, `pipx` is a far better experience.

## Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) to build and run. You will need to install
`uv` yourself, and you can follow their official documentation if you wish. My personal
preference is to use `pipx` to install `uv`.

On Ubuntu:

```bash
$ sudo apt install pipx
$ pipx install uv
```

## Running from the source directory

To run from the source directory (checked out of git, or unpacked tarball), simply do:

```bash
$ uv run evdevremapkeys
```

## Installing from source

I recommend using `pipx` to install the program and make it accessible in your user environment.

```bash
$ pipx install <path/to/git/checkout>
```

or

```bash
$ pipx install <source-tarball>
```

If you are trying to do active developing, installing with `--editable` will cause the
installation to always reflect your changes.

## Building a self-contained executable

You will not usually need a self-contained executable, given the existing options for running
and installing the program, but it is possible to build one, if you wish.

Run `build-binary.sh`. It assumes you have uv installed. This will download and install all dependencies,
compile the python to excutable code using PyInstaller, then bundle all the dynamic modules into a
single static executable using StaticX. You may need to install patchelf on your system.

## Running evdevremapkeys as a user background service

You shouldn't run evdevremapkeys as a system service, these means everyone using it will
have the exact same config.

systemd supports user-level services, where each user can have their own evdevremapkeys instance. It
is started when they log in, and shut down when they log out.

While `evdevremapkeys` can be run directly, it probably makes the most sense to run it in the
background. On a modern distro with Systemd, this can be done fairly easily by running it as a user
service. I've provided an example as `examples/evdevremapkeys.service`.

If you are using X11, you will need to reverse the gnome-shell-wayland.service and
gnome-shell-x11.service entries.

If you choose to build a static executable, edit the service file to refer to where you put the
executable

This example assumes you're running gnome-shell and so it adds itself as `WantedBy` gnome-shell when
wayland is in use.

```shell
$ mkdir -p ~/.config/systemd/user
$ cp examples/evdevremapkeys.service ~/.config/systemd/user
$ systemctl --user daemon-reload
$ systemctl --user enable evdevremapkeys
$ systemctl --user start evdevremapkeys
```

### Configuration

You can edit one of the sample config files, and then put it in the following locations:

Linux: `~/.config/evdevremapkeys/config.yaml`

