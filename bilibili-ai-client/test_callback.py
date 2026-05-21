import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.')))

from config import config
from database import database
from message_poller import MessagePoller
from utils.logger import logger

print("=== Direct Callback Test ===")

async def process_new_message(msg):
    print(f"[process_new_message] START - msg_id: {msg.get('msg_id')}")
    bv_id = msg.get("bv_id", "")
    sender_uid = msg.get("sender_uid", "")
    print(f"[process_new_message] bv_id={bv_id}, sender_uid={sender_uid}")

    is_whitelisted = database.is_whitelist(sender_uid)
    print(f"[process_new_message] is_whitelisted={is_whitelisted}")

    if sender_uid and not is_whitelisted:
        print(f"[process_new_message] SKIP - not whitelisted")
        return

    msg_id = msg.get("msg_id", f"{bv_id}_{sender_uid}" if bv_id else msg.get("content", "")[:20])
    print(f"[process_new_message] Adding to DB: {msg_id}")

    database.add_message(
        msg_id=msg_id,
        sender_uid=sender_uid,
        sender_name=msg.get("sender_name", ""),
        bv_id=bv_id or "unknown",
        content=msg.get("content", "")
    )
    print(f"[process_new_message] DONE - Message added to DB")

async def main():
    poller = MessagePoller()

    # Set up callback that calls process_new_message
    def wrapped_callback(msg):
        print(f"[wrapped_callback] Creating task for msg: {msg.get('msg_id')}")
        asyncio.create_task(process_new_message(msg))

    poller.set_callback(wrapped_callback)

    print("Starting poller...")
    poller.start()

    print("Waiting 10 seconds...")
    await asyncio.sleep(10)

    print("Stopping poller...")
    poller.stop()

    print()
    print("=== Database Check ===")
    for m in database.get_messages(limit=5):
        print(f"DB: {m}")

asyncio.run(main())
