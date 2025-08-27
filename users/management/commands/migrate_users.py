from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User as DjangoUser
from django.db import transaction
from domenico.models import UserProfile as OldUserProfile
from users.models import UserProfile

class Command(BaseCommand):
    help = 'Migrate existing users to new authentication system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes'
        )

    def handle(self, *args, **options):
        CustomUser = get_user_model()
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
        
        # Get all existing Django users
        django_users = DjangoUser.objects.all()
        
        if not django_users.exists():
            self.stdout.write("No existing users found to migrate.")
            return
        
        migrated_count = 0
        
        with transaction.atomic():
            for old_user in django_users:
                # Check if user already migrated
                if CustomUser.objects.filter(email=old_user.email).exists():
                    self.stdout.write(f"User {old_user.username} already exists in new system")
                    continue
                
                if dry_run:
                    self.stdout.write(f"Would migrate user: {old_user.username} ({old_user.email})")
                    migrated_count += 1
                    continue
                
                # Create new custom user
                new_user = CustomUser.objects.create_user(
                    email=old_user.email or f"{old_user.username}@example.com",
                    first_name=old_user.first_name,
                    last_name=old_user.last_name,
                    password=old_user.password,  # Copy hashed password
                    is_staff=old_user.is_staff,
                    is_superuser=old_user.is_superuser,
                    is_active=old_user.is_active,
                    date_joined=old_user.date_joined,
                    last_login=old_user.last_login,
                    username=old_user.email or old_user.username,
                )
                
                # Copy old UserProfile if exists
                try:
                    old_profile = old_user.userprofile
                    new_profile = UserProfile.objects.create(
                        user=new_user,
                        bio=f"Migrated from old system - {old_profile.role}",
                        phone=getattr(old_profile, 'phone', ''),
                        company=getattr(old_profile, 'department', ''),
                    )
                    
                    # Map old permissions to new user model
                    if hasattr(old_profile, 'can_manage_users') and old_profile.can_manage_users:
                        new_user.is_staff = True
                        
                except OldUserProfile.DoesNotExist:
                    # Create basic profile
                    UserProfile.objects.create(
                        user=new_user,
                        bio="Migrated from old system"
                    )
                
                new_user.save()
                migrated_count += 1
                
                self.stdout.write(f"Migrated user: {old_user.username} -> {new_user.email}")
        
        if dry_run:
            self.stdout.write(f"Would migrate {migrated_count} users")
        else:
            self.stdout.write(f"Successfully migrated {migrated_count} users")