from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import render
from .models import Ticket, TicketComment
from .serializers import TicketSerializer, TicketCreateSerializer, TicketCommentSerializer
import requests

User = get_user_model()

class TicketCreateView(generics.CreateAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            ticket = serializer.save()

            response_serializer = TicketSerializer(ticket)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': 'Si è verificato un errore durante la creazione del ticket.', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TicketListView(generics.ListAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ticket.objects.all()
        else:
            return Ticket.objects.filter(user=user)

class TicketDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ticket.objects.all()
        else:
            return Ticket.objects.filter(user=user)

@api_view(['POST'])
@permission_classes([AllowAny])
def submit_feedback(request):
    try:
        data = request.data.copy()

        if not data.get('title'):
            data['title'] = 'Feedback dell\'utente'

        if not data.get('ticket_type'):
            data['ticket_type'] = 'other'

        if not data.get('priority'):
            data['priority'] = 'medium'

        serializer = TicketCreateSerializer(data=data, context={'request': request})

        if serializer.is_valid():
            ticket = serializer.save()
            response_serializer = TicketSerializer(ticket)

            try:
                from decouple import config
                BOT_TOKEN = config('BOT_TOKEN', default='')
                CHAT_ID = config('CHAT_ID', default='')
            except ImportError:
                import os

                BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
                CHAT_ID = os.environ.get('CHAT_ID', '')
                

            output = f"Ticket {data.get('priority')}: {data.get('ticket_type')}\n\n{data.get('description')}"

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": CHAT_ID,
                "text": output,
                "parse_mode": "HTML"
            }

            response = requests.post(url, data=payload)

            return Response({
                'success': True,
                'message': 'Feedback inviato con successo! Grazie per il tuo contributo.',
                'ticket': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'message': 'Errore nella validazione dei dati.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({
            'success': False,
            'message': 'Si è verificato un errore interno. Riprova più tardi.',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def demo_view(request):
    return render(request, 'tickets/demo.html')
