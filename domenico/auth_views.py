
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
import json
from .models import UserProfile, UserSession, ActivityLog
from .activity_logging import log_activity

def custom_login(request):
    """Vista personalizzata per il login"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                
                # Configura sessione
                if not remember_me:
                    request.session.set_expiry(0)  # Chiudi al browser
                
                # Crea record sessione
                UserSession.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Aggiorna profilo utente
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.update_last_activity()
                
                # Log attività
                log_activity(
                    'user_login',
                    f'Accesso utente: {user.username}',
                    f'Utente {user.username} ha effettuato l\'accesso',
                    request=request
                )
                
                messages.success(request, f'Benvenuto, {user.first_name or user.username}!')
                
                # Redirect alla pagina richiesta o home
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Account disattivato. Contatta l\'amministratore.')
        else:
            messages.error(request, 'Username o password non corretti.')
    
    return render(request, 'auth/login.html')

def custom_logout(request):
    """Vista personalizzata per il logout"""
    if request.user.is_authenticated:
        # Chiudi sessione attiva
        try:
            session = UserSession.objects.filter(
                user=request.user,
                is_active=True
            ).latest('login_time')
            session.logout_time = timezone.now()
            session.is_active = False
            session.save()
        except UserSession.DoesNotExist:
            pass
        
        # Log attività
        log_activity(
            'user_login',
            f'Logout utente: {request.user.username}',
            f'Utente {request.user.username} ha effettuato il logout',
            request=request
        )
        
        logout(request)
        messages.info(request, 'Logout effettuato con successo.')
    
    return redirect('login')

# Decorator per controllare se l'utente è admin
def admin_required(view_func):
    """Decorator per richiedere privilegi admin"""
    def check_admin(user):
        if not user.is_authenticated:
            return False
        try:
            profile = user.userprofile
            return profile.role == 'admin' or user.is_superuser
        except UserProfile.DoesNotExist:
            return user.is_superuser
    
    return user_passes_test(check_admin, login_url='login')(view_func)

@admin_required
def admin_dashboard(request):
    """Dashboard amministratore"""
    # Statistiche utenti
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    admin_users = UserProfile.objects.filter(role='admin').count()
    
    # Sessioni attive
    active_sessions = UserSession.objects.filter(is_active=True).count()
    
    # Attività recenti
    recent_activities = ActivityLog.objects.select_related().order_by('-timestamp')[:10]
    
    # Utenti per ruolo
    users_by_role = UserProfile.objects.values('role').annotate(count=Count('role'))
    
    context = {
        'stats': {
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'active_sessions': active_sessions,
        },
        'recent_activities': recent_activities,
        'users_by_role': users_by_role,
    }
    
    return render(request, 'auth/admin_dashboard.html', context)

@admin_required
def user_management(request):
    """Vista per gestione utenti"""
    # Filtri
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # Query base
    users = User.objects.select_related('userprofile').order_by('username')
    
    # Applica filtri
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    if role_filter:
        users = users.filter(userprofile__role=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Paginazione
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'role_choices': UserProfile.ROLE_CHOICES,
    }
    
    return render(request, 'auth/user_management.html', context)

@admin_required
@require_http_methods(["POST"])
@csrf_exempt
def api_create_user(request):
    """API per creare nuovo utente"""
    try:
        data = json.loads(request.body)
        
        # Validazione dati
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', 'viewer')
        password = data.get('password', '')
        
        if not username or not email or not password:
            return JsonResponse({
                'success': False,
                'error': 'Username, email e password sono obbligatori'
            })
        
        # Controlla se username esiste
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'error': 'Username già esistente'
            })
        
        # Controlla se email esiste
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'Email già esistente'
            })
        
        # Crea utente
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        # Crea profilo
        profile = UserProfile.objects.create(
            user=user,
            role=role,
            phone=data.get('phone', ''),
            department=data.get('department', ''),
            can_manage_users=data.get('can_manage_users', False),
            can_export_data=data.get('can_export_data', False),
            can_manage_clients=data.get('can_manage_clients', True),
            can_manage_treatments=data.get('can_manage_treatments', True),
            can_view_reports=data.get('can_view_reports', True),
        )
        
        # Log attività
        log_activity(
            'cliente_created',  # Riusa tipo esistente
            f'Utente creato: {username}',
            f'Nuovo utente {username} creato con ruolo {role}',
            related_object=user,
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Utente {username} creato con successo',
            'user_id': user.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante la creazione: {str(e)}'
        })

@admin_required
@require_http_methods(["POST"])
@csrf_exempt
def api_update_user(request, user_id):
    """API per aggiornare utente"""
    try:
        user = get_object_or_404(User, id=user_id)
        profile = user.userprofile
        data = json.loads(request.body)
        
        # Aggiorna dati utente
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.is_active = data.get('is_active', user.is_active)
        user.save()
        
        # Aggiorna profilo
        profile.role = data.get('role', profile.role)
        profile.phone = data.get('phone', profile.phone)
        profile.department = data.get('department', profile.department)
        profile.can_manage_users = data.get('can_manage_users', profile.can_manage_users)
        profile.can_export_data = data.get('can_export_data', profile.can_export_data)
        profile.can_manage_clients = data.get('can_manage_clients', profile.can_manage_clients)
        profile.can_manage_treatments = data.get('can_manage_treatments', profile.can_manage_treatments)
        profile.can_view_reports = data.get('can_view_reports', profile.can_view_reports)
        profile.is_active_custom = data.get('is_active_custom', profile.is_active_custom)
        profile.save()
        
        # Aggiorna password se fornita
        new_password = data.get('password')
        if new_password:
            user.set_password(new_password)
            user.save()
        
        # Log attività
        log_activity(
            'trattamento_updated',  # Riusa tipo esistente
            f'Utente aggiornato: {user.username}',
            f'Profilo utente {user.username} modificato',
            related_object=user,
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Utente {user.username} aggiornato con successo'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante l\'aggiornamento: {str(e)}'
        })

@admin_required
@require_http_methods(["DELETE"])
@csrf_exempt
def api_delete_user(request, user_id):
    """API per eliminare utente"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Non permettere di eliminare se stesso
        if user == request.user:
            return JsonResponse({
                'success': False,
                'error': 'Non puoi eliminare il tuo stesso account'
            })
        
        # Non eliminare il superuser
        if user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'Non puoi eliminare un superuser'
            })
        
        username = user.username
        
        # Log attività prima dell'eliminazione
        log_activity(
            'backup_created',  # Riusa tipo esistente
            f'Utente eliminato: {username}',
            f'Utente {username} è stato eliminato dal sistema',
            request=request
        )
        
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Utente {username} eliminato con successo'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante l\'eliminazione: {str(e)}'
        })

def get_client_ip(request):
    """Helper per ottenere IP del client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip