Running as a background service
===============================

While `evdevremapkeys` can be run directly, it probably makes the most
sense to run it in the background. On a modern distro with Systemd,
this can be done fairly easily by running it as a user service. I've
provided an example as `examples/evdevremapkeys.service`.

This example assumes you're running gnome-shell and so it adds itself
as `WantedBy` gnome-shell when wayland is in use.

Installation
------------

```shell
$ mkdir -p ~/.config/systemd/user
$ cp examples/evdevremapkeys.service ~/.config/systemd/user
$ systemctl --user daemon-reload
$ systemctl --user enable evdevremapkeys
$ systemctl --user start evdevremapkeys
```
