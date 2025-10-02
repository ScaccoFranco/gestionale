#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestionale.settings')
django.setup()

from tickets.models import Ticket

print(f'Total tickets created: {Ticket.objects.count()}')
print('\nTickets list:')
for ticket in Ticket.objects.all():
    print(f'  - #{ticket.id}: {ticket.title} ({ticket.ticket_type}/{ticket.priority}) - {ticket.status}')
    print(f'    Created: {ticket.created_at.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'    Description: {ticket.description[:100]}...')
    print()