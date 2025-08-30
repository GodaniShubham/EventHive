from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('EventHive_app.urls')),
    path('home/', TemplateView.as_view(template_name='home.html'), name='home'),
]