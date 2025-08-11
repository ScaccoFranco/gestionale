from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

class Cliente(models.Model):
    nome = models.CharField(max_length=200)
    creato_il = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nome
    
    def get_superficie_totale(self):
        """Calcola la superficie totale di tutti i terreni del cliente"""
        from decimal import Decimal
        try:
            superficie = sum(cascina.get_superficie_totale() for cascina in self.cascine.all())
            return Decimal(str(superficie))
        except Exception:
            return Decimal('0')


class ContattoEmail(models.Model):
    """Contatti email per le comunicazioni dei trattamenti"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='contatti_email')
    nome = models.CharField(max_length=200, help_text="Nome del contatto")
    email = models.EmailField(help_text="Indirizzo email del contatto")
    
    def __str__(self):
        return f"{self.nome} ({self.email}) - {self.cliente.nome}"
    
    class Meta:
        verbose_name = "Contatto Email"
        verbose_name_plural = "Contatti Email"

class Contoterzista(models.Model):
    nome = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = "Contoterzista"
        verbose_name_plural = "Contoterzisti"

class Cascina(models.Model):
    nome = models.CharField(max_length=200)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='cascine')
    contoterzista = models.ForeignKey(
        Contoterzista, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='cascine',
        help_text="Contoterzista responsabile per questa cascina (opzionale)"
    )
    
    def __str__(self):
        return f"{self.nome} - {self.cliente.nome}"
    
    def get_superficie_totale(self):
        """Calcola la superficie totale di tutti i terreni della cascina"""
        from decimal import Decimal
        try:
            superficie = sum(terreno.superficie for terreno in self.terreni.all())
            return Decimal(str(superficie))
        except Exception:
            return Decimal('0')
        
class Terreno(models.Model):
    nome = models.CharField(max_length=200)
    cascina = models.ForeignKey(Cascina, on_delete=models.CASCADE, related_name='terreni')
    superficie = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Superficie in ettari"
    )
    
    def __str__(self):
        return f"{self.nome} - {self.cascina.nome} ({self.superficie} ha)"
    
    def get_trattamenti_attivi(self):
        """Restituisce i trattamenti in corso per questo terreno"""
        return self.trattamenti.filter(stato__in=['programmato', 'comunicato'])
    
    class Meta:
        verbose_name = "Terreno"
        verbose_name_plural = "Terreni"

class PrincipioAttivo(models.Model):
    nome = models.CharField(max_length=200, unique=True)
    descrizione = models.TextField(blank=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = "Principio Attivo"
        verbose_name_plural = "Principi Attivi"

class Prodotto(models.Model):
    nome = models.CharField(max_length=200)
    principi_attivi = models.ManyToManyField(PrincipioAttivo, related_name='prodotti')
    descrizione = models.TextField(blank=True)
    unita_misura = models.CharField(
        max_length=20, 
        default='L',
        help_text="Es: L, Kg, g, ml"
    )
    
    def __str__(self):
        return self.nome
    
    def get_principi_attivi_list(self):
        """Restituisce una lista dei nomi dei principi attivi"""
        return [pa.nome for pa in self.principi_attivi.all()]
    
    class Meta:
        verbose_name = "Prodotto"
        verbose_name_plural = "Prodotti"

class Trattamento(models.Model):

    STATI_CHOICES = [
        ('programmato', 'Programmato'),
        ('comunicato', 'Comunicato'), 
        ('completato', 'Completato'),
        ('annullato', 'Annullato'),
    ]
    
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='trattamenti')
    cascina = models.ForeignKey(Cascina, on_delete=models.CASCADE, null=True, blank=True, related_name='trattamenti')
    terreni = models.ManyToManyField(Terreno, blank=True, related_name='trattamenti')
    
    # Livello di applicazione
    LIVELLI_APPLICAZIONE = [
        ('cliente', 'Intera Azienda'),
        ('cascina', 'Cascina'),
        ('terreno', 'Terreni Selezionati'),
    ]
    
    livello_applicazione = models.CharField(
        max_length=20,
        choices=LIVELLI_APPLICAZIONE,
        default='cliente',
        help_text="Specifica il livello di applicazione del trattamento"
    )
    
    # Date
    data_inserimento = models.DateTimeField(auto_now_add=True)
    data_comunicazione = models.DateTimeField(null=True, blank=True)
    data_esecuzione = models.DateField(null=True, blank=True)
    
    # Stato
    stato = models.CharField(
        max_length=20,
        choices=STATI_CHOICES,
        default='programmato',
        help_text="Stato attuale del trattamento"
    )
    
    note = models.TextField(blank=True, help_text="Note aggiuntive per il trattamento")
    
    class Meta:
        ordering = ['-data_inserimento']
        verbose_name = 'Trattamento'
        verbose_name_plural = 'Trattamenti'
    
    def __str__(self):
        return f"Trattamento #{self.id} - {self.cliente.nome} ({self.get_stato_display()})"
    
    def get_superficie_interessata(self):
        """Calcola la superficie totale interessata dal trattamento"""
        from decimal import Decimal
        
        try:
            if self.livello_applicazione == 'cliente':
                superficie = self.cliente.get_superficie_totale()
            elif self.livello_applicazione == 'cascina' and self.cascina:
                superficie = self.cascina.get_superficie_totale()
            elif self.livello_applicazione == 'terreno':
                superficie = sum(terreno.superficie for terreno in self.terreni.all())
            else:
                superficie = 0
            
            return Decimal(str(superficie)) if superficie else Decimal('0')
            
        except Exception as e:
            print(f"Errore calcolo superficie trattamento {self.id}: {e}")
            return Decimal('0')
    
    def get_contoterzista(self):
        """Restituisce il contoterzista associato al trattamento"""
        if self.cascina and self.cascina.contoterzista:
            return self.cascina.contoterzista
        return None
    

class TrattamentoProdotto(models.Model):
    """Tabella intermedia per gestire quantità dei prodotti nei trattamenti"""
    trattamento = models.ForeignKey(Trattamento, on_delete=models.CASCADE)
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE)
    quantita_per_ettaro = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Quantità per ettaro"
    )
    
    def __str__(self):
        quantita = self.get_quantita_per_ettaro()
        return f"{self.prodotto.nome} - {quantita} {self.prodotto.unita_misura}/ha"
    

    def get_quantita_per_ettaro(self):
        """
        Metodo helper per ottenere la quantità per ettaro
        indipendentemente dal nome del campo nel database
        """
        # Prova prima 'quantita_per_ettaro', poi 'quantita' come fallback
        if hasattr(self, 'quantita_per_ettaro'):
            return self.quantita_per_ettaro
        elif hasattr(self, 'quantita'):
            return self.quantita
        
    @property
    def quantita_totale(self):
        """Calcola la quantità totale moltiplicando per la superficie interessata"""
        try:
            superficie = self.trattamento.get_superficie_interessata()
            quantita_per_ettaro = self.get_quantita_per_ettaro()
            
            from decimal import Decimal
            if superficie is None or superficie == 0:
                return quantita_per_ettaro
            
            superficie_decimal = Decimal(str(superficie))
            quantita_decimal = Decimal(str(quantita_per_ettaro))
            return quantita_decimal * superficie_decimal
            
        except (ValueError, TypeError, AttributeError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Errore calcolo quantita_totale per {self}: {e}")
            return self.get_quantita_per_ettaro()
    
    class Meta:
        unique_together = ['trattamento', 'prodotto']
        verbose_name = "Prodotto del Trattamento"
        verbose_name_plural = "Prodotti del Trattamento"

     
class ComunicazioneTrattamento(models.Model):
    """Traccia le comunicazioni inviate per ogni trattamento"""
    trattamento = models.ForeignKey(Trattamento, on_delete=models.CASCADE, related_name='comunicazioni')
    data_invio = models.DateTimeField(auto_now_add=True)
    destinatari = models.TextField(help_text="Lista email destinatari (separati da virgola)")
    oggetto = models.CharField(max_length=500)
    corpo_email = models.TextField()
    allegati = models.TextField(blank=True, help_text="Lista percorsi allegati (separati da virgola)")
    inviato_con_successo = models.BooleanField(default=False)
    errore = models.TextField(blank=True)
    
    def __str__(self):
        return f"Comunicazione {self.trattamento.id} - {self.data_invio.strftime('%d/%m/%Y %H:%M')}"
    
    class Meta:
        verbose_name = "Comunicazione Trattamento"
        verbose_name_plural = "Comunicazioni Trattamenti"
        ordering = ['-data_invio']



class ActivityLog(models.Model):
    """Log delle attività dell'utente nel sistema"""
    
    ACTIVITY_TYPES = [
        ('cliente_created', 'Cliente Creato'),
        ('cascina_created', 'Cascina Creata'),
        ('terreno_created', 'Terreno Creato'),
        ('prodotto_created', 'Prodotto Creato'),
        ('contoterzista_created', 'Contoterzista Creato'),
        ('contatto_created', 'Contatto Email Creato'),
        ('trattamento_created', 'Trattamento Creato'),
        ('trattamento_updated', 'Trattamento Aggiornato'),
        ('comunicazione_sent', 'Comunicazione Inviata'),
        ('user_login', 'Accesso Utente'),
        ('data_export', 'Esportazione Dati'),
        ('backup_created', 'Backup Creato'),
    ]
    
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES,
        help_text="Tipo di attività eseguita"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Titolo breve dell'attività"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Descrizione dettagliata dell'attività"
    )
    
    # Riferimenti agli oggetti coinvolti
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Tipo di oggetto coinvolto (Cliente, Terreno, etc.)"
    )
    
    related_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID dell'oggetto coinvolto"
    )
    
    related_object_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nome dell'oggetto coinvolto"
    )
    
    # Metadati
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Dati aggiuntivi in formato JSON
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dati aggiuntivi dell'attività in formato JSON"
    )
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.title}"
    
    def get_icon(self):
        """Restituisce l'icona FontAwesome per il tipo di attività"""
        icon_map = {
            'cliente_created': 'fas fa-building',
            'cascina_created': 'fas fa-home',
            'terreno_created': 'fas fa-seedling',
            'prodotto_created': 'fas fa-flask',
            'contoterzista_created': 'fas fa-user-tie',
            'contatto_created': 'fas fa-address-book',
            'trattamento_created': 'fas fa-spray-can',
            'trattamento_updated': 'fas fa-edit',
            'comunicazione_sent': 'fas fa-paper-plane',
            'user_login': 'fas fa-sign-in-alt',
            'data_export': 'fas fa-download',
            'backup_created': 'fas fa-save',
        }
        return icon_map.get(self.activity_type, 'fas fa-circle')
    
    def get_color_class(self):
        """Restituisce la classe CSS per il colore dell'attività"""
        color_map = {
            'cliente_created': 'text-primary',
            'cascina_created': 'text-info',
            'terreno_created': 'text-success',
            'prodotto_created': 'text-warning',
            'contoterzista_created': 'text-secondary',
            'contatto_created': 'text-info',
            'trattamento_created': 'text-primary',
            'trattamento_updated': 'text-warning',
            'comunicazione_sent': 'text-success',
            'user_login': 'text-muted',
            'data_export': 'text-info',
            'backup_created': 'text-success',
        }
        return color_map.get(self.activity_type, 'text-muted')
    
    def time_since(self):
        """Restituisce il tempo trascorso dall'attività"""
        from django.utils.timesince import timesince
        return timesince(self.timestamp)
    
    class Meta:
        verbose_name = "Log Attività"
        verbose_name_plural = "Log Attività"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['related_object_type', 'related_object_id']),
        ]

# ============ FUNZIONI HELPER PER LOGGING ============

def log_activity(activity_type, title, description='', related_object=None, 
                 request=None, extra_data=None):
    """
    Funzione helper per registrare un'attività
    
    Args:
        activity_type (str): Tipo di attività (deve essere in ACTIVITY_TYPES)
        title (str): Titolo dell'attività
        description (str): Descrizione opzionale
        related_object: Oggetto Django correlato (Cliente, Terreno, etc.)
        request: Oggetto request Django per IP e user agent
        extra_data (dict): Dati aggiuntivi da salvare
    """
    try:
        # Prepara dati dell'oggetto correlato
        related_object_type = None
        related_object_id = None
        related_object_name = None
        
        if related_object:
            related_object_type = related_object.__class__.__name__
            related_object_id = related_object.pk
            related_object_name = str(related_object)
        
        # Prepara dati dalla request
        ip_address = None
        user_agent = ''
        
        if request:
            # Ottieni IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            # Ottieni user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Crea il log
        ActivityLog.objects.create(
            activity_type=activity_type,
            title=title,
            description=description,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            related_object_name=related_object_name,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data or {}
        )
        
        print(f"✅ Attività registrata: {title}")
        
    except Exception as e:
        print(f"❌ Errore nel logging attività: {str(e)}")

# ============ FUNZIONI SPECIFICHE PER OGNI AZIONE ============

def log_cliente_created(cliente, request=None):
    """Log per creazione cliente"""
    log_activity(
        activity_type='cliente_created',
        title=f'Nuovo cliente: {cliente.nome}',
        description=f'È stato aggiunto il cliente {cliente.nome} al database',
        related_object=cliente,
        request=request,
        extra_data={
            'cliente_id': cliente.id,
            'cliente_nome': cliente.nome,
            'data_creazione': cliente.creato_il.isoformat() if hasattr(cliente, 'creato_il') else None
        }
    )

def log_terreno_created(terreno, request=None):
    """Log per creazione terreno"""
    log_activity(
        activity_type='terreno_created',
        title=f'Nuovo terreno: {terreno.nome}',
        description=f'È stato aggiunto il terreno {terreno.nome} ({terreno.superficie} ha) alla cascina {terreno.cascina.nome}',
        related_object=terreno,
        request=request,
        extra_data={
            'terreno_id': terreno.id,
            'terreno_nome': terreno.nome,
            'superficie': float(terreno.superficie),
            'cascina_id': terreno.cascina.id,
            'cascina_nome': terreno.cascina.nome,
            'cliente_nome': terreno.cascina.cliente.nome
        }
    )

def log_prodotto_created(prodotto, principi_attivi=None, request=None):
    """Log per creazione prodotto"""
    principi_list = []
    if principi_attivi:
        principi_list = [pa.nome for pa in principi_attivi]
    
    log_activity(
        activity_type='prodotto_created',
        title=f'Nuovo prodotto: {prodotto.nome}',
        description=f'È stato aggiunto il prodotto {prodotto.nome} ({prodotto.unita_misura}) con principi attivi: {", ".join(principi_list)}',
        related_object=prodotto,
        request=request,
        extra_data={
            'prodotto_id': prodotto.id,
            'prodotto_nome': prodotto.nome,
            'unita_misura': prodotto.unita_misura,
            'principi_attivi': principi_list,
            'descrizione': prodotto.descrizione
        }
    )

def log_contoterzista_created(contoterzista, request=None):
    """Log per creazione contoterzista"""
    log_activity(
        activity_type='contoterzista_created',
        title=f'Nuovo contoterzista: {contoterzista.nome}',
        description=f'È stato aggiunto il contoterzista {contoterzista.nome}',
        related_object=contoterzista,
        request=request,
        extra_data={
            'contoterzista_id': contoterzista.id,
            'contoterzista_nome': contoterzista.nome,
            'email': contoterzista.email
        }
    )

def log_contatto_created(contatto, request=None):
    """Log per creazione contatto email"""
    log_activity(
        activity_type='contatto_created',
        title=f'Nuovo contatto: {contatto.nome}',
        description=f'È stato aggiunto il contatto email {contatto.nome} ({contatto.email}) per {contatto.cliente.nome}',
        related_object=contatto,
        request=request,
        extra_data={
            'contatto_id': contatto.id,
            'contatto_nome': contatto.nome,
            'contatto_email': contatto.email,
            'cliente_id': contatto.cliente.id,
            'cliente_nome': contatto.cliente.nome
        }
    )

def log_trattamento_created(trattamento, request=None):
    """Log per creazione trattamento"""
    superficie = trattamento.get_superficie_interessata()
    
    log_activity(
        activity_type='trattamento_created',
        title=f'Nuovo trattamento per {trattamento.cliente.nome}',
        description=f'È stato programmato un trattamento per {trattamento.cliente.nome} su {superficie} ettari',
        related_object=trattamento,
        request=request,
        extra_data={
            'trattamento_id': trattamento.id,
            'cliente_nome': trattamento.cliente.nome,
            'superficie_interessata': float(superficie),
            'livello_applicazione': trattamento.livello_applicazione,
            'stato': trattamento.stato,
        }
    )

def log_comunicazione_sent(trattamento, destinatari_count, request=None):
    """Log per invio comunicazione"""
    log_activity(
        activity_type='comunicazione_sent',
        title=f'Comunicazione inviata per trattamento #{trattamento.id}',
        description=f'È stata inviata la comunicazione per il trattamento di {trattamento.cliente.nome} a {destinatari_count} destinatari',
        related_object=trattamento,
        request=request,
        extra_data={
            'trattamento_id': trattamento.id,
            'cliente_nome': trattamento.cliente.nome,
            'destinatari_count': destinatari_count,
            'data_comunicazione': timezone.now().isoformat()
        }
    )