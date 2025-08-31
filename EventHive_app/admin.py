from django.contrib import admin
from .models import CustomUser, Category, Event, Ticket, Booking, Attendee, Profile
from django.contrib.auth.admin import UserAdmin
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    model = CustomUser
    list_display = ["id", "username", "email", "phone", "is_verified", "is_organizer", "is_attendee"]
    fieldsets = UserAdmin.fieldsets + (
        ("Extra Info", {"fields": ("phone", "otp", "is_verified", "is_organizer", "is_attendee", "image")}),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'event_type', 'status', 'organizer_name']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['event', 'type', 'price', 'available_quantity']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'ticket', 'quantity', 'payment_status', 'payment_id', 'booked_at']

@admin.register(Attendee)
class AttendeeAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'gender', 'booking']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'bio']