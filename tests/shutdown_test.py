import asyncio

from evdevremapkeys.evdevremapkeys import shutdown


def test_shutdown_cancels_other_tasks_and_stops_loop():
    loop = asyncio.new_event_loop()
    try:

        async def long_running():
            await asyncio.sleep(60)

        async def driver():
            t1 = loop.create_task(long_running())
            t2 = loop.create_task(long_running())
            # Yield once so the tasks actually start.
            await asyncio.sleep(0)
            results = await shutdown(loop)
            assert t1.cancelled()
            assert t2.cancelled()
            # shutdown returns one entry per cancelled task (driver excluded).
            assert len(results) == 2
            return results

        loop.run_until_complete(driver())
        assert not loop.is_running()
    finally:
        loop.close()


def test_shutdown_excludes_current_task():
    loop = asyncio.new_event_loop()
    try:

        async def driver():
            results = await shutdown(loop)
            # No other tasks were spawned; only the driver exists, and it
            # is excluded — so results is empty.
            assert results == []

        loop.run_until_complete(driver())
    finally:
        loop.close()


def test_shutdown_results_contain_cancelled_errors():
    """gather(return_exceptions=True) wraps cancellations as CancelledError
    instances; verify they appear in the returned list rather than propagating."""
    loop = asyncio.new_event_loop()
    try:

        async def long_running():
            await asyncio.sleep(60)

        async def driver():
            loop.create_task(long_running())
            await asyncio.sleep(0)
            results = await shutdown(loop)
            assert len(results) == 1
            assert isinstance(results[0], asyncio.CancelledError)

        loop.run_until_complete(driver())
    finally:
        loop.close()
