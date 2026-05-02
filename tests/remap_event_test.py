import asyncio

import pytest
from evdev import InputEvent, ecodes

from evdevremapkeys.evdevremapkeys import Daemon, repeat_event

from _helpers import remapping


class MockOutput:
    """Records write_event/syn calls for assertions."""

    def __init__(self):
        self.events = []

    def write_event(self, event):
        self.events.append((event.type, event.code, event.value))

    def syn(self):
        pass


def make_event(code, value, type=ecodes.EV_KEY):
    return InputEvent(0, 0, type, code, value)


# ---------------------------------------------------------------------------
# Plain remapping
# ---------------------------------------------------------------------------


class TestRemapPlain:
    def test_single_remapping_key_down(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B)]
        daemon.remap_event(output, event, remappings)
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_B, 1)]

    def test_single_remapping_key_up(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 0)
        remappings = [remapping(code=ecodes.KEY_B)]
        daemon.remap_event(output, event, remappings)
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_B, 0)]

    def test_multiple_remappings(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_LEFTMETA), remapping(code=ecodes.KEY_B)]
        daemon.remap_event(output, event, remappings)
        assert output.events == [
            (ecodes.EV_KEY, ecodes.KEY_LEFTMETA, 1),
            (ecodes.EV_KEY, ecodes.KEY_B, 1),
        ]

    def test_type_override(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B, type=ecodes.EV_REL)]
        daemon.remap_event(output, event, remappings)
        assert output.events == [(ecodes.EV_REL, ecodes.KEY_B, 1)]

    def test_value_override_single(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B, value=[0])]
        daemon.remap_event(output, event, remappings)
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_B, 0)]

    def test_value_override_sequence(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B, value=[1, 0])]
        daemon.remap_event(output, event, remappings)
        assert output.events == [
            (ecodes.EV_KEY, ecodes.KEY_B, 1),
            (ecodes.EV_KEY, ecodes.KEY_B, 0),
        ]

    def test_autorepeat_forwarded(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 2)
        remappings = [remapping(code=ecodes.KEY_B)]
        daemon.remap_event(output, event, remappings)
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_B, 2)]


# ---------------------------------------------------------------------------
# Delay mode
# ---------------------------------------------------------------------------


class TestRemapDelay:
    def test_first_key_down_emits(self):
        """With count=1, the first key-down sets the counter to count
        and then checks counter == count, so it emits."""
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B, delay=True, count=1)]
        daemon.remap_event(output, event, remappings)
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_B, 1)]

    def test_second_key_down_suppressed(self):
        """With count=1, the second key-down decrements the counter to 0,
        which != count, so it is suppressed. This gives every-other behavior."""
        daemon = Daemon()
        output = MockOutput()
        remappings = [remapping(code=ecodes.KEY_B, delay=True, count=1)]

        # First press — emitted
        event1 = make_event(ecodes.KEY_A, 1)
        daemon.remap_event(output, event1, remappings)
        assert len(output.events) == 1

        # Second press — suppressed
        event2 = make_event(ecodes.KEY_A, 1)
        daemon.remap_event(output, event2, remappings)
        assert len(output.events) == 1  # still 1, no new event

    def test_third_key_down_emits_again(self):
        """With count=1, the third press resets and emits again."""
        daemon = Daemon()
        output = MockOutput()
        remappings = [remapping(code=ecodes.KEY_B, delay=True, count=1)]

        event1 = make_event(ecodes.KEY_A, 1)
        daemon.remap_event(output, event1, remappings)
        event2 = make_event(ecodes.KEY_A, 1)
        daemon.remap_event(output, event2, remappings)
        event3 = make_event(ecodes.KEY_A, 1)
        daemon.remap_event(output, event3, remappings)
        assert len(output.events) == 2  # first and third emitted

    def test_key_up_no_prior_key_down(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 0)
        remappings = [remapping(code=ecodes.KEY_B, delay=True, count=1)]
        # Should not raise KeyError
        daemon.remap_event(output, event, remappings)
        assert output.events == []

    def test_autorepeat_skipped_not_returned(self):
        """Autorepeat (value=2) in delay mode should skip the delay remapping
        but still process subsequent plain remappings in the list."""
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 2)
        remappings = [
            remapping(code=ecodes.KEY_B, delay=True, count=1),
            remapping(code=ecodes.KEY_C),
        ]
        daemon.remap_event(output, event, remappings)
        # The delay remapping is skipped, but plain KEY_C should still emit
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_C, 2)]

    def test_non_integer_count_raises(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B, delay=True, count="bad")]
        with pytest.raises(ValueError, match="Count must be an integer"):
            daemon.remap_event(output, event, remappings)


# ---------------------------------------------------------------------------
# Repeat mode
# ---------------------------------------------------------------------------


class TestRemapRepeat:
    def test_key_down_creates_task(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B, repeat=True, rate=0.1, count=0)]

        async def run():
            daemon.remap_event(output, event, remappings)
            assert ecodes.KEY_A in daemon.repeat_tasks
            task = daemon.repeat_tasks[ecodes.KEY_A]
            assert not task.done()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run())

    def test_key_up_cancels_task(self):
        daemon = Daemon()
        output = MockOutput()
        remappings = [remapping(code=ecodes.KEY_B, repeat=True, rate=0.1, count=0)]

        async def run():
            # Key down — starts task
            event_down = make_event(ecodes.KEY_A, 1)
            daemon.remap_event(output, event_down, remappings)
            task = daemon.repeat_tasks[ecodes.KEY_A]

            # Key up — cancels task
            event_up = make_event(ecodes.KEY_A, 0)
            daemon.remap_event(output, event_up, remappings)
            assert ecodes.KEY_A not in daemon.repeat_tasks
            # Let cancellation propagate
            await asyncio.sleep(0)
            assert task.cancelled()

        asyncio.run(run())

    def test_key_down_finite_count(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B, repeat=True, rate=0.01, count=3)]

        async def run():
            daemon.remap_event(output, event, remappings)
            task = daemon.repeat_tasks[ecodes.KEY_A]
            await task
            # 3 iterations, 1 event each
            assert len(output.events) == 3
            assert all(e == (ecodes.EV_KEY, ecodes.KEY_B, 1) for e in output.events)

        asyncio.run(run())

    def test_key_up_ignored_with_finite_count(self):
        daemon = Daemon()
        output = MockOutput()
        remappings = [remapping(code=ecodes.KEY_B, repeat=True, rate=0.01, count=3)]

        async def run():
            event_down = make_event(ecodes.KEY_A, 1)
            daemon.remap_event(output, event_down, remappings)
            task = daemon.repeat_tasks[ecodes.KEY_A]

            # Key up with count>0 should be ignored — task keeps running
            event_up = make_event(ecodes.KEY_A, 0)
            daemon.remap_event(output, event_up, remappings)
            assert ecodes.KEY_A in daemon.repeat_tasks
            assert not task.cancelled()

            await task

        asyncio.run(run())

    def test_second_key_down_replaces_task(self):
        daemon = Daemon()
        output = MockOutput()
        remappings = [remapping(code=ecodes.KEY_B, repeat=True, rate=0.1, count=0)]

        async def run():
            event1 = make_event(ecodes.KEY_A, 1)
            daemon.remap_event(output, event1, remappings)
            first_task = daemon.repeat_tasks[ecodes.KEY_A]

            event2 = make_event(ecodes.KEY_A, 1)
            daemon.remap_event(output, event2, remappings)
            second_task = daemon.repeat_tasks[ecodes.KEY_A]

            # Let cancellation propagate
            await asyncio.sleep(0)
            assert first_task.cancelled()
            assert not second_task.done()

            second_task.cancel()
            try:
                await second_task
            except asyncio.CancelledError:
                pass

        asyncio.run(run())

    def test_non_float_rate_raises(self):
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [remapping(code=ecodes.KEY_B, repeat=True, rate=1, count=0)]

        async def run():
            with pytest.raises(ValueError, match="Rate must be a float"):
                daemon.remap_event(output, event, remappings)

        asyncio.run(run())

    def test_autorepeat_skipped_continues_to_next(self):
        """Autorepeat (value=2) in repeat mode should skip the repeat remapping
        but still process subsequent plain remappings in the list."""
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 2)
        remappings = [
            remapping(code=ecodes.KEY_B, repeat=True, rate=0.01, count=0),
            remapping(code=ecodes.KEY_C),
        ]

        async def run():
            daemon.remap_event(output, event, remappings)

        asyncio.run(run())
        assert ecodes.KEY_A not in daemon.repeat_tasks
        assert output.events == [(ecodes.EV_KEY, ecodes.KEY_C, 2)]


# ---------------------------------------------------------------------------
# original_value isolation across iterations (regression for e1b8fbd)
# ---------------------------------------------------------------------------


class TestOriginalValueIsolation:
    def test_value_override_then_delay_uses_original_value(self):
        """A plain remapping that overrides event.value to 0 must not
        cause the subsequent delay remapping to treat the event as key-up.
        We check that KEY_C emits at all (delay logic ran with key_down=True
        derived from original_value=1, despite event.value being mutated to 0
        by the prior remapping)."""
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [
            remapping(code=ecodes.KEY_B, value=[0]),
            remapping(code=ecodes.KEY_C, delay=True, count=1),
        ]
        daemon.remap_event(output, event, remappings)
        emitted_codes = [(t, c) for (t, c, v) in output.events]
        assert emitted_codes == [
            (ecodes.EV_KEY, ecodes.KEY_B),
            (ecodes.EV_KEY, ecodes.KEY_C),
        ]
        # And the delay counter was set, proving key_down was detected.
        assert daemon.remapped_tasks[ecodes.KEY_A] == 1

    def test_value_override_then_repeat_uses_original_value(self):
        """A plain remapping that overrides event.value to 0 must not
        cause the subsequent repeat remapping to treat the event as key-up."""
        daemon = Daemon()
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)
        remappings = [
            remapping(code=ecodes.KEY_B, value=[0]),
            remapping(code=ecodes.KEY_C, repeat=True, rate=0.01, count=0),
        ]

        async def run():
            daemon.remap_event(output, event, remappings)
            # A repeat task should have been scheduled because original_value==1
            # is treated as key_down regardless of the prior overwrite to 0.
            assert ecodes.KEY_A in daemon.repeat_tasks
            task = daemon.repeat_tasks[ecodes.KEY_A]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run())


# ---------------------------------------------------------------------------
# repeat_event async behavior
# ---------------------------------------------------------------------------


class TestRepeatEvent:
    def test_count_zero_repeats_until_cancelled(self):
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)

        async def run():
            task = asyncio.create_task(repeat_event(event, 0.01, 0, [1], output))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert len(output.events) >= 2

        asyncio.run(run())

    def test_finite_count_emits_exact_iterations(self):
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)

        async def run():
            task = asyncio.create_task(repeat_event(event, 0.01, 3, [1], output))
            await task
            assert len(output.events) == 3

        asyncio.run(run())

    def test_multi_value_sequence(self):
        output = MockOutput()
        event = make_event(ecodes.KEY_A, 1)

        async def run():
            task = asyncio.create_task(repeat_event(event, 0.01, 2, [1, 0], output))
            await task
            # 2 iterations * 2 values = 4 events
            assert len(output.events) == 4
            assert output.events[0] == (ecodes.EV_KEY, ecodes.KEY_A, 1)
            assert output.events[1] == (ecodes.EV_KEY, ecodes.KEY_A, 0)
            assert output.events[2] == (ecodes.EV_KEY, ecodes.KEY_A, 1)
            assert output.events[3] == (ecodes.EV_KEY, ecodes.KEY_A, 0)

        asyncio.run(run())
