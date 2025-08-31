from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("register/", views.register, name="register"),
    path('profile/', views.profile_view, name="profile"),
    path("profile_page/", views.profile_page, name="profile_page"), 
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify/<int:user_id>/", views.verify_otp, name="verify_otp"),
    path('' , views.home , name="home"),
    # Attendee
    path('make-payment/<int:event_id>/', views.make_payment, name="make_payment"),
    path('payment-success/<int:event_id>/', views.payment_success, name="payment_success"),


    path("ahome/", views.attendee_home, name="attendee_home"),
    path("event/<int:event_id>/register/", views.register_event, name="register_event"),
    
    path("event/<int:event_id>/", views.event_detail, name="event_detail"),
    path("tickets/<int:event_id>/", views.book_tickets, name="book_tickets"),
    # path("tickets/register/<int:event_id>/", views.register_tickets, name="register_tickets"),
    path('attendee-tickets/<int:event_id>/', views.attendee_tickets, name='attendee_tickets'),

    path("tickets/attendees/<int:event_id>/", views.attendee_details, name="attendee_details"),
    path("tickets/payment/<int:event_id>/", views.make_payment, name="make_payment"),

    # Organizer
    path("organizer/home/", views.organizer_home, name="organizer_home"),
    path("organizer/event/create/", views.create_event, name="create_event"),
    path("organizer/event/<int:event_id>/edit/", views.edit_event, name="edit_event"),
    path("organizer/event/<int:event_id>/delete/", views.delete_event, name="delete_event"),
    path("organizer/event/<int:event_id>/tickets/", views.manage_tickets, name="manage_tickets"),
    path("organizer/event/<int:event_id>/bookings/", views.view_bookings, name="view_bookings"),

    # ⭐ New Attendees List Page
    path("organizer/event/<int:event_id>/attendees/", views.attendees_list, name="attendees_list"),
]
