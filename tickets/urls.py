from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('demo/', views.demo_view, name='demo'),
    path('api/feedback/', views.submit_feedback, name='submit_feedback'),
    path('api/tickets/', views.TicketListView.as_view(), name='ticket_list'),
    path('api/tickets/create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('api/tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
]