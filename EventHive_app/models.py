from django.db import models
from django.contrib.auth.models import AbstractUser


# ------------------- Custom User Model -------------------
class CustomUser(AbstractUser):
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_organizer = models.BooleanField(default=False) 
    is_attendee = models.BooleanField(default=False)
    def __str__(self):
        return self.username


# ------------------- Event Category -------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Bootstrap icon class (e.g. bi-music-note)")
    
    def __str__(self):
        return self.name


# ------------------- Event Model -------------------
class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ("free", "Free"),
        ("paid", "Paid"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    banner_image = models.ImageField(upload_to="events/banners/", blank=True, null=True)

    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    location = models.CharField(max_length=200)

    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES, default="free")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    organizer_name = models.CharField(max_length=100)
    organizer_email = models.EmailField()
    organizer_phone = models.CharField(max_length=15)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # ✅ latest event first

    def __str__(self):
        return f"{self.title} ({self.start_date})"


# ------------------- Ticket Model -------------------
class Ticket(models.Model):
    TICKET_TYPE_CHOICES = [
        ("standard", "Standard"),
        ("vip", "VIP"),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    type = models.CharField(max_length=50, choices=TICKET_TYPE_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    available_quantity = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"{self.type} - {self.event.title}"


# ------------------- Booking Model -------------------
class Booking(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    booked_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return self.ticket.price * self.quantity

    def __str__(self):
        return f"{self.user.username} - {self.event.title} ({self.ticket.type})"


# ------------------- Attendee Model -------------------
class Attendee(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="attendees")
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")]
    )

    def __str__(self):
        return f"{self.name} - {self.booking.event.title}"
