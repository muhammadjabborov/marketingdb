from django.contrib import admin
from .models import User, UserContact


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "full_name", "username", "created_at")
    search_fields = ("telegram_id", "full_name", "username")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(UserContact)
class UserContactAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "created_at")
    search_fields = ("user__telegram_id", "user__full_name", "phone_number")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)
    ordering = ("-created_at",)
