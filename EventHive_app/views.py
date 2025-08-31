import random
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import razorpay
from .models import CustomUser, Event, Category, Ticket, Booking, Attendee
from .models import Event 

# ------------------- Register -------------------
def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if not all([username, email, phone, password, role]):
            messages.error(request, "⚠️ All fields are required.")
            return redirect("register")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "⚠️ Email already registered!")
            return redirect("register")
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "⚠️ Username already taken!")
            return redirect("register")
        if CustomUser.objects.filter(phone=phone).exists():   # ✅ Add this
            messages.error(request, "⚠️ Phone number already registered!")
            return redirect("register")
        if role not in ["organizer", "attendee"]:
            messages.error(request, "⚠️ Invalid role selected.")
            return redirect("register")

        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            password=password,
            otp=otp,
            is_verified=False,
            is_organizer=(role == "organizer"),
            is_attendee=(role == "attendee")
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
            # Store user data in session
            request.session['user_data'] = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': 'organizer' if user.is_organizer else 'attendee'
            }
            request.session.modified = True
            messages.success(request, "🎉 Account verified successfully!")
            if user.is_organizer:
                return redirect("organizer_home")
            return redirect("attendee_home")
        else:
            messages.error(request, "❌ Invalid OTP. Please try again.")

    return render(request, "verify.html", {"email": user.email})

# ------------------- Login -------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if not all([email, password, role]):
            messages.error(request, "⚠️ Email, password, and role are required.")
            return redirect("login")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, "❌ User does not exist.")
            return redirect("login")

        # Check if the role matches
        if role == "organizer" and not user.is_organizer:
            messages.error(request, "❌ This account is not registered as an organizer.")
            return redirect("login")
        if role == "attendee" and not user.is_attendee:
            messages.error(request, "❌ This account is not registered as a normal user.")
            return redirect("login")

        user = authenticate(request, username=user.username, password=password)
        if user:
            if user.is_verified:
                login(request, user)
                # Store user data in session
                request.session['user_data'] = {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': 'organizer' if user.is_organizer else 'attendee'
                }
                request.session.modified = True
                messages.success(request, "✅ Logged in successfully!")
                if user.is_organizer:
                    return redirect("organizer_home")
                return redirect("attendee_home")
            else:
                return redirect("verify_otp", user_id=user.id)
        else:
            messages.error(request, "❌ Invalid credentials.")

    return render(request, "login.html")

# ------------------- Logout -------------------
@login_required(login_url="login")
def logout_view(request):
    # Clear session data
    request.session.flush()
    logout(request)
    messages.success(request, "✅ Logged out successfully!")
    return redirect("login")

# ------------------- Home -------------------
@login_required(login_url="login")
def home(request):
    context = {
        'user_data': request.session.get('user_data', {})
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
        "registered": registered,
        "user_data": request.session.get('user_data', {})
    })

# ------------------- Attendee Home -------------------
def attendee_home(request):
    events = Event.objects.all()
    categories = Category.objects.all()

    category_filter = request.GET.get("category", "all")
    date_filter = request.GET.get("date", "")
    event_type_filter = request.GET.get("event_type", "all")
    search_query = request.GET.get("search", "")

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

    paginator = Paginator(events, 6)
    page_number = request.GET.get("page")
    events_page = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")

    return render(request, "attendeehome.html", {
        "events": events_page,
        "categories": categories,
        "category_filter": category_filter,
        "date_filter": date_filter,
        "event_type_filter": event_type_filter,
        "search_query": search_query,
        "query_params": query_params.urlencode(),
        "user_data": request.session.get('user_data', {})
    })

# ------------------- Profile -------------------
@login_required(login_url="login")
def profile_view(request):
    return render(request, "profile.html", {
        "user": request.user,
        "user_data": request.session.get('user_data', {})
    })

from django.contrib.auth.decorators import login_required

@login_required(login_url="login")
def profile_page(request):
    user = request.user

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        bio = request.POST.get("bio")
        image = request.FILES.get("image")

        if full_name:
            user.first_name = full_name.split(" ")[0]
            if len(full_name.split(" ")) > 1:
                user.last_name = " ".join(full_name.split(" ")[1:])
        if email:
            user.email = email
        if bio:
            user.bio = bio  # if you add a bio field in CustomUser
        if image:
            user.image = image  # ✅ save uploaded profile pic

        user.save()
        messages.success(request, "✅ Profile updated successfully!")
        return redirect("profile_page")

    return render(request, "profile_page.html", {
        "user": user,
        "user_data": request.session.get("user_data", {})
    })

# ------------------- Ticket Booking Flow -------------------
@login_required(login_url="login")
def register_tickets(request, event_id):
    return redirect("book_tickets", event_id=event_id)

@login_required(login_url="login")
def book_tickets(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == "POST":
        standard = int(request.POST.get('standard_qty', 0))
        vip = int(request.POST.get('vip_qty', 0))

        if standard == 0 and vip == 0:
            messages.error(request, "⚠️ Please select at least one ticket.")
            return redirect("book_tickets", event_id=event_id)

        request.session["tickets"] = {
            "standard": standard,
            "vip": vip
        }
        request.session.modified = True

        return redirect("attendee_tickets", event_id=event_id)

    return render(request, "tickets.html", {
        "event": event,
        "user_data": request.session.get('user_data', {})
    })

def attendee_tickets(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    standard_qty = int(request.GET.get("standard_qty", 0))
    vip_qty = int(request.GET.get("vip_qty", 0))

    tickets = {
        "standard": range(standard_qty),
        "vip": range(vip_qty),
    }

    return render(request, "attendee_tickets.html", {
        "event": event,
        "tickets": tickets,
    })



@login_required(login_url="login")
def make_payment(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    tickets = request.session.get("tickets", {})

    if not tickets:
        messages.error(request, "⚠️ No tickets selected.")
        return redirect("book_tickets", event_id=event_id)

    if request.method == "POST":
        attendees = []
        total_tickets = tickets.get("standard", 0) + tickets.get("vip", 0)
        for i in range(1, total_tickets + 1):
            attendee = {
                "name": request.POST.get(f"attendee_{i}_name"),
                "email": request.POST.get(f"attendee_{i}_email"),
                "phone": request.POST.get(f"attendee_{i}_phone"),
                "gender": request.POST.get(f"attendee_{i}_gender"),
                "ticket_type": request.POST.get(f"attendee_{i}_ticket_type")
            }
            if not all([attendee["name"], attendee["email"], attendee["phone"], attendee["gender"], attendee["ticket_type"]]):
                messages.error(request, "⚠️ All attendee fields are required.")
                return redirect("attendee_ticket_page", event_id=event_id)
            attendees.append(attendee)

        request.session["attendees"] = attendees
        request.session.modified = True

        total_amount = 0
        standard_ticket = Ticket.objects.filter(event=event, type="standard").first()
        vip_ticket = Ticket.objects.filter(event=event, type="vip").first()
        for attendee in attendees:
            if attendee["ticket_type"] == "VIP" and vip_ticket:
                total_amount += int(vip_ticket.price * 100)  # Convert to paise
            elif attendee["ticket_type"] == "Standard" and standard_ticket:
                total_amount += int(standard_ticket.price * 100)

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order = client.order.create({
                "amount": total_amount,
                "currency": "INR",
                "payment_capture": "1"
            })
            request.session["order_id"] = order["id"]
            request.session["total_amount"] = total_amount
            request.session.modified = True
        except Exception as e:
            messages.error(request, f"❌ Failed to create Razorpay order: {str(e)}")
            return redirect("attendee_ticket_page", event_id=event_id)

        return render(request, "payment_page.html", {
            "event": event,
            "order_id": order["id"],
            "total_amount": total_amount,
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "user_data": request.session.get('user_data', {})
        })

    return redirect("attendee_ticket_page", event_id=event_id)

@csrf_exempt
@login_required
def payment_success(request, event_id):
    if request.method == "POST":
        data = request.POST
        attendees = request.session.get("attendees", [])
        event = get_object_or_404(Event, id=event_id)
        total_amount = request.session.get("total_amount", 0) / 100  # in ₹

        standard_ticket = Ticket.objects.filter(event=event, type="standard").first()
        vip_ticket = Ticket.objects.filter(event=event, type="vip").first()

        try:
            for attendee in attendees:
                ticket = vip_ticket if attendee["ticket_type"] == "VIP" else standard_ticket
                if ticket:
                    booking = Booking.objects.create(
                        user=request.user,
                        event=event,
                        ticket=ticket,
                        quantity=1,
                        attendee_name=attendee["name"],
                        attendee_email=attendee["email"],
                        attendee_phone=attendee["phone"],
                        attendee_gender=attendee["gender"],
                        payment_id=data.get("razorpay_payment_id"),
                        amount_paid=total_amount / len(attendees) if attendees else 0,
                        payment_status="paid"
                    )
                    Attendee.objects.create(
                        booking=booking,
                        name=attendee["name"],
                        email=attendee["email"],
                        phone=attendee["phone"],
                        gender=attendee["gender"]
                    )
            # Clear session data
            request.session.pop("attendees", None)
            request.session.pop("order_id", None)
            request.session.pop("total_amount", None)
            request.session.pop("tickets", None)
            request.session.modified = True
            messages.success(request, "✅ Payment successful & tickets booked!")
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})

# ------------------- Organizer Section -------------------
@login_required(login_url="login")
def organizer_home(request):
    if not request.user.is_organizer:
        messages.error(request, "❌ Unauthorized access!")
        return redirect("attendee_home")
    else:
        # All events for this organizer
        events = Event.objects.filter(organizer_name=request.user.username).order_by("-created_at")
        categories = Category.objects.all()

        # ---- Filters ----
        category_filter = request.GET.get("category", "all")
        date_filter = request.GET.get("date", "")
        search_query = request.GET.get("search", "")

        if category_filter != "all":
            events = events.filter(category__name__iexact=category_filter)
        if date_filter:
            events = events.filter(start_date=date_filter)
        if search_query:
            events = events.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(location__icontains=search_query)
            )

        # ---- Counters ----
        total_events = events.count()
        published_events = events.filter(is_published=True).count()
        draft_events = events.filter(is_published=False).count()
        tickets_sold = Ticket.objects.filter(event__in=events).count()

        # ---- Pagination ----
        paginator = Paginator(events, 12)  # 12 per page
        page_number = request.GET.get("page")
        events_page = paginator.get_page(page_number)

        # Preserve query params (for filters + pagination)
        query_params = request.GET.copy()
        if "page" in query_params:
            query_params.pop("page")

        return render(request, "organizer.html", {
            "events": events_page,
            "categories": categories,
            "category_filter": category_filter,
            "date_filter": date_filter,
            "search_query": search_query,
            "query_params": query_params.urlencode(),
            "user_data": request.session.get('user_data', {}),

            # 👇 Added counters
            "total_events": total_events,
            "published_events": published_events,
            "draft_events": draft_events,
            "tickets_sold": tickets_sold,
        })

@login_required(login_url="login")
def create_event(request):
    if not request.user.is_organizer:
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
        banner_image = request.FILES.get("banner_image")

        if not all([title, description, start_date, end_date, start_time, location, event_type, category_id]):
            messages.error(request, "⚠️ All fields are required.")
            return redirect("create_event")

        category = Category.objects.filter(id=category_id).first()

        # ✅ Create and save the event
        event = Event.objects.create(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            location=location,
            event_type=event_type,
            category=category,
            banner_image=banner_image,
            organizer_name=request.user.username,
            organizer_email=request.user.email,
        )

        messages.success(request, f"✅ Event '{event.title}' created successfully!")
        return redirect("manage_tickets", event_id=event.id)

    return render(request, "create_event.html", {
        "categories": categories,
        "user_data": request.session.get('user_data', {})
    })


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

        # ✅ Ensure event_type is saved (fallback to "offline" if missing)
        event.event_type = request.POST.get("event_type") or event.event_type or "offline"

        # ✅ Assign category safely
        category_id = request.POST.get("category")
        if category_id:
            event.category = Category.objects.filter(id=category_id).first()

        # ✅ Handle file upload safely
        banner_image = request.FILES.get("banner_image")
        if banner_image:
            event.banner_image = banner_image

        event.save()
        messages.success(request, "✅ Event updated successfully!")
        return redirect("organizer_home")

    return render(request, "editevent.html", {
        "event": event,
        "categories": categories,
        "user_data": request.session.get("user_data", {}),
    })


@login_required(login_url="login")
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer_email=request.user.email)

    if request.method == "POST":
        event.delete()
        messages.success(request, "🗑️ Event deleted successfully!")
        return redirect("organizer_home")

    return render(request, "organizer/confirm_delete.html", {
        "event": event,
        "user_data": request.session.get('user_data', {})
    })

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

    return render(request, "manage_tickets.html", {
        "event": event,
        "tickets": tickets,
        "user_data": request.session.get('user_data', {})
    })

@login_required(login_url="login")
def view_bookings(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer_email=request.user.email)
    bookings = Booking.objects.filter(event=event).select_related("user", "ticket")

    return render(request, "organizer/view_bookings.html", {
        "event": event,
        "bookings": bookings,
        "user_data": request.session.get('user_data', {})
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
        "user_data": request.session.get('user_data', {})
    })

@login_required(login_url="login")
def register_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if Booking.objects.filter(event=event, user=request.user).exists():
        messages.info(request, "⚠️ You are already registered for this event.")
        return redirect("event_detail", event_id=event_id)

    return redirect("book_tickets", event_id=event_id)

# ------------------- Helper -------------------
def get_organizer_event(user, event_id):
    return get_object_or_404(Event, id=event_id, organizer_email=user.email)

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
        "user_data": request.session.get('user_data', {})
    })

def my_events(request):
    events = [
        {
            "id": 1,
            "title": "Music Fest 2025",
            "description": "An amazing night of live music.",
            "banner_image": "https://picsum.photos/600/300?1",
            "start_date": "2025-09-10",
            "location": "Mumbai",
            "is_published": True,
        },
        {
            "id": 2,
            "title": "Startup Expo",
            "description": "Showcasing India’s top startups.",
            "banner_image": "https://picsum.photos/600/300?2",
            "start_date": "2025-10-05",
            "location": "Bangalore",
            "is_published": False,
        },
    ]
    return render(request, "organizer.html", {"events": events})
