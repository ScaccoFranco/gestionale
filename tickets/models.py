from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Ticket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Bassa'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]

    STATUS_CHOICES = [
        ('open', 'Aperto'),
        ('in_progress', 'In Lavorazione'),
        ('resolved', 'Risolto'),
        ('closed', 'Chiuso'),
    ]

    TYPE_CHOICES = [
        ('bug', 'Bug'),
        ('feature', 'Richiesta Funzionalità'),
        ('improvement', 'Miglioramento'),
        ('question', 'Domanda'),
        ('other', 'Altro'),
    ]

    title = models.CharField(max_length=200, verbose_name='Titolo')
    description = models.TextField(verbose_name='Descrizione')
    ticket_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='bug', verbose_name='Tipo')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name='Priorità')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name='Stato')

    # User info
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Utente')
    user_email = models.EmailField(max_length=254, null=True, blank=True, verbose_name='Email Utente')

    # Browser and page info for better debugging
    page_url = models.URLField(max_length=500, null=True, blank=True, verbose_name='URL Pagina')
    user_agent = models.TextField(null=True, blank=True, verbose_name='User Agent')
    browser_info = models.JSONField(null=True, blank=True, verbose_name='Info Browser')

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Creato il')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Aggiornato il')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Risolto il')

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.id} - {self.title}"

    def save(self, *args, **kwargs):
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status != 'resolved':
            self.resolved_at = None
        super().save(*args, **kwargs)


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments', verbose_name='Ticket')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Autore')
    comment = models.TextField(verbose_name='Commento')
    is_internal = models.BooleanField(default=False, verbose_name='Commento Interno')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Creato il')

    class Meta:
        verbose_name = 'Commento Ticket'
        verbose_name_plural = 'Commenti Tickets'
        ordering = ['created_at']

    def __str__(self):
        return f"Commento su #{self.ticket.id} da {self.author.email}"
