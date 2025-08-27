# apps/bot/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.bot.models import Advertisement
from apps.bot.tasks import send_advertisement_task


@receiver(post_save, sender=Advertisement)
def send_ad_on_create(sender, instance: Advertisement, created: bool, **kwargs):
    if created:
        send_advertisement_task.delay(instance.id)
