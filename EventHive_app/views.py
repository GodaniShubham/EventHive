import random
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator   # ✅ Import paginator
from .models import CustomUser, Event   # ✅ Event भी import किया

# ------------------- Register -------------------
def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')

        if not all([username, email, phone, password]):
            messages.error(request, "All fields are required.")
            return redirect("register")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("register")
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect("register")

        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            password=password,
            otp=otp,
            is_verified=False
        )

        try:
            send_mail(
                subject="EventHive OTP Verification",
                message=f"Your OTP for EventHive verification is: {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, "OTP sent to your email.")
        except Exception as e:
            messages.error(request, f"Failed to send OTP: {str(e)}")
            user.delete()
            return redirect("register")

        return redirect("verify_otp", user_id=user.id)

    return render(request, "register.html")


# ------------------- Verify OTP -------------------
def verify_otp(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        if not entered_otp:
            messages.error(request, "Please enter the OTP.")
            return render(request, "verify.html", {"email": user.email})

        if user.otp == entered_otp:
            user.is_verified = True
            user.otp = None
            user.save()
            login(request, user)
            messages.success(request, "Account verified successfully!")
            return redirect("attendee_home")   # ✅ home → attendee_home
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, "verify.html", {"email": user.email})

    return render(request, "verify.html", {"email": user.email})


# ------------------- Login -------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not all([email, password]):
            messages.error(request, "Email and password are required.")
            return redirect("login")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, "User does not exist.")
            return redirect("login")

        user = authenticate(request, username=user.username, password=password)
        if user:
            if user.is_verified:
                login(request, user)
                messages.success(request, "Logged in successfully!")
                return redirect("attendee_home")   # ✅ home → attendee_home
            else:
                messages.error(request, "Please verify your email first.")
                return redirect("verify_otp", user_id=user.id)
        else:
            messages.error(request, "Invalid credentials.")
            return redirect("login")

    return render(request, "login.html")


# ------------------- Logout -------------------
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("login")


# ------------------- Event Detail -------------------
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, "event_detail.html", {"event": event})


# ------------------- Attendee Home (Events List with Pagination) -------------------
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.shortcuts import render

def attendee_home(request):
    # ---- Dummy events (no DB needed) ----
    base_imgs = [
        "https://picsum.photos/seed/music/800/500",
        "https://picsum.photos/seed/exhibition/800/500",
        "https://picsum.photos/seed/sports/800/500",
        "https://picsum.photos/seed/conference/800/500",
        "https://picsum.photos/seed/meetup/800/500",
        "https://picsum.photos/seed/fest/800/500",
    ]
    categories = ["Music", "Exhibition", "Sports", "Conference", "Meetup", "Festival"]
    locations  = ["Delhi", "Mumbai", "Pune", "Bengaluru", "Hyderabad", "Jaipur"]

    dummy_events = []
    for i in range(1, 25):  # 24 dummy cards
        dummy_events.append({
            "id": i,
            "title": f"Sample Event #{i}",
            "description": "This is a short sample description for the event. Enjoy networking & fun!",
            "location": locations[i % len(locations)],
            "start_date": (datetime.now() + timedelta(days=i)),
            "category": categories[i % len(categories)],
            "banner": base_imgs[i % len(base_imgs)],  # direct image URL
        })

    # ---- Pagination (6 per page) ----
    paginator = Paginator(dummy_events, 6)
    page_number = request.GET.get("page")
    events = paginator.get_page(page_number)

    return render(request, "attendeehome.html", {"events": events})

def book_tickets(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, "tickets.html", {"event": event})


def register_tickets(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        standard_qty = int(request.POST.get("standard_qty", 0))
        vip_qty = int(request.POST.get("vip_qty", 0))

        if standard_qty == 0 and vip_qty == 0:
            messages.error(request, "⚠️ Please select at least one ticket.")
            return redirect("book_tickets", event_id=event.id)

        messages.success(
            request,
            f"🎟 Tickets booked successfully! Standard: {standard_qty}, VIP: {vip_qty}"
        )
        return redirect("event_detail", event_id=event.id)

    return redirect("book_tickets", event_id=event.id)

