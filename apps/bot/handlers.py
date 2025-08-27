# apps/bot/handlers.py

import os

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import base64
import logging
import django

django.setup()

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove, ContentType
from aiogram.dispatcher.filters import CommandStart
from apps.bot.config import bot, dp
from apps.bot.models import User, UserContact
from apps.bot.keyboards import build_contact_request_keyboard

logger = logging.getLogger(__name__)


class JoinRequestState(StatesGroup):
    waiting_for_contact = State()


@dp.message_handler(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    telegram_user = message.from_user
    user, _ = User.objects.get_or_create(
        telegram_id=telegram_user.id,
        defaults={
            "full_name": f"{telegram_user.first_name or ''} {telegram_user.last_name or ''}".strip() or None,
            "username": telegram_user.username,
        },
    )
    # Update fields in case they changed
    updated = False
    full_name_now = f"{telegram_user.first_name or ''} {telegram_user.last_name or ''}".strip() or None
    if user.full_name != full_name_now:
        user.full_name = full_name_now
        updated = True
    if user.username != telegram_user.username:
        user.username = telegram_user.username
        updated = True
    if updated:
        user.save(update_fields=["full_name", "username"])

    await message.answer(
        "Welcome! If you are trying to join our channel, you'll be prompted to share your phone number when needed."
    )


@dp.chat_join_request_handler()
async def handle_chat_join_request(join_request: types.ChatJoinRequest):
    from_user = join_request.from_user
    chat = join_request.chat

    # Ensure we have a user record
    user, _ = User.objects.get_or_create(
        telegram_id=from_user.id,
        defaults={
            "full_name": f"{from_user.first_name or ''} {from_user.last_name or ''}".strip() or None,
            "username": from_user.username,
        },
    )
    # Update name/username if changed
    updated = False
    full_name_now = f"{from_user.first_name or ''} {from_user.last_name or ''}".strip() or None
    if user.full_name != full_name_now:
        user.full_name = full_name_now
        updated = True
    if user.username != from_user.username:
        user.username = from_user.username
        updated = True
    if updated:
        user.save(update_fields=["full_name", "username"])

    # Store the pending join chat_id in the user's private state
    state = dp.current_state(chat=from_user.id, user=from_user.id)
    await state.update_data(pending_join_chat_id=chat.id)
    # IMPORTANT: set the state on this exact FSM context
    await state.set_state(JoinRequestState.waiting_for_contact.state)

    # Prompt the user in private chat to share phone number
    try:
        await bot.send_message(
            from_user.id,
            "You are trying to join the channel. To proceed, please share your phone number.",
            reply_markup=build_contact_request_keyboard(),
        )
    except Exception as exc:
        logger.exception("Failed to send contact request message: %s", exc)


@dp.message_handler(content_types=ContentType.CONTACT, state=JoinRequestState.waiting_for_contact)
async def handle_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    sender = message.from_user

    # Debug print if needed
    print(contact)

    # Log contact details for debugging
    logger.info(
        "Contact received: user_id=%s, sender_id=%s, phone=%s",
        contact.user_id, sender.id, contact.phone_number
    )

    # Persist user and contact
    logger.info("Starting to save user and contact to database...")
    db_save_ok = True
    try:
        logger.info("Getting/creating user with telegram_id=%s", sender.id)
        user, _ = User.objects.get_or_create(
            telegram_id=sender.id,
            defaults={
                "full_name": f"{sender.first_name or ''} {sender.last_name or ''}".strip() or None,
                "username": sender.username,
            },
        )
        logger.info("User retrieved/created: %s", user)

        # Save latest phone
        logger.info(
            "Creating UserContact for user_id=%s, phone=%s",
            user.id, contact.phone_number
        )
        UserContact.objects.create(user=user, phone_number=contact.phone_number)
        logger.info("UserContact created successfully")

    except Exception as exc:
        db_save_ok = False
        logger.exception("Failed to save contact to DB: %s", exc)
        await message.answer(
            "We couldn't save your phone due to a server error. We'll still try to approve your join request.",
            reply_markup=ReplyKeyboardRemove(),
        )

    # Retrieve pending chat to approve
    logger.info("Retrieving pending chat data from state...")
    data = await state.get_data()
    pending_chat_id = data.get("pending_join_chat_id")
    logger.info("Pending chat_id from state: %s", pending_chat_id)

    try:
        if pending_chat_id:
            logger.info(
                "Attempting to approve join request for chat_id=%s, user_id=%s",
                pending_chat_id, sender.id
            )
            await bot.approve_chat_join_request(chat_id=pending_chat_id, user_id=sender.id)
            logger.info("Join request approved successfully!")

            if db_save_ok:
                await message.answer(
                    "Thanks! Your request has been approved.",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await message.answer(
                    "Your request has been approved. We could not save your phone due to a server issue.",
                    reply_markup=ReplyKeyboardRemove()
                )
        else:
            logger.warning("No pending chat_id found in state")
            await message.answer(
                "Thanks! We received your phone number.",
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as exc:
        logger.exception("Failed to approve join request: %s", exc)
        await message.answer(
            "We saved your number but failed to approve automatically. An admin will review shortly.",
            reply_markup=ReplyKeyboardRemove()
        )
    finally:
        logger.info("Finishing state and cleaning up...")
        await state.finish()
        logger.info("State finished successfully")
