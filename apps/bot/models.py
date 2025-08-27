from apps.common.models import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(BaseModel):
    full_name = models.CharField(_("full_name"), max_length=255, null=True, blank=True)
    username = models.CharField(_("username"), max_length=255, null=True, blank=True)
    telegram_id = models.BigIntegerField(_("telegram_id"), unique=True, db_index=True)

    def __str__(self):
        return f"{self.full_name}:{self.username}:{self.telegram_id}"

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")


class UserContact(BaseModel):
    user = models.ForeignKey("bot.User", verbose_name=_("user"), on_delete=models.CASCADE, related_name="user_contacts")
    phone_number = models.CharField(_("phone number"), max_length=32)

    def __str__(self):
        return f"{self.user_id}:{self.phone_number}"

    class Meta:
        verbose_name = _("User Contact")
        verbose_name_plural = _("User Contacts")
