import os

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from celery import shared_task
import logging
from django.conf import settings
from apps.bot.models import Advertisement, User
from apps.bot.config import bot
import asyncio

logger = logging.getLogger(__name__)


def sanitize_telegram_html(html_text: str) -> str:
    if not html_text:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")

        for p in soup.find_all("p"):
            p.insert_before("\n\n")
            p.unwrap()

        for br in soup.find_all("br"):
            br.replace_with("\n")

        allowed_tags = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "code", "pre", "a"}

        for tag in soup.find_all(True):
            if tag.name not in allowed_tags:
                tag.unwrap()
            else:
                if tag.name == "a":
                    href = tag.get("href")
                    tag.attrs = {"href": href} if href and (href.startswith("http://") or href.startswith("https://")) else {}
                else:
                    tag.attrs = {}

        text = str(soup)
        return text.strip()
    except Exception:
        import re
        text = html_text
        text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        text = text.replace("</p>", "\n\n").replace("<p>", "")
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()


async def send_broadcast(user_id, ad):
    try:
        if ad.photo and hasattr(ad.photo, 'url') and ad.photo.url:
            raw_url = ad.photo.url
            make_url = raw_url if raw_url.startswith("http") else f"{settings.HOST.rstrip('/')}/{raw_url.lstrip('/')}"
            caption = sanitize_telegram_html(ad.message_text)
            await bot.send_photo(user_id, photo=make_url, caption=caption, parse_mode="HTML")
        else:
            text = sanitize_telegram_html(ad.message_text)
            await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Error sending broadcast to member {user_id}: {str(e)}")


@shared_task
def send_advertisement_task(announcement_id):
    announcement = Advertisement.objects.get(id=announcement_id)
    users = User.objects.all()

    if announcement.send_to_all:
        users = User.objects.all()
    else:
        users = User.objects.filter(source__in=announcement.utm_sources.all())

    async def send_notifications():
        for user in users:
            await send_broadcast(user_id=user.telegram_id, ad=announcement)

    asyncio.run(send_notifications())
