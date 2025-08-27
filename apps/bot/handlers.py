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
from aiogram.types import ReplyKeyboardRemove, ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import CommandStart

from apps.bot.config import bot, dp
from apps.bot.models import User, UserContact
from apps.bot.keyboards import build_contact_request_keyboard

logger = logging.getLogger(__name__)

# Kanalga qo‘shilish havolasi (siz bergan link)
JOIN_LINK = "https://t.me/+sXEjY_SpDLg3ZWQy"


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
    # Maydonlar o‘zgargan bo‘lsa — yangilaymiz
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
        "Assalomu alaykum! Agar kanalimizga qo‘shilmoqchi bo‘lsangiz, kerakli paytda sizdan telefon raqamingizni ulashish so‘raladi."
    )


@dp.chat_join_request_handler()
async def handle_chat_join_request(join_request: types.ChatJoinRequest):
    from_user = join_request.from_user
    chat = join_request.chat

    # Foydalanuvchi yozuvini ta’minlaymiz
    user, _ = User.objects.get_or_create(
        telegram_id=from_user.id,
        defaults={
            "full_name": f"{from_user.first_name or ''} {from_user.last_name or ''}".strip() or None,
            "username": from_user.username,
        },
    )
    # Ism/foydalanuvchi nomi o‘zgargan bo‘lsa — yangilaymiz
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

    # Pending chat_id ni foydalanuvchi FSM holatida saqlaymiz
    state = dp.current_state(chat=from_user.id, user=from_user.id)
    await state.update_data(pending_join_chat_id=chat.id)
    await state.set_state(JoinRequestState.waiting_for_contact.state)

    # Shaxsiy chatga telefon so‘rash xabarini yuboramiz
    try:
        await bot.send_message(
            from_user.id,
            f"Assalomu alaykum, {from_user.full_name or 'do‘stimiz'}!\n"
            "Kanalga qo‘shilish uchun, iltimos, telefon raqamingizni yuboring:\n\n"
            "📲 “Kontakt yuborish” tugmasini bosing",
            reply_markup=build_contact_request_keyboard(),
        )
    except Exception as exc:
        logger.exception("Kontakt so‘rovi xabarini yuborib bo‘lmadi: %s", exc)


@dp.message_handler(content_types=ContentType.CONTACT, state=JoinRequestState.waiting_for_contact)
async def handle_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    sender = message.from_user

    print(contact)  # Debug (ixtiyoriy)

    logger.info(
        "Kontakt qabul qilindi: user_id=%s, sender_id=%s, phone=%s",
        contact.user_id, sender.id, contact.phone_number
    )

    # Foydalanuvchi va kontaktni DB ga saqlash
    logger.info("Foydalanuvchi va kontaktni DB ga saqlash boshlandi...")
    db_save_ok = True
    try:
        logger.info("telegram_id=%s bo‘yicha foydalanuvchini olish/yaratish", sender.id)
        user, _ = User.objects.get_or_create(
            telegram_id=sender.id,
            defaults={
                "full_name": f"{sender.first_name or ''} {sender.last_name or ''}".strip() or None,
                "username": sender.username,
            },
        )
        logger.info("Foydalanuvchi tayyor: %s", user)

        # So‘nggi telefonni saqlaymiz
        logger.info(
            "UserContact yaratish: user_id=%s, phone=%s",
            user.id, contact.phone_number
        )
        UserContact.objects.create(user=user, phone_number=contact.phone_number)
        logger.info("UserContact muvaffaqiyatli yaratildi")
    except Exception as exc:
        db_save_ok = False
        logger.exception("Kontaktni DB ga saqlashda xatolik: %s", exc)
        await message.answer(
            "Telefon raqamingizni saqlashda server xatosi yuz berdi. Baribir kanalga qo‘shishimizga harakat qilamiz.",
            reply_markup=ReplyKeyboardRemove(),
        )

    # Pending chatni olish (join requestni tasdiqlash uchun)
    logger.info("Holatdan pending chat ma’lumotlarini olayapmiz...")
    data = await state.get_data()
    pending_chat_id = data.get("pending_join_chat_id")
    logger.info("Holatdan olingan chat_id: %s", pending_chat_id)

    # Inline tugma: kanalga o‘tish
    join_btn = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text="🔗 Kanalga o‘tish", url=JOIN_LINK)
    )

    try:
        if pending_chat_id:
            logger.info("Join requestni tasdiqlashga urinyapmiz: chat_id=%s, user_id=%s",
                        pending_chat_id, sender.id)
            await bot.approve_chat_join_request(chat_id=pending_chat_id, user_id=sender.id)
            logger.info("Join request muvaffaqiyatli tasdiqlandi!")

            phone_for_text = contact.phone_number
            if db_save_ok:
                await message.answer(
                    "🤩 Muvaffaqiyatli ro‘yxatdan o‘tdingiz!\n\n"
                    f"📱 Telefon raqamingiz: {phone_for_text}\n"
                    "🎉 Siz endi kanalimiz a’zosisiz. Kanalga o‘tish uchun tugmani bosing 👇🏻",
                    reply_markup=join_btn
                )
            else:
                await message.answer(
                    "Siz kanalga qo‘shildingiz, biroq telefon raqamingizni saqlab bo‘lmadi.\n\n"
                    f"📱 Oxirgi yuborgan raqamingiz: {phone_for_text}\n"
                    "Kanalga o‘tish uchun tugmani bosing 👇🏻",
                    reply_markup=join_btn
                )
        else:
            logger.warning("Holatda pending chat_id topilmadi")
            await message.answer(
                "Rahmat! Telefon raqamingizni qabul qildik.",
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as exc:
        logger.exception("Join requestni tasdiqlab bo‘lmadi: %s", exc)
        await message.answer(
            "Raqamingiz saqlandi, biroq avtomatik tasdiqlashda muammo yuz berdi. Admin tez orada ko‘rib chiqadi.",
            reply_markup=ReplyKeyboardRemove()
        )
    finally:
        logger.info("Holatni yakunlayapmiz va tozalayapmiz...")
        await state.finish()
        logger.info("Holat muvaffaqiyatli yakunlandi")
