from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('ticket/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<int:pk>/chat/', views.send_ticket_message, name='send_ticket_message'),
    path('ticket/new/', views.ticket_create, name='ticket_create'),
]
