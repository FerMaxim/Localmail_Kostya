from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('personnel/', views.personnel_management, name='personnel'),
    path('ticket/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<int:pk>/chat/', views.send_ticket_message, name='send_ticket_message'),
    path('ticket/new/', views.ticket_create, name='ticket_create'),
    path('export-report/', views.export_report_xlsx, name='export_report_xlsx'),
]
