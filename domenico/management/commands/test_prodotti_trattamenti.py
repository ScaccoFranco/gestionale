from django.core.management.base import BaseCommand
from domenico.models import Cliente, Cascina, Terreno, Trattamento, Prodotto, TrattamentoProdotto
from decimal import Decimal
import json

class Command(BaseCommand):
    help = 'Testa il salvataggio dei prodotti nei trattamenti'

    def handle(self, *args, **options):
        self.stdout.write('=== TEST PRODOTTI NEI TRATTAMENTI ===\n')
        
        # Trova dati esistenti
        cliente = Cliente.objects.first()
        prodotto = Prodotto.objects.first()
        
        if not cliente:
            self.stdout.write(self.style.ERROR('❌ Nessun cliente trovato'))
            return
            
        if not prodotto:
            self.stdout.write(self.style.ERROR('❌ Nessun prodotto trovato'))
            return
        
        self.stdout.write(f'Cliente test: {cliente.nome}')
        self.stdout.write(f'Prodotto test: {prodotto.nome}')
        
        # Crea trattamento test
        trattamento = Trattamento.objects.create(
            cliente=cliente,
            livello_applicazione='cliente',
            stato='programmato',
            note='Test prodotti'
        )
        
        self.stdout.write(f'✅ Trattamento creato: ID {trattamento.id}')
        
        # Aggiungi prodotto
        trattamento_prodotto = TrattamentoProdotto.objects.create(
            trattamento=trattamento,
            prodotto=prodotto,
            quantita_per_ettaro=Decimal('2.5')
        )
        
        self.stdout.write(f'✅ Prodotto associato: {trattamento_prodotto}')
        
        # Verifica lettura
        prodotti_associati = trattamento.trattamentoprodotto_set.all()
        self.stdout.write(f'✅ Prodotti nel trattamento: {prodotti_associati.count()}')
        
        for tp in prodotti_associati:
            self.stdout.write(f'   - {tp.prodotto.nome}: {tp.quantita_per_ettaro}/ha')
            self.stdout.write(f'   - Quantità totale: {tp.quantita_totale}')
        
        # Pulizia
        trattamento.delete()
        self.stdout.write('✅ Test completato e pulito')
