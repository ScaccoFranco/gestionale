from django.contrib import admin
from .models import Ticket, TicketComment

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'ticket_type', 'priority', 'status', 'user', 'created_at']
    list_filter = ['ticket_type', 'priority', 'status', 'created_at']
    search_fields = ['title', 'description', 'user__email', 'user_email']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Informazioni Principali', {
            'fields': ('title', 'description', 'ticket_type', 'priority', 'status')
        }),
        ('Utente', {
            'fields': ('user', 'user_email')
        }),
        ('Informazioni Tecniche', {
            'fields': ('page_url', 'user_agent', 'browser_info'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['ticket__title', 'author__email', 'comment']
    readonly_fields = ['created_at']
