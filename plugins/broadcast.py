import asyncio
import contextlib

from pyrogram import Client, enums, errors, filters
from pyrogram.helpers import ikb
from pyrogram.types import CallbackQuery, Message

from bot import (
    authorized_users_only,
    del_user,
    get_protect_content,
    get_users,
    helper_buttons,
    helper_handlers,
    logger,
)

BroadcastRunning, BroadcastSent, BroadcastFailed, BroadcastTotal = (
    False,
    0,
    0,
    0,
)


def is_not_supergroup(_, __, message: Message) -> bool:
    return message.chat.type == enums.ChatType.GROUP


filters_group = filters.create(is_not_supergroup, "filters_group")


@Client.on_message(~filters_group & filters.command(["broadcast", "bc"]))
@authorized_users_only
async def broadcast_handler(_, message: Message) -> None:
    global BroadcastRunning
    global BroadcastSent
    global BroadcastFailed
    global BroadcastTotal

    if not (broadcast_msg := message.reply_to_message):
        if not BroadcastRunning:
            await message.reply_text(
                "<i>Balas pesan yang ingin Anda siarkan!</i>",
                quote=True,
            )
        else:
            await message.reply_text(
                "<b>Broadcast Status</b>:\n"
                f"  - <code>Sent  : {BroadcastSent}/{BroadcastTotal}</code>\n"
                f"  - <code>Failed: {BroadcastFailed}</code>",
                quote=True,
                reply_markup=ikb(helper_buttons.Broadcast),
            )
        return

    else:
        if BroadcastRunning:
            return await message.reply_text(
                "<i>Saat ini siaran sedang berjalan, periksa status tanpa balasan</i>",
                quote=True,
            )

    progress_msg = await message.reply_text(
        "<i>Broadcasting...</i>",
        quote=True,
        reply_markup=ikb(helper_buttons.Broadcast),
    )

    users, admins = await get_users(), helper_handlers.admins
    user_ids = [user for user in users if user not in admins]

    BroadcastRunning, BroadcastTotal = True, len(user_ids)
    logger.info("Broadcast: Memulai...")

    for user_id in user_ids:
        if not BroadcastRunning:
            break

        protect_content = await get_protect_content()
        try:
            await broadcast_msg.copy(user_id, protect_content=protect_content)
            BroadcastSent += 1
        except errors.FloodWait as flood:
            await asyncio.sleep(flood.value)
            logger.warning(f"FLOOD_WAIT: Sleep {flood.value}", exc_info=flood)
        except errors.RPCError:
            await del_user(user_id)
            BroadcastFailed += 1

        if (BroadcastSent + BroadcastFailed) % 250 == 0:
            asyncio.create_task(broadcast_progress(progress_msg))

    if BroadcastSent + BroadcastFailed == BroadcastTotal:
        await message.reply_text(
            "<b>Broadcast Finished</b>\n"
            f"<code>  - Sent  : {BroadcastSent}/{BroadcastTotal}</code>\n"
            f"<code>  - Failed: {BroadcastFailed}</code>",
            quote=True,
            reply_markup=ikb(helper_buttons.Close),
        )

        logger.info("Broadcast: Finished")

    else:
        await message.reply_text(
            "<b>Broadcast Berhenti</b>\n"
            f"<code>  - Sent  : {BroadcastSent}/{BroadcastTotal}</code>\n"
            f"<code>  - Failed: {BroadcastFailed}</code>",
            quote=True,
            reply_markup=ikb(helper_buttons.Close),
        )

        logger.info("Broadcast: Berhenti")

    await progress_msg.delete()

    BroadcastRunning, BroadcastSent, BroadcastFailed, BroadcastTotal = (
        False,
        0,
        0,
        0,
    )


@Client.on_callback_query(filters.regex(r"^broadcast"))
async def broadcast_handler_query(_, query: CallbackQuery) -> None:
    global BroadcastRunning
    global BroadcastSent
    global BroadcastFailed
    global BroadcastTotal

    query_data = query.data.split()[1]
    if query_data == "refresh":
        await query.message.edit_text("<i>Refreshing...</i>")

        await query.message.edit_text(
            "<b>Broadcast Status</b>:\n"
            f"  - <code>Sent  : {BroadcastSent}/{BroadcastTotal}</code>\n"
            f"  - <code>Failed: {BroadcastFailed}</code>",
            reply_markup=ikb(helper_buttons.Broadcast),
        )

    elif query_data == "stop":
        await query.message.edit_text("<i>Broadcast telah dihentikan!</i>")

        BroadcastRunning = False


async def broadcast_progress(message: Message) -> Message:
    global BroadcastSent
    global BroadcastFailed
    global BroadcastTotal

    with contextlib.suppress(Exception):
        await message.edit_text(
            "<b>Broadcast Status</b>:\n"
            f"  - <code>Sent  : {BroadcastSent}/{BroadcastTotal}</code>\n"
            f"  - <code>Failed: {BroadcastFailed}</code>",
            reply_markup=ikb(helper_buttons.Broadcast),
        )
