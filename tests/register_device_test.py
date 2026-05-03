import asyncio
import errno
from unittest.mock import MagicMock, patch

import pytest
from evdev import ecodes

from evdevremapkeys.evdevremapkeys import Daemon

from _helpers import device as device_config


def make_input_device(
    capabilities,
    path="/dev/input/event0",
    name="dev",
    phys="phys0",
    grab_error=None,
    input_props=None,
):
    dev = MagicMock()
    dev.path = path
    dev.name = name
    dev.phys = phys
    dev.capabilities.return_value = capabilities
    dev.input_props.return_value = input_props or []
    if grab_error is not None:
        dev.grab.side_effect = grab_error
    return dev


def make_loop():
    """Real event loop is needed because register_device calls loop.create_task."""
    return asyncio.new_event_loop()


class TestRegisterDeviceCapabilityExtension:
    def test_extends_ev_key_with_remapping_codes(self):
        daemon = Daemon()
        loop = make_loop()
        try:
            input = make_input_device(
                {
                    ecodes.EV_SYN: [0, 1, 3],
                    ecodes.EV_KEY: [ecodes.KEY_A],
                }
            )
            captured = {}

            def fake_uinput(caps, **kwargs):
                captured["caps"] = caps
                return MagicMock()

            device = device_config(
                input_name="dev",
                output_name="out",
                remappings={
                    ecodes.KEY_A: [{"code": ecodes.KEY_B}, {"code": ecodes.KEY_C}],
                },
            )
            with (
                patch.object(daemon, "find_input", return_value=input),
                patch("evdevremapkeys.evdevremapkeys.UInput", side_effect=fake_uinput),
            ):
                task = daemon.register_device(device, loop)
            assert task is not None
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass

            ev_key = set(captured["caps"][ecodes.EV_KEY])
            assert {ecodes.KEY_A, ecodes.KEY_B, ecodes.KEY_C}.issubset(ev_key)
            assert ecodes.EV_SYN not in captured["caps"]
        finally:
            loop.close()

    def test_extends_ev_key_with_modifier_group_codes(self):
        daemon = Daemon()
        loop = make_loop()
        try:
            input = make_input_device(
                {
                    ecodes.EV_SYN: [0],
                    ecodes.EV_KEY: [ecodes.KEY_A],
                }
            )
            captured = {}

            def fake_uinput(caps, **kwargs):
                captured["caps"] = caps
                return MagicMock()

            device = device_config(
                input_name="dev",
                output_name="out",
                remappings={
                    ecodes.KEY_LEFTSHIFT: [{"modifier_group": "mod1"}],
                },
                modifier_groups={
                    "mod1": {
                        ecodes.KEY_A: [{"code": ecodes.KEY_Z}],
                    }
                },
            )
            with (
                patch.object(daemon, "find_input", return_value=input),
                patch("evdevremapkeys.evdevremapkeys.UInput", side_effect=fake_uinput),
            ):
                task = daemon.register_device(device, loop)
            assert task is not None
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass

            ev_key = set(captured["caps"][ecodes.EV_KEY])
            assert ecodes.KEY_Z in ev_key
        finally:
            loop.close()

    def test_extends_ev_key_with_extra_keys(self):
        daemon = Daemon()
        loop = make_loop()
        try:
            input = make_input_device(
                {
                    ecodes.EV_SYN: [0],
                    ecodes.EV_KEY: [ecodes.KEY_A],
                }
            )
            captured = {}

            def fake_uinput(caps, **kwargs):
                captured["caps"] = caps
                return MagicMock()

            device = device_config(
                input_name="dev",
                output_name="out",
                remappings={},
                extra_keys=[ecodes.BTN_SOUTH, ecodes.BTN_EAST],
            )
            with (
                patch.object(daemon, "find_input", return_value=input),
                patch("evdevremapkeys.evdevremapkeys.UInput", side_effect=fake_uinput),
            ):
                task = daemon.register_device(device, loop)
            assert task is not None
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass

            ev_key = set(captured["caps"][ecodes.EV_KEY])
            assert {ecodes.KEY_A, ecodes.BTN_SOUTH, ecodes.BTN_EAST}.issubset(ev_key)
        finally:
            loop.close()

    def test_extra_keys_on_buttonless_device(self):
        """A device that exposes no EV_KEY at all can still advertise buttons
        on the output via extra_keys (Steam/wine recognition workaround)."""
        daemon = Daemon()
        loop = make_loop()
        try:
            input = make_input_device(
                {
                    ecodes.EV_SYN: [0],
                    # No EV_KEY at all
                }
            )
            captured = {}

            def fake_uinput(caps, **kwargs):
                captured["caps"] = caps
                return MagicMock()

            device = device_config(
                input_name="dev",
                output_name="out",
                remappings={},
                extra_keys=[ecodes.BTN_SOUTH],
            )
            with (
                patch.object(daemon, "find_input", return_value=input),
                patch("evdevremapkeys.evdevremapkeys.UInput", side_effect=fake_uinput),
            ):
                task = daemon.register_device(device, loop)
            assert task is not None
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass

            ev_key = set(captured["caps"][ecodes.EV_KEY])
            assert ev_key == {ecodes.BTN_SOUTH}
        finally:
            loop.close()

    def test_handles_device_without_ev_key(self):
        """register_device should not crash when input.capabilities() has no
        EV_KEY entry (regression for commit d19fbbd)."""
        daemon = Daemon()
        loop = make_loop()
        try:
            input = make_input_device(
                {
                    ecodes.EV_SYN: [0, 1, 3],
                    # No EV_KEY at all
                }
            )

            def fake_uinput(caps, **kwargs):
                return MagicMock()

            device = device_config(
                input_name="dev",
                output_name="out",
                remappings={
                    ecodes.KEY_A: [{"code": ecodes.KEY_B}],
                },
            )
            with (
                patch.object(daemon, "find_input", return_value=input),
                patch("evdevremapkeys.evdevremapkeys.UInput", side_effect=fake_uinput),
            ):
                task = daemon.register_device(device, loop)
            assert task is not None
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass
        finally:
            loop.close()


class TestRegisterDeviceErrorPaths:
    def test_ebusy_raises_system_exit(self):
        daemon = Daemon()
        loop = make_loop()
        try:
            input = make_input_device(
                {ecodes.EV_SYN: [0], ecodes.EV_KEY: [ecodes.KEY_A]},
                grab_error=OSError(errno.EBUSY, "Device or resource busy"),
            )
            device = device_config(
                input_name="dev",
                output_name="out",
                remappings={},
            )
            with patch.object(daemon, "find_input", return_value=input):
                with pytest.raises(SystemExit):
                    daemon.register_device(device, loop)
            input.close.assert_called_once()
        finally:
            loop.close()

    def test_other_oserror_raises_system_exit(self):
        daemon = Daemon()
        loop = make_loop()
        try:
            input = make_input_device(
                {ecodes.EV_SYN: [0], ecodes.EV_KEY: [ecodes.KEY_A]},
                grab_error=OSError(errno.EACCES, "Permission denied"),
            )
            device = device_config(
                input_name="dev",
                output_name="out",
                remappings={},
            )
            with patch.object(daemon, "find_input", return_value=input):
                with pytest.raises(SystemExit):
                    daemon.register_device(device, loop)
            input.close.assert_called_once()
        finally:
            loop.close()

    def test_no_input_found_returns_none(self):
        daemon = Daemon()
        loop = make_loop()
        try:
            device = device_config(
                input_name="missing", output_name="out", remappings={}
            )
            with patch.object(daemon, "find_input", return_value=None):
                result = daemon.register_device(device, loop)
            assert result is None
        finally:
            loop.close()


class TestRegisterDeviceDeduplication:
    def test_already_registered_returns_existing_task(self):
        daemon = Daemon()
        loop = make_loop()
        try:
            existing_task = MagicMock()
            device = device_config(input_name="dev", output_name="out", remappings={})
            daemon.registered_devices["/dev/input/event0"] = {
                "device": device,
                "task": existing_task,
                "input": MagicMock(),
                "output": MagicMock(),
            }
            # find_input should not even be consulted; we shortcut on config
            # equality.
            with patch.object(daemon, "find_input") as find_mock:
                result = daemon.register_device(device, loop)
            assert result is existing_task
            find_mock.assert_not_called()
        finally:
            loop.close()
