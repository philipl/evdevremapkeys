from unittest.mock import MagicMock

from evdevremapkeys.evdevremapkeys import Config, Daemon

from _helpers import device


def make_udev_event(action):
    ev = MagicMock()
    ev.action = action
    return ev


def make_monitor(scripted_events):
    """A pyudev.Monitor stand-in whose poll(0) returns the next scripted event,
    or None when exhausted."""
    monitor = MagicMock()
    iterator = iter(list(scripted_events) + [None])
    monitor.poll.side_effect = lambda timeout=0: next(iterator)
    return monitor


class TestHandleUdevEvent:
    def test_add_event_triggers_register_for_each_device(self) -> None:
        daemon = Daemon()
        monitor = make_monitor([make_udev_event("add")])
        config: Config = {"devices": [device(input_name="d1"), device(input_name="d2")]}
        loop = MagicMock()

        called = []
        daemon.register_device = lambda device, lp: called.append(device)  # type: ignore[assignment]

        daemon.handle_udev_event(monitor, config, loop)
        assert called == config["devices"]

    def test_non_add_events_do_not_trigger_register(self) -> None:
        daemon = Daemon()
        monitor = make_monitor([make_udev_event("remove"), make_udev_event("change")])
        config: Config = {"devices": [device(input_name="d1")]}
        loop = MagicMock()

        called = []
        daemon.register_device = lambda device, lp: called.append(device)  # type: ignore[assignment]

        daemon.handle_udev_event(monitor, config, loop)
        assert called == []

    def test_mixed_remove_then_add_still_registers(self) -> None:
        """Regression for the bug where handle_udev_event used to break out of
        the polling loop on a non-add event, missing later add events."""
        daemon = Daemon()
        monitor = make_monitor(
            [
                make_udev_event("remove"),
                make_udev_event("add"),
            ]
        )
        config: Config = {"devices": [device(input_name="d1")]}
        loop = MagicMock()

        called = []
        daemon.register_device = lambda device, lp: called.append(device)  # type: ignore[assignment]

        daemon.handle_udev_event(monitor, config, loop)
        assert called == config["devices"]

    def test_empty_queue_does_not_call_register(self) -> None:
        daemon = Daemon()
        monitor = make_monitor([])
        config: Config = {"devices": [device(input_name="d1")]}
        loop = MagicMock()

        called = []
        daemon.register_device = lambda device, lp: called.append(device)  # type: ignore[assignment]

        daemon.handle_udev_event(monitor, config, loop)
        assert called == []

    def test_multiple_add_events_register_devices_once(self) -> None:
        """Multiple add events in one poll batch should still result in a single
        registration pass over the configured devices."""
        daemon = Daemon()
        monitor = make_monitor(
            [
                make_udev_event("add"),
                make_udev_event("add"),
                make_udev_event("add"),
            ]
        )
        config: Config = {"devices": [device(input_name="d1"), device(input_name="d2")]}
        loop = MagicMock()

        called = []
        daemon.register_device = lambda device, lp: called.append(device)  # type: ignore[assignment]

        daemon.handle_udev_event(monitor, config, loop)
        # One pass over devices, regardless of how many add events were polled.
        assert called == config["devices"]
