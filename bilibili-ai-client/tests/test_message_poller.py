import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from message_poller import MessagePoller


class TestMessagePollerLifecycle:
    def test_initial_state(self):
        poller = MessagePoller()
        assert poller.running == False

    def test_start_sets_running(self):
        poller = MessagePoller()
        poller.start()
        assert poller.running == True
        poller.stop()

    def test_stop_clears_running(self):
        poller = MessagePoller()
        poller.start()
        poller.stop()
        assert poller.running == False


class TestMessagePollerCallbacks:
    def test_set_callback(self):
        poller = MessagePoller()
        results = []

        def callback(msg):
            results.append(msg)

        poller.set_callback(callback)
        assert poller.callback == callback

    def test_notify_callbacks(self):
        poller = MessagePoller()
        results = []

        def callback(msg):
            results.append(msg)

        poller.set_callback(callback)
        test_msg = {"msg_id": "test_001", "bv_id": "BV1xxx", "content": "测试"}
        poller._notify_callbacks(test_msg)

        assert len(results) == 1
        assert results[0]["msg_id"] == "test_001"


class TestMessagePollerRetry:
    def test_retry_config(self):
        poller = MessagePoller()
        assert poller.base_delay == 5
        assert poller.max_retries == 5
        assert poller.max_delay == 300

    def test_exponential_backoff(self):
        poller = MessagePoller()
        delays = [poller._calculate_delay(i) for i in range(5)]
        assert delays[0] == 5
        assert delays[1] == 10
        assert delays[2] == 20
        assert delays[3] == 40
        assert delays[4] == 80


class TestMessagePollerAPI:
    @pytest.mark.asyncio
    async def test_getdynamic_with_invalid_auth(self):
        poller = MessagePoller()
        result = await poller.getdynamic("invalid_cookie")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_mentions_with_invalid_auth(self):
        poller = MessagePoller()
        result = await poller.get_mentions("invalid_cookie")
        assert result == []

    def test_getdynamic_returns_list(self, valid_cookie):
        import asyncio
        poller = MessagePoller()

        async def test():
            return await poller.getdynamic(valid_cookie)

        result = asyncio.run(test())
        assert isinstance(result, list)