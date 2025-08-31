import random
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from .models import CustomUser, Event, Category, Ticket, Booking


# ------------------- Register -------------------
def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')

        if not all([username, email, phone, password]):
            messages.error(request, "⚠️ All fields are required.")
            return redirect("register")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "⚠️ Email already registered!")
            return redirect("register")
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "⚠️ Username already taken!")
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
                message=f"Your OTP is: {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, "✅ OTP sent to your email.")
        except Exception as e:
            messages.error(request, f"❌ Failed to send OTP: {str(e)}")
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
            messages.error(request, "⚠️ Please enter the OTP.")
        elif user.otp == entered_otp:
            user.is_verified = True
            user.otp = None
            user.save()
            login(request, user)
            messages.success(request, "🎉 Account verified successfully!")
            return redirect("attendee_home")
        else:
            messages.error(request, "❌ Invalid OTP. Please try again.")

    return render(request, "verify.html", {"email": user.email})


# ------------------- Login -------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not all([email, password]):
            messages.error(request, "⚠️ Email and password required.")
            return redirect("login")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, "❌ User does not exist.")
            return redirect("login")

        user = authenticate(request, username=user.username, password=password)
        if user:
            if user.is_verified:
                login(request, user)
                messages.success(request, "✅ Logged in successfully!")
                return redirect("attendee_home")
            else:
                return redirect("verify_otp", user_id=user.id)
        else:
            messages.error(request, "❌ Invalid credentials.")

    return render(request, "login.html")


# ------------------- Logout -------------------
@login_required(login_url="login")
def logout_view(request):
    logout(request)
    messages.success(request, "✅ Logged out successfully!")
    return redirect("login")


# ------------------- Home -------------------
@login_required(login_url="login")
def home(request):
    context = {
        'some_data': 'value',
    }
    return render(request, 'home.html', context)


# ------------------- Event Detail -------------------
@login_required(login_url="login")
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    tickets = Ticket.objects.filter(event=event)
    registered = Booking.objects.filter(event=event, user=request.user).exists()

    return render(request, "event_detail.html", {
        "event": event,
        "tickets": tickets,
        "registered": registered
    })


@login_required(login_url="login")
def profile_view(request):
    return render(request, "profile.html", {"user": request.user})
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Event, Category

def attendee_home(request):
    events = Event.objects.all()
    categories = Category.objects.all()

    # --- Get filter values ---
    category_filter = request.GET.get("category", "all")
    date_filter = request.GET.get("date", "")
    event_type_filter = request.GET.get("event_type", "all")
    search_query = request.GET.get("search", "")

    # --- Apply filters ---
    if category_filter != "all":
        events = events.filter(category__name__iexact=category_filter)

    if date_filter:
        events = events.filter(start_date=date_filter)

    if event_type_filter != "all":
        events = events.filter(event_type__iexact=event_type_filter)

    if search_query:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    # --- Pagination ---
    paginator = Paginator(events, 6)  # 6 events per page
    page_number = request.GET.get("page")
    events_page = paginator.get_page(page_number)

    # --- Preserve filters in pagination links ---
    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")  # remove page to append later

    return render(request, "attendeehome.html", {
        "events": events_page,
        "categories": categories,
        "category_filter": category_filter,
        "date_filter": date_filter,
        "event_type_filter": event_type_filter,
        "search_query": search_query,
        "query_params": query_params.urlencode(),  # for pagination links
    })


def profile_page(request):
    return render(request, "profile_page.html")


# ------------------- Ticket Booking Flow -------------------
@login_required(login_url="login")
def book_tickets(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, "tickets.html", {"event": event})



# ------------------- Organizer Attendees -------------------
@login_required(login_url="login")
def attendees_list(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer_email=request.user.email)
    attendees = Booking.objects.filter(event=event).select_related("user")

    gender_filter = request.GET.get("gender")
    attended_filter = request.GET.get("attended")
    search_query = request.GET.get("search")

    if gender_filter and gender_filter != "all":
        attendees = attendees.filter(user__gender__iexact=gender_filter)

    if attended_filter and attended_filter != "all":
        attendees = attendees.filter(status__iexact=attended_filter)

    if search_query:
        attendees = attendees.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__phone__icontains=search_query)
        )

    return render(request, "organizer/attendees_list.html", {
        "event": event,
        "attendees": attendees,
        "gender_filter": gender_filter,
        "attended_filter": attended_filter,
        "search_query": search_query,
    })


# ------------------- Helper -------------------
def get_organizer_event(user, event_id):
    return get_object_or_404(Event, id=event_id, organizer_email=user.email)


# ------------------- Payment -------------------
@login_required(login_url="login")
def make_payment(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    tickets = request.session.get("tickets", {})
    attendees = request.session.get("attendees", [])

    if not tickets or not attendees:
        messages.error(request, "⚠️ Invalid booking flow.")
        return redirect("book_tickets", event_id=event.id)

    return render(request, "payment.html", {"event": event, "tickets": tickets, "attendees": attendees})


# ------------------- Organizer Section -------------------
@login_required(login_url="login")
def organizer_home(request):
    if not getattr(request.user, "is_organizer", False):
        messages.error(request, "❌ Unauthorized access!")
        return redirect("attendee_home")

    events = Event.objects.filter(organizer_name=request.user.username).order_by("-created_at")
    return render(request, "organizer/home.html", {"events": events})

@login_required
def create_event(request):
    if not getattr(request.user, "is_organizer", False):
        messages.error(request, "❌ Unauthorized access!")
        return redirect("attendee_home")

    categories = Category.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        start_time = request.POST.get("start_time")
        location = request.POST.get("location")
        event_type = request.POST.get("event_type")
        category_id = request.POST.get("category")
        banner_image = request.FILES.get("banner_image")  # ✅ handle uploaded image

        event = Event.objects.create(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            location=location,
            event_type=event_type,
            organizer_name=request.user.username,
            organizer_email=request.user.email,
            organizer_phone=request.user.phone,
            banner_image=banner_image,
            category=Category.objects.filter(id=category_id).first() if category_id else None
        )
        messages.success(request, "✅ Event created successfully with image!")
        return redirect("organizer_home")

    return render(request, "organizer/create_event.html", {"categories": categories})

@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer_email=request.user.email)
    categories = Category.objects.all()

    if request.method == "POST":
        event.title = request.POST.get("title")
        event.description = request.POST.get("description")
        event.start_date = request.POST.get("start_date")
        event.end_date = request.POST.get("end_date")
        event.start_time = request.POST.get("start_time")
        event.location = request.POST.get("location")
        event.event_type = request.POST.get("event_type")
        category_id = request.POST.get("category")
        event.category = Category.objects.filter(id=category_id).first() if category_id else None

        banner_image = request.FILES.get("banner_image")
        if banner_image:
            event.banner_image = banner_image  # ✅ update image if uploaded

        event.save()
        messages.success(request, "✅ Event updated successfully!")
        return redirect("organizer_home")

    return render(request, "organizer/edit_event.html", {
        "event": event,
        "categories": categories
    })


@login_required(login_url="login")
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer_email=request.user.email)

    if request.method == "POST":
        event.delete()
        messages.success(request, "🗑️ Event deleted successfully!")
        return redirect("organizer_home")

    return render(request, "organizer/confirm_delete.html", {"event": event})


@login_required(login_url="login")
def manage_tickets(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer_email=request.user.email)
    tickets = Ticket.objects.filter(event=event)

    if request.method == "POST":
        ticket_type = request.POST.get("type")
        price = request.POST.get("price")
        quantity = request.POST.get("available_quantity")

        Ticket.objects.create(
            event=event,
            type=ticket_type,
            price=price,
            available_quantity=quantity
        )
        messages.success(request, "🎟️ Ticket added successfully!")
        return redirect("manage_tickets", event_id=event.id)

    return render(request, "organizer/manage_tickets.html", {
        "event": event,
        "tickets": tickets
    })


@login_required(login_url="login")
def view_bookings(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer_email=request.user.email)
    bookings = Booking.objects.filter(event=event).select_related("user", "ticket")

    return render(request, "organizer/view_bookings.html", {
        "event": event,
        "bookings": bookings
    })


@login_required(login_url="login")
def attendee_details(request, event_id, booking_id):
    event = get_object_or_404(Event, id=event_id, organizer_email=request.user.email)
    booking = get_object_or_404(Booking, id=booking_id, event=event)

    return render(request, "organizer/attend_details.html", {
        "event": event,
        "booking": booking,
        "attendee": booking.user,
        "ticket": booking.ticket,
    })

@login_required(login_url="login")
def register_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Check if already registered
    if Booking.objects.filter(event=event, user=request.user).exists():
        messages.info(request, "⚠️ You are already registered for this event.")
        return redirect("event_detail", event_id=event.id)

    # ✅ Instead of directly creating a booking, send user to ticket booking page
    return redirect("book_tickets", event_id=event.id)


import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@login_required
def make_payment(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        # Collect attendee info from POST
        attendees = []
        for key in request.POST:
            if key.startswith("attendee_") and key.endswith("_name"):
                index = key.split("_")[1]
                attendee = {
                    "name": request.POST.get(f"attendee_{index}_name"),
                    "email": request.POST.get(f"attendee_{index}_email"),
                    "phone": request.POST.get(f"attendee_{index}_phone"),
                    "gender": request.POST.get(f"attendee_{index}_gender"),
                    "ticket_type": "Standard" if index == "1" else "VIP"
                }
                attendees.append(attendee)

        # Store attendees in session
        request.session["attendees"] = attendees

        # Calculate amount dynamically (example: Standard=0, VIP=500)
        total_amount = 0
        for attendee in attendees:
            if attendee["ticket_type"] == "VIP":
                total_amount += 50000  # in paise (₹500)
            else:
                total_amount += 0  # Standard ticket free

        # Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # Create order
        order = client.order.create({
            "amount": total_amount,
            "currency": "INR",
            "payment_capture": "1"
        })

        # Store order info in session
        request.session["order_id"] = order["id"]
        request.session["total_amount"] = total_amount

        return render(request, "payment_page.html", {
            "event": event,
            "order_id": order["id"],
            "total_amount": total_amount,
            "razorpay_key": settings.RAZORPAY_KEY_ID
        })

@csrf_exempt
@login_required
def payment_success(request, event_id):
    if request.method == "POST":
        data = request.POST
        attendees = request.session.get("attendees", [])
        event = get_object_or_404(Event, id=event_id)

        # Save booking for each attendee
        for attendee in attendees:
            Booking.objects.create(
                user=request.user,
                event=event,
                ticket_type=attendee["ticket_type"],
                attendee_name=attendee["name"],
                attendee_email=attendee["email"],
                attendee_phone=attendee["phone"],
                attendee_gender=attendee["gender"],
                payment_id=data.get("razorpay_payment_id"),
                amount_paid=request.session.get("total_amount", 0)/100  # in ₹
            )

        # Clear session
        request.session.pop("attendees", None)
        request.session.pop("order_id", None)
        request.session.pop("total_amount", None)

        messages.success(request, "✅ Payment successful & tickets booked!")
        return JsonResponse({"status": "success"})

