from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Event


# ✅ Custom User Admin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "phone", "is_verified", "is_staff", "date_joined")
    list_filter = ("is_verified", "is_staff", "is_superuser")
    search_fields = ("username", "email", "phone")
    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (
        ("Extra Info", {"fields": ("phone", "otp", "is_verified")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra Info", {"fields": ("phone", "otp", "is_verified")}),
    )


# ✅ Event Admin
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "end_date", "location", "organizer_name")
    search_fields = ("title", "location", "organizer_name", "organizer_email")
    list_filter = ("start_date", "end_date", "location")
    ordering = ("-start_date",)

    # Event detail page में कौनसे fields editable हों
    fieldsets = (
        ("Event Info", {"fields": ("title", "description", "banner")}),
        ("Schedule", {"fields": ("start_date", "end_date", "location")}),
        ("Organizer", {"fields": ("organizer_name", "organizer_email", "organizer_phone")}),
    )

    # Direct list page पर कौनसे fields editable हों
    list_editable = ("location", "organizer_name")
