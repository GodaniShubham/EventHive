from django.db import models
from django.contrib.auth.models import AbstractUser


# Custom User Model
class CustomUser(AbstractUser):
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


# Event Category
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Bootstrap icon class (e.g. bi-music-note)")

    def __str__(self):
        return self.name


# Event Model
class Event(models.Model):
    CATEGORY_CHOICES = [
        ("music", "Music"),
        ("sports", "Sports"),
        ("exhibition", "Exhibition"),
        ("conference", "Conference"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ Linked to category
    banner_image = models.ImageField(upload_to="events/banners/", blank=True, null=True)  # ✅ Better than URL
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    location = models.CharField(max_length=200)

    organizer_name = models.CharField(max_length=100)
    organizer_email = models.EmailField()
    organizer_phone = models.CharField(max_length=15)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.start_date})"

    class Meta:
        ordering = ["-created_at"]  # ✅ Latest event first


# Ticket Model (For Booking System)
class Ticket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    type = models.CharField(max_length=50, choices=[("standard", "Standard"), ("vip", "VIP")])
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    available_quantity = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"{self.type} - {self.event.title}"


# Booking Model
class Booking(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    booked_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return self.ticket.price * self.quantity

    def __str__(self):
        return f"{self.user.username} - {self.event.title} ({self.ticket.type})"
