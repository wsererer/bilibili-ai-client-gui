from config import config
from database import database
from utils.logger import logger
from utils.subtitle_extractor import subtitle_extractor
from openclaw_trigger import openclaw_trigger
from gui.signal_bus import signal_bus


def on_openclaw_complete(bv_id: str, success: bool, summary_text: str, error_msg: str):
    if success and summary_text:
        logger.info(f"OpenClaw 处理完成: {bv_id}, 摘要长度: {len(summary_text)}")
        messages = database.get_messages_by_bv_id(bv_id)
        sender_uid = ""
        sender_name = ""
        subtitle_text = ""
        for msg in messages:
            sender_uid = msg.get("sender_uid", "")
            sender_name = msg.get("sender_name", "")
            subtitle_text = msg.get("content", "")
            break
        database.add_summary(
            bv_id=bv_id,
            sender_uid=sender_uid,
            sender_name=sender_name,
            subtitle_text=subtitle_text,
            summary_text=summary_text,
        )
        triggered = database.get_messages_by_bv_id(bv_id, "triggered")
        for msg in triggered:
            database.update_message_status(msg["id"], "processed")
        logger.info(f"摘要已保存到数据库: {bv_id}")
        signal_bus.summary_added.emit({"bv_id": bv_id})
        stats = database.get_stats()
        signal_bus.stats_updated.emit(stats)
    else:
        logger.error(f"OpenClaw 处理失败: {bv_id}, 错误: {error_msg}")
        failed = database.get_messages_by_bv_id(bv_id, "triggered")
        for msg in failed:
            database.update_message_status(msg["id"], "openclaw_failed")
    signal_bus.openclaw_status.emit(bv_id, success)


def process_new_message(msg: dict):
    logger.info(f"process_new_message called with: {msg}")
    bv_id = msg.get("bv_id", "")
    sender_uid = msg.get("sender_uid", "")
    if not bv_id and not msg.get("content"):
        logger.info("No bv_id and no content, skipping")
        return
    msg_id = msg.get("msg_id", f"{bv_id}_{sender_uid}" if bv_id else msg.get("content", "")[:20])
    existing = database.get_message(msg_id)
    if existing and existing.get("status") not in ("pending", "not_whitelisted"):
        logger.info(f"消息 {msg_id} 已处理过 (status={existing.get('status')})，跳过")
        return
    is_whitelisted = database.is_whitelist(sender_uid)
    logger.info(f"sender_uid: {sender_uid}, is_whitelisted: {is_whitelisted}")
    database.add_message(
        msg_id=msg_id,
        sender_uid=sender_uid,
        sender_name=msg.get("sender_name", ""),
        bv_id=bv_id or "unknown",
        content=msg.get("content", ""),
    )
    if not sender_uid:
        database.update_message_status(msg_id, "no_sender_uid")
        logger.info(f"消息 {msg_id} 无发送者UID，已记录")
        signal_bus.message_status_changed.emit(msg_id)
        return
    if not is_whitelisted:
        database.update_message_status(msg_id, "not_whitelisted")
        logger.info(f"用户 {sender_uid} 不在白名单，已记录")
        signal_bus.message_status_changed.emit(msg_id)
        return
    logger.info(f"处理消息: {bv_id or 'N/A'} from {msg.get('sender_name', sender_uid)}")
    if bv_id and bv_id != "unknown":
        subtitle_text = subtitle_extractor.extract_text(f"https://www.bilibili.com/video/{bv_id}")
        if subtitle_text:
            openclaw_trigger.set_openclaw_path(config.get("openclaw_path", "openclaw"))
            openclaw_trigger.set_callback(on_openclaw_complete)
            success = openclaw_trigger.trigger(
                bv_id=bv_id,
                subtitle_text=subtitle_text,
                sender_uid=sender_uid,
                sender_name=msg.get("sender_name", ""),
            )
            if success:
                database.update_message_status(msg_id, "triggered")
                logger.info(f"已触发OpenClaw处理: {bv_id}")
            else:
                database.update_message_status(msg_id, "trigger_failed")
        else:
            database.update_message_status(msg_id, "no_subtitle")
            logger.warning(f"无法获取字幕: {bv_id}")
    signal_bus.message_status_changed.emit(msg_id)


def reprocess_blocked_messages(uid=None):
    blocked = database.get_not_whitelisted_messages()
    if not blocked:
        return
    logger.info(f"重新处理 {len(blocked)} 条被拦截的消息")
    for msg in blocked:
        msg_id = msg.get("id", "")
        sender_uid = msg.get("sender_uid", "")
        if uid and sender_uid != uid:
            continue
        if database.is_whitelist(sender_uid):
            database.update_message_status(msg_id, "pending")
            logger.info(f"消息 {msg_id} 用户 {sender_uid} 已加入白名单，重新处理")
            process_new_message({
                "msg_id": msg_id,
                "bv_id": msg.get("bv_id", ""),
                "sender_uid": sender_uid,
                "sender_name": msg.get("sender_name", ""),
                "content": msg.get("content", ""),
            })
