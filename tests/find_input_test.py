from unittest.mock import MagicMock, patch

import pytest

from evdevremapkeys.evdevremapkeys import Daemon

from _helpers import device


def make_mock_device(path, name="test-device", phys="usb-0000:00:14.0-1/input0"):
    dev = MagicMock()
    dev.path = path
    dev.name = name
    dev.phys = phys
    return dev


def mock_list_devices(*paths):
    """Patch evdev.list_devices to return the given paths."""
    return patch("evdevremapkeys.evdevremapkeys.evdev.list_devices", return_value=paths)


def mock_input_device(devices_by_path):
    """Patch InputDevice constructor to return a mock based on the path."""

    def constructor(path):
        if path in devices_by_path:
            return devices_by_path[path]
        raise OSError(f"No such device: {path}")

    return patch("evdevremapkeys.evdevremapkeys.InputDevice", side_effect=constructor)


class TestFindInputByName:
    def test_match_by_name(self):
        daemon = Daemon()
        dev = make_mock_device("/dev/input/event0", name="My Keyboard")
        with (
            mock_list_devices("/dev/input/event0"),
            mock_input_device({"/dev/input/event0": dev}),
        ):
            result = daemon.find_input(device(input_name="My Keyboard"))
        assert result is dev

    def test_name_mismatch(self):
        daemon = Daemon()
        dev = make_mock_device("/dev/input/event0", name="Other Device")
        with (
            mock_list_devices("/dev/input/event0"),
            mock_input_device({"/dev/input/event0": dev}),
        ):
            result = daemon.find_input(device(input_name="My Keyboard"))
        assert result is None


class TestFindInputByPhys:
    def test_match_by_phys(self):
        daemon = Daemon()
        dev = make_mock_device("/dev/input/event0", phys="usb-0:1/input0")
        with (
            mock_list_devices("/dev/input/event0"),
            mock_input_device({"/dev/input/event0": dev}),
        ):
            result = daemon.find_input(device(input_phys="usb-0:1/input0"))
        assert result is dev

    def test_phys_mismatch(self):
        daemon = Daemon()
        dev = make_mock_device("/dev/input/event0", phys="usb-0:2/input0")
        with (
            mock_list_devices("/dev/input/event0"),
            mock_input_device({"/dev/input/event0": dev}),
        ):
            result = daemon.find_input(device(input_phys="usb-0:1/input0"))
        assert result is None


class TestFindInputByFn:
    def test_match_by_fn(self):
        daemon = Daemon()
        dev = make_mock_device("/dev/input/event5")
        with mock_input_device({"/dev/input/event5": dev}):
            result = daemon.find_input(device(input_fn="/dev/input/event5"))
        assert result is dev

    def test_fn_device_not_found(self):
        daemon = Daemon()
        with mock_input_device({}):
            result = daemon.find_input(device(input_fn="/dev/input/event99"))
        assert result is None


class TestFindInputMultipleCriteria:
    def test_name_and_phys_both_match(self):
        daemon = Daemon()
        dev = make_mock_device(
            "/dev/input/event0", name="My Keyboard", phys="usb-0:1/input0"
        )
        with (
            mock_list_devices("/dev/input/event0"),
            mock_input_device({"/dev/input/event0": dev}),
        ):
            result = daemon.find_input(
                device(input_name="My Keyboard", input_phys="usb-0:1/input0")
            )
        assert result is dev

    def test_name_matches_phys_does_not(self):
        daemon = Daemon()
        dev = make_mock_device(
            "/dev/input/event0", name="My Keyboard", phys="usb-0:2/input0"
        )
        with (
            mock_list_devices("/dev/input/event0"),
            mock_input_device({"/dev/input/event0": dev}),
        ):
            result = daemon.find_input(
                device(input_name="My Keyboard", input_phys="usb-0:1/input0")
            )
        assert result is None


class TestFindInputEdgeCases:
    def test_no_criteria_raises(self):
        daemon = Daemon()
        with pytest.raises(NameError, match="Devices must be identified"):
            daemon.find_input(device())

    def test_device_already_registered(self):
        daemon = Daemon()
        dev = make_mock_device("/dev/input/event0", name="My Keyboard")
        daemon.registered_devices["/dev/input/event0"] = {"device": {}, "task": None}
        with (
            mock_list_devices("/dev/input/event0"),
            mock_input_device({"/dev/input/event0": dev}),
        ):
            result = daemon.find_input(device(input_name="My Keyboard"))
        assert result is None

    def test_device_already_registered_by_fn(self):
        daemon = Daemon()
        dev = make_mock_device("/dev/input/event0")
        daemon.registered_devices["/dev/input/event0"] = {"device": {}, "task": None}
        with mock_input_device({"/dev/input/event0": dev}):
            result = daemon.find_input(device(input_fn="/dev/input/event0"))
        assert result is None

    def test_no_matching_device(self):
        daemon = Daemon()
        dev = make_mock_device("/dev/input/event0", name="Other Device")
        with (
            mock_list_devices("/dev/input/event0"),
            mock_input_device({"/dev/input/event0": dev}),
        ):
            result = daemon.find_input(device(input_name="My Keyboard"))
        assert result is None
