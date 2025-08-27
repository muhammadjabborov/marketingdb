from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse
import csv
from .models import User, UserContact, UTMSource, UTMSourceType, UTMSourceSubType, Advertisement
from .tasks import send_advertisement_task


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "full_name", "username", "created_at")
    search_fields = ("telegram_id", "full_name", "username")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(UserContact)
class UserContactAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__telegram_id", "user__full_name", "phone_number")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)
    ordering = ("-created_at",)
    actions = ("export_user_contacts_csv",)

    @admin.action(description="Tanlanganlarni CSVga eksport qilish")
    def export_user_contacts_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = "attachment; filename=foydalanuvchi_kontaktlari.csv"
        writer = csv.writer(response)
        writer.writerow(["To'liq ism", "Telefon Raqami"])
        for contact in queryset.select_related("user"):
            writer.writerow([
                (contact.user.full_name if contact.user and contact.user.full_name else ""),
                f"+{str(contact.phone_number)}" or "",
            ])
        return response


@admin.register(UTMSourceSubType)
class UTMSourceSubTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)


@admin.register(UTMSourceType)
class UTMSourceTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "sub_type", "created_at")
    list_filter = ("sub_type",)
    search_fields = ("name", "sub_type__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("sub_type",)
    ordering = ("name",)


@admin.register(UTMSource)
class UTMSourceAdmin(admin.ModelAdmin):
    list_display = ("invite_link", "utm_source_type", "total_clicks", "total_joins", "created_at")
    list_filter = ("utm_source_type",)
    search_fields = ("invite_link", "utm_source_type__name", "utm_source_type__sub_type__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("utm_source_type",)
    ordering = ("-created_at",)


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ("id", "send_to_all", "created_at")
    list_filter = ("send_to_all",)
    search_fields = ("message_text",)
    filter_horizontal = ("utm_sources",)
    readonly_fields = ("created_at", "updated_at")
