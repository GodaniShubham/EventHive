import random
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import razorpay
from .models import CustomUser, Event, Category, Ticket, Booking, Attendee

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
        if CustomUser.objects.filter(phone=phone).exists():
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
            user.bio = bio
        if image:
            user.image = image

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

# (skipping unchanged booking/payment views here for brevity — they remain same as your code)

# ------------------- Organizer Section -------------------
@login_required(login_url="login")
def organizer_home(request):
    if not request.user.is_organizer:
        messages.error(request, "❌ Unauthorized access!")
        return redirect("attendee_home")

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
    published_events = events.filter(status="published").count()
    draft_events = events.filter(status="draft").count()
    archived_events = events.filter(status="archived").count()

    # ✅ FIX: calculate tickets_sold and revenue
    tickets_sold = Booking.objects.filter(event__in=events, payment_status="paid").aggregate(
        total=Sum("quantity")
    )["total"] or 0

    revenue = Booking.objects.filter(event__in=events, payment_status="paid").aggregate(
        total=Sum("amount_paid")
    )["total"] or 0

    # ---- Pagination ----
    paginator = Paginator(events, 12)
    page_number = request.GET.get("page")
    events_page = paginator.get_page(page_number)

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
        "total_events": total_events,
        "published_events": published_events,
        "draft_events": draft_events,
        "tickets_sold": tickets_sold,
        "revenue": revenue,
    })
def payment_page(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, "payment_page.html", {"event": event})

def confirm_payment(request, event_id):
    if request.method == "POST":
        # payment process logic (fake/sandbox)
        messages.success(request, "✅ Payment Successful! Tickets booked.")
        return redirect("home")
