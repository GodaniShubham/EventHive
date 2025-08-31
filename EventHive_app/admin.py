from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Event, Category, Ticket, Booking

# ---------------- Custom User Admin ----------------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        "username", "email", "phone", "is_verified",
        "is_organizer", "is_attendee",
        "is_staff", "is_superuser", "date_joined"
    )
    list_filter = ("is_verified", "is_organizer", "is_attendee", "is_staff", "is_superuser")
    search_fields = ("username", "email", "phone")
    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (
        ("Extra Info", {"fields": ("phone", "otp", "is_verified", "is_organizer", "is_attendee")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra Info", {"fields": ("phone", "otp", "is_verified", "is_organizer", "is_attendee")}),
    )

# ---------------- Category Admin ----------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)
    ordering = ("name",)

# ---------------- Event Admin ----------------
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title", "category", "event_type",
        "start_date", "end_date", "location",
        "status", "organizer_name", "organizer_email"
    )
    list_filter = ("event_type", "category", "status", "start_date")
    search_fields = ("title", "location", "organizer_name", "organizer_email")
    ordering = ("-start_date",)

    fieldsets = (
        ("Event Info", {"fields": ("title", "description", "category", "banner_image", "event_type", "status")}),
        ("Schedule", {"fields": ("start_date", "end_date", "start_time", "location")}),
        ("Organizer", {"fields": ("organizer_name", "organizer_email", "organizer_phone")}),
    )

    list_editable = ("status", "location")  # Edit directly in list view

# ---------------- Ticket Admin ----------------
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("event", "type", "price", "available_quantity")
    list_filter = ("type", "event")
    search_fields = ("event__title", "type")
    ordering = ("event", "type")

# ---------------- Booking Admin ----------------
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'event', 'date', 'status', 'transaction_id')
