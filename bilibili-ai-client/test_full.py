import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.')))

from config import config
from database import database
from message_poller import MessagePoller
from utils.logger import logger

print("=== Full Integration Test ===")
print(f"bili_auth: {config.get('bili_auth', '')[:50] if config.get('bili_auth') else 'EMPTY'}...")
print(f"polling_interval: {config.get('polling_interval')}")
print()

# Test get_mentions directly
async def test_get_mentions():
    poller = MessagePoller()
    cookie = config.get('bili_auth')
    print(f"Calling get_mentions with cookie: {cookie[:30]}...")
    result = await poller.get_mentions(cookie)
    print(f"get_mentions returned {len(result)} messages")
    for m in result:
        print(f"  - {m}")
    return result

# Test with callback
async def test_with_callback():
    messages_processed = []

    def callback(msg):
        print(f"CALLBACK triggered with: {msg.get('msg_id')}")
        messages_processed.append(msg)

    poller = MessagePoller()
    poller.set_callback(callback)

    print("Starting poller...")
    poller.start()

    print("Waiting 5 seconds for poll cycle...")
    await asyncio.sleep(5)

    print(f"Poller running: {poller.running}")

    poller.stop()
    print(f"Messages processed: {len(messages_processed)}")

    return messages_processed

async def main():
    # Test 1: Direct API call
    print("\n=== Test 1: Direct API call ===")
    messages = await test_get_mentions()

    # Test 2: With callback
    print("\n=== Test 2: With callback and polling ===")
    await test_with_callback()

    # Check DB
    print("\n=== Test 3: Database check ===")
    db_msgs = database.get_messages(limit=5)
    print(f"Messages in DB: {len(db_msgs)}")
    for m in db_msgs:
        print(f"  - {m}")

asyncio.run(main())
