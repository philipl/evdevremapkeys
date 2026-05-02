import asyncio

from evdev import InputEvent, ecodes

from evdevremapkeys.evdevremapkeys import Daemon


class MockOutput:
    def __init__(self):
        self.events = []
        self.closed = False

    def write_event(self, event):
        self.events.append((event.type, event.code, event.value))

    def syn(self):
        pass

    def close(self):
        self.closed = True


class FakeInput:
    """Async input device whose async_read_loop yields scripted events
    then raises CancelledError to terminate the loop."""

    def __init__(self, events, path="/dev/input/event0", name="fake", phys="phys0"):
        self._events = list(events)
        self.path = path
        self.name = name
        self.phys = phys
        self.closed = False

    def async_read_loop(self):
        events = self._events

        async def gen():
            for ev in events:
                yield ev
            # Block forever once events are exhausted; the test cancels the task.
            await asyncio.Event().wait()

        return gen()

    def close(self):
        self.closed = True


def make_event(code, value, type=ecodes.EV_KEY):
    return InputEvent(0, 0, type, code, value)


def run_handle_events(daemon, input, output, remappings, modifier_groups):
    """Run handle_events until all scripted events are consumed, then cancel."""

    async def runner():
        task = asyncio.create_task(
            daemon.handle_events(input, output, remappings, modifier_groups)
        )
        # Yield enough times for the generator to drain.
        for _ in range(10):
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(runner())


class TestHandleEventsPassthrough:
    def test_unmapped_event_passes_through(self):
        daemon = Daemon()
        output = MockOutput()
        input = FakeInput([make_event(ecodes.KEY_X, 1)])
        run_handle_events(daemon, input, output, {}, {})
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_X, 1)]

    def test_mapped_event_is_remapped(self):
        daemon = Daemon()
        output = MockOutput()
        input = FakeInput([make_event(ecodes.KEY_A, 1)])
        remappings = {ecodes.KEY_A: [{"code": ecodes.KEY_B}]}
        run_handle_events(daemon, input, output, remappings, {})
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_B, 1)]


class TestHandleEventsModifierGroup:
    def _make_config(self):
        # Pressing KEY_LEFTSHIFT activates modifier group "mod1".
        # While active, KEY_A => KEY_C. Otherwise, KEY_A => KEY_B.
        remappings = {
            ecodes.KEY_LEFTSHIFT: [{"modifier_group": "mod1"}],
            ecodes.KEY_A: [{"code": ecodes.KEY_B}],
        }
        modifier_groups = {
            "mod1": {
                ecodes.KEY_A: [{"code": ecodes.KEY_C}],
            }
        }
        return remappings, modifier_groups

    def test_modifier_press_activates_group(self):
        daemon = Daemon()
        output = MockOutput()
        remappings, modifier_groups = self._make_config()
        events = [
            make_event(ecodes.KEY_LEFTSHIFT, 1),
            make_event(ecodes.KEY_A, 1),
        ]
        input = FakeInput(events)
        run_handle_events(daemon, input, output, remappings, modifier_groups)
        # Modifier itself produces no output; KEY_A is remapped via mod1.
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_C, 1)]

    def test_modifier_release_restores_base_mappings(self):
        daemon = Daemon()
        output = MockOutput()
        remappings, modifier_groups = self._make_config()
        events = [
            make_event(ecodes.KEY_LEFTSHIFT, 1),
            make_event(ecodes.KEY_A, 1),
            make_event(ecodes.KEY_LEFTSHIFT, 0),
            make_event(ecodes.KEY_A, 1),
        ]
        input = FakeInput(events)
        run_handle_events(daemon, input, output, remappings, modifier_groups)
        assert output.events == [
            (ecodes.EV_KEY, ecodes.KEY_C, 1),
            (ecodes.EV_KEY, ecodes.KEY_B, 1),
        ]

    def test_modifier_autorepeat_does_not_reactivate(self):
        """Modifier key-down only activates on value==1; an autorepeat (value==2)
        of the modifier while it is already active should not change state."""
        daemon = Daemon()
        output = MockOutput()
        remappings, modifier_groups = self._make_config()
        events = [
            make_event(ecodes.KEY_LEFTSHIFT, 1),
            make_event(ecodes.KEY_LEFTSHIFT, 2),
            make_event(ecodes.KEY_A, 1),
            make_event(ecodes.KEY_LEFTSHIFT, 0),
            make_event(ecodes.KEY_A, 1),
        ]
        input = FakeInput(events)
        run_handle_events(daemon, input, output, remappings, modifier_groups)
        assert output.events == [
            (ecodes.EV_KEY, ecodes.KEY_C, 1),
            (ecodes.EV_KEY, ecodes.KEY_B, 1),
        ]

    def test_unmapped_event_while_active_passes_through(self):
        daemon = Daemon()
        output = MockOutput()
        remappings, modifier_groups = self._make_config()
        events = [
            make_event(ecodes.KEY_LEFTSHIFT, 1),
            make_event(ecodes.KEY_X, 1),  # Not in mod1 mappings
        ]
        input = FakeInput(events)
        run_handle_events(daemon, input, output, remappings, modifier_groups)
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_X, 1)]


class TestHandleEventsCleanup:
    def test_finally_cleans_up_registered_devices(self):
        daemon = Daemon()
        output = MockOutput()
        input = FakeInput([], path="/dev/input/event0")
        daemon.registered_devices["/dev/input/event0"] = {
            "input": input,
            "output": output,
            "task": None,
            "device": {},
        }
        run_handle_events(daemon, input, output, {}, {})
        assert "/dev/input/event0" not in daemon.registered_devices
        assert output.closed
        assert input.closed

    def test_finally_handles_missing_registered_entry(self):
        """If the entry was already popped elsewhere, finally still completes
        and closes the input device."""
        daemon = Daemon()
        output = MockOutput()
        input = FakeInput([])
        run_handle_events(daemon, input, output, {}, {})
        assert input.closed
        # output.close() should NOT be called since there was no entry
        assert not output.closed
