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
permission to use the tablet, and the permission of your inactive account will be logged out. This
is all handled by logind/systemd/X automatically.

# Software Setup

## Building a self-contained executable

Run `build.sh`. It assumes you have pip installed. This will download and install all dependencies,
compile the python to excutable code using PyInstaller, then bundle all the dynamic modules into a
single static executable using StaticX. You may need to install patchelf on your system.

## Running evdevremapkeys as a user background service

You shouldn't run evdevremapkeys as a system service, these means everyone using the tablet will
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

