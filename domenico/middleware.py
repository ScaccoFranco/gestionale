
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import UserProfile

class UserActivityMiddleware:
    """Middleware per tracciare l'attività utente"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Aggiorna attività utente se autenticato
        if request.user.is_authenticated:
            try:
                profile = request.user.userprofile
                profile.update_last_activity()
            except UserProfile.DoesNotExist:
                # Crea profilo se non esistente
                UserProfile.objects.create(user=request.user)
        
        response = self.get_response(request)
        return response

class LoginRequiredMiddleware:
    """Middleware per richiedere login su tutto il sito"""
    
    # URL che non richiedono autenticazione
    EXEMPT_URLS = [
        '/login/',
        '/admin/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Controlla se l'URL è esente
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return self.get_response(request)
        
        # Richiedi login se non autenticato
        if not request.user.is_authenticated:
            messages.warning(request, 'Devi effettuare il login per accedere.')
            return redirect(f"{reverse('login')}?next={request.path}")
        
        return self.get_response(request)