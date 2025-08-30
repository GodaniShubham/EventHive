from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify/<int:user_id>/', views.verify_otp, name='verify_otp'),
    path('details/', TemplateView.as_view(template_name='details.html'), name='details'),
    path('ahome/', views.attendee_home, name='ahome'),
    path("event/<int:event_id>/", views.event_detail, name="event_detail"), 
    path("tickets/<int:event_id>/", views.book_tickets, name="book_tickets"),
    path("tickets/register/<int:event_id>/", views.register_tickets, name="register_tickets"),
]
