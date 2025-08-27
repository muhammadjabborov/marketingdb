from apps.common.models import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _
from ckeditor.fields import RichTextField


class User(BaseModel):
    full_name = models.CharField(_("full_name"), max_length=255, null=True, blank=True)
    username = models.CharField(_("username"), max_length=255, null=True, blank=True)
    telegram_id = models.BigIntegerField(_("telegram_id"), unique=True, db_index=True)
    source = models.ForeignKey("bot.UTMSource", models.SET_NULL, null=True, blank=True)

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


class UTMSourceSubType(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("name"))

    class Meta:
        verbose_name = "UTM SourceSubType"
        verbose_name_plural = "UTM SourceSubTypes"

    def __str__(self):
        return self.name


class UTMSourceType(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("name"))
    sub_type = models.ForeignKey("bot.UTMSourceSubType", verbose_name=_("sub_type"), on_delete=models.SET_NULL,
                                 null=True, blank=True)

    def __str__(self):
        return f"{self.name} : {self.sub_type.name}"

    class Meta:
        verbose_name = "UTM SourceType"
        verbose_name_plural = "UTM SourceTypes"


class UTMSource(BaseModel):
    name = models.CharField(_("name"), null=True)
    invite_link = models.URLField(_("url link"))
    utm_source_type = models.ForeignKey("bot.UTMSourceType", on_delete=models.CASCADE,
                                        verbose_name=_("utm source type"))

    total_joins = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)

    class Meta:
        verbose_name = "UTM Source"
        verbose_name_plural = "UTM Sources"

    def __str__(self):
        return self.name


class Advertisement(BaseModel):
    message_text = RichTextField(verbose_name=_("message text"))
    photo = models.ImageField(upload_to="ads/", null=True, blank=True)
    send_to_all = models.BooleanField(default=False)
    utm_sources = models.ManyToManyField("bot.UTMSource", blank=True, related_name="advertisements")

    class Meta:
        verbose_name = _("Advertisement")
        verbose_name_plural = _("Advertisements")

    def __str__(self):
        try:
            text = self.message_text or ""
            return (text[:47] + "…") if len(text) > 48 else text
        except Exception:
            return f"Advertisement {self.id}"
