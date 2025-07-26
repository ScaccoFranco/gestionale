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
        return sum(cascina.get_superficie_totale() for cascina in self.cascine.all())
    
    def get_trattamenti_attivi(self):
        """Restituisce i trattamenti in corso per questo cliente"""
        return Trattamento.objects.filter(
            cliente=self,
            stato__in=['programmato', 'comunicato']
        )
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clienti"

class Contoterzista(models.Model):
    nome = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
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
        help_text="Contoterzista responsabile per questa cascina"
    )
    
    def __str__(self):
        return f"{self.nome} - {self.cliente.nome}"
    
    def get_superficie_totale(self):
        """Calcola la superficie totale di tutti i terreni della cascina"""
        return sum(terreno.superficie for terreno in self.terreni.all())
    
    def get_trattamenti_attivi(self):
        """Restituisce i trattamenti in corso per questa cascina"""
        return Trattamento.objects.filter(
            cascina=self,
            stato__in=['programmato', 'comunicato']
        )
    
    class Meta:
        verbose_name = "Cascina"
        verbose_name_plural = "Cascine"

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
        ('in_esecuzione', 'In Esecuzione'),
        ('completato', 'Completato'),
        ('annullato', 'Annullato'),
    ]
    
    LIVELLO_CHOICES = [
        ('cliente', 'Cliente'),
        ('cascina', 'Cascina'),
        ('terreno', 'Terreno'),
    ]
    
    # Relazioni gerarchiche (nullable per flessibilità)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='trattamenti')
    cascina = models.ForeignKey(Cascina, on_delete=models.CASCADE, null=True, blank=True, related_name='trattamenti')
    terreni = models.ManyToManyField(Terreno, related_name='trattamenti', blank=True)
    
    # Informazioni del trattamento
    livello_applicazione = models.CharField(max_length=10, choices=LIVELLO_CHOICES)
    prodotti = models.ManyToManyField(Prodotto, through='TrattamentoProdotto')
    
    # Stati e date
    stato = models.CharField(max_length=20, choices=STATI_CHOICES, default='programmato')
    data_inserimento = models.DateTimeField(auto_now_add=True)
    data_comunicazione = models.DateTimeField(null=True, blank=True)
    data_esecuzione_prevista = models.DateField(null=True, blank=True)
    data_esecuzione_effettiva = models.DateTimeField(null=True, blank=True)
    
    # Note
    note = models.TextField(blank=True)
    
    def __str__(self):
        livello_desc = ""
        if self.livello_applicazione == 'cliente':
            livello_desc = self.cliente.nome
        elif self.livello_applicazione == 'cascina' and self.cascina:
            livello_desc = f"{self.cascina.nome}"
        elif self.livello_applicazione == 'terreno':
            terreni_nomi = ", ".join([t.nome for t in self.terreni.all()[:3]])
            if self.terreni.count() > 3:
                terreni_nomi += f" (+{self.terreni.count()-3} altri)"
            livello_desc = terreni_nomi
        
        return f"Trattamento {self.id} - {livello_desc} ({self.get_stato_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-imposta data comunicazione quando stato cambia in 'comunicato'
        if self.stato == 'comunicato' and not self.data_comunicazione:
            self.data_comunicazione = timezone.now()
        
        # Auto-imposta data esecuzione quando stato cambia in 'completato'
        if self.stato == 'completato' and not self.data_esecuzione_effettiva:
            self.data_esecuzione_effettiva = timezone.now()
            
        super().save(*args, **kwargs)
    
    def get_superficie_interessata(self):
        """Calcola la superficie totale interessata dal trattamento"""
        if self.livello_applicazione == 'cliente':
            return self.cliente.get_superficie_totale()
        elif self.livello_applicazione == 'cascina' and self.cascina:
            return self.cascina.get_superficie_totale()
        elif self.livello_applicazione == 'terreno':
            return sum(terreno.superficie for terreno in self.terreni.all())
        return 0
    
    def get_contoterzista(self):
        """Restituisce il contoterzista responsabile per questo trattamento"""
        if self.livello_applicazione == 'terreno' and self.terreni.exists():
            # Per i terreni, prendi il contoterzista della cascina del primo terreno
            return self.terreni.first().cascina.contoterzista
        elif self.livello_applicazione == 'cascina' and self.cascina:
            return self.cascina.contoterzista
        elif self.livello_applicazione == 'cliente':
            # Per il cliente, prendi il contoterzista della prima cascina
            prima_cascina = self.cliente.cascine.first()
            return prima_cascina.contoterzista if prima_cascina else None
        return None
    
    class Meta:
        verbose_name = "Trattamento"
        verbose_name_plural = "Trattamenti"
        ordering = ['-data_inserimento']

class TrattamentoProdotto(models.Model):
    """Tabella intermedia per gestire quantità dei prodotti nei trattamenti"""
    trattamento = models.ForeignKey(Trattamento, on_delete=models.CASCADE)
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE)
    quantita = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        validators=[MinValueValidator(0.001)]
    )
    
    def __str__(self):
        return f"{self.prodotto.nome} - {self.quantita} {self.prodotto.unita_misura}"
    
    class Meta:
        unique_together = ['trattamento', 'prodotto']
        verbose_name = "Prodotto del Trattamento"
        verbose_name_plural = "Prodotti del Trattamento"
