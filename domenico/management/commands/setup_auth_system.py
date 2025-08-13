from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from domenico.models import UserProfile

class Command(BaseCommand):
    help = 'Inizializza il sistema di autenticazione'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== SETUP SISTEMA AUTENTICAZIONE ==='))
        
        # Crea profili per utenti esistenti
        users_without_profile = User.objects.filter(userprofile__isnull=True)
        
        for user in users_without_profile:
            # Determina ruolo basato su is_superuser
            role = 'admin' if user.is_superuser else 'viewer'
            
            UserProfile.objects.create(
                user=user,
                role=role,
                can_manage_users=user.is_superuser,
                can_export_data=user.is_superuser,
                can_manage_clients=True,
                can_manage_treatments=True,
                can_view_reports=True,
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Profilo creato per {user.username} con ruolo {role}')
            )
        
        # Crea utenti di test se non esistono
        test_users = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'Sistema',
                'role': 'admin',
                'permissions': {
                    'can_manage_users': True,
                    'can_export_data': True,
                    'can_manage_clients': True,
                    'can_manage_treatments': True,
                    'can_view_reports': True,
                }
            },
            {
                'username': 'editor',
                'email': 'editor@example.com',
                'first_name': 'Editor',
                'last_name': 'Utente',
                'role': 'editor',
                'permissions': {
                    'can_manage_users': False,
                    'can_export_data': False,
                    'can_manage_clients': True,
                    'can_manage_treatments': True,
                    'can_view_reports': True,
                }
            },
            {
                'username': 'viewer',
                'email': 'viewer@example.com',
                'first_name': 'Viewer',
                'last_name': 'Utente',
                'role': 'viewer',
                'permissions': {
                    'can_manage_users': False,
                    'can_export_data': False,
                    'can_manage_clients': False,
                    'can_manage_treatments': False,
                    'can_view_reports': True,
                }
            }
        ]
        
        for user_data in test_users:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    password='password'
                )
                
                UserProfile.objects.create(
                    user=user,
                    role=user_data['role'],
                    **user_data['permissions']
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Utente di test {user_data["username"]} creato')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Utente {user_data["username"]} già esistente')
                )
        
        self.stdout.write(self.style.SUCCESS('\n✅ Setup completato con successo!'))
        self.stdout.write('📝 Credenziali di test:')
        self.stdout.write('   admin/password - Amministratore completo')
        self.stdout.write('   editor/password - Editor con permessi limitati')
        self.stdout.write('   viewer/password - Solo visualizzazione')