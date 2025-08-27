from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from apps.permissions.models import Role

class Command(BaseCommand):
    help = 'Create default roles and permissions'
    
    def handle(self, *args, **options):
        # Create default roles
        roles_data = [
            {
                'name': 'Super Administrator',
                'description': 'Full system access',
                'role_type': 'admin'
            },
            {
                'name': 'Manager',
                'description': 'Manage users and content',
                'role_type': 'manager'
            },
            {
                'name': 'Standard User',
                'description': 'Basic user access',
                'role_type': 'user'
            },
            {
                'name': 'Guest',
                'description': 'Read-only access',
                'role_type': 'guest'
            }
        ]
        
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created role: {role.name}')
                )
            else:
                self.stdout.write(f'Role already exists: {role.name}')
        
        # Assign permissions to roles
        admin_role = Role.objects.get(name='Super Administrator')
        admin_role.permissions.set(Permission.objects.all())
        
        self.stdout.write(
            self.style.SUCCESS('Default roles created successfully!')
        )
