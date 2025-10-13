from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a new user account'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email address')
        parser.add_argument('--password', type=str, help='User password', default='Password123')
        parser.add_argument('--first-name', type=str, help='First name', default='')
        parser.add_argument('--last-name', type=str, help='Last name', default='')
        parser.add_argument('--staff', action='store_true', help='Make user staff member')
        parser.add_argument('--superuser', action='store_true', help='Make user superuser')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        is_staff = options['staff']
        is_superuser = options['superuser']

        try:
            if is_superuser:
                user = User.objects.create_superuser(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created superuser: {user.email}')
                )
            else:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=is_staff
                )
                user_type = 'staff user' if is_staff else 'user'
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created {user_type}: {user.email}')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user: {str(e)}')
            )