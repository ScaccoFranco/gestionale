from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse
import json

from domenico.models import Cliente, Cascina, Terreno, Prodotto, Contoterzista

class Command(BaseCommand):
    help = 'Testa tutte le funzionalità della pagina inserisci'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== TEST PAGINA INSERISCI ===\n'))
        
        # Verifica dati necessari
        self.check_required_data()
        
        # Testa le view principali
        self.test_inserisci_page()
        
        # Testa le API
        self.test_api_endpoints()
        
        # Testa la creazione di un trattamento
        self.test_create_trattamento()
        
        # Risultato finale
        self.final_summary()

    def check_required_data(self):
        """Verifica che ci siano dati sufficienti per testare"""
        self.stdout.write("📊 Verifica Dati Necessari:")
        
        clienti_count = Cliente.objects.count()
        cascine_count = Cascina.objects.count()
        terreni_count = Terreno.objects.count()
        prodotti_count = Prodotto.objects.count()
        contoterzisti_count = Contoterzista.objects.count()
        
        self.stdout.write(f"  • Clienti: {self.style.SUCCESS(clienti_count) if clienti_count > 0 else self.style.WARNING(clienti_count)}")
        self.stdout.write(f"  • Cascine: {self.style.SUCCESS(cascine_count) if cascine_count > 0 else self.style.WARNING(cascine_count)}")
        self.stdout.write(f"  • Terreni: {self.style.SUCCESS(terreni_count) if terreni_count > 0 else self.style.WARNING(terreni_count)}")
        self.stdout.write(f"  • Prodotti: {self.style.SUCCESS(prodotti_count) if prodotti_count > 0 else self.style.WARNING(prodotti_count)}")
        self.stdout.write(f"  • Contoterzisti: {self.style.SUCCESS(contoterzisti_count) if contoterzisti_count > 0 else self.style.WARNING(contoterzisti_count)}")
        
        if clienti_count == 0 or prodotti_count == 0:
            self.stdout.write(self.style.ERROR("\n❌ DATI INSUFFICIENTI!"))
            self.stdout.write("Esegui: python manage.py populate_data --reset")
            return False
        
        self.stdout.write(self.style.SUCCESS("  ✅ Dati sufficienti per il test"))
        return True

    def test_inserisci_page(self):
        """Testa che la pagina inserisci si carichi correttamente"""
        self.stdout.write("\n🌐 Test Pagina Inserisci:")
        
        client = Client()
        
        try:
            response = client.get('/inserisci/')
            
            if response.status_code == 200:
                self.stdout.write("  ✅ Pagina caricata correttamente")
                
                # Verifica che i dati siano nel context
                if 'clienti' in response.context:
                    clienti_count = len(response.context['clienti'])
                    self.stdout.write(f"  ✅ Clienti nel context: {clienti_count}")
                else:
                    self.stdout.write("  ⚠️  Clienti non trovati nel context")
                
                if 'prodotti' in response.context:
                    prodotti_count = len(response.context['prodotti'])
                    self.stdout.write(f"  ✅ Prodotti nel context: {prodotti_count}")
                else:
                    self.stdout.write("  ⚠️  Prodotti non trovati nel context")
                
                # Verifica che il template contenga gli elementi necessari
                content = response.content.decode()
                if 'step-indicator' in content:
                    self.stdout.write("  ✅ Step indicator presente")
                else:
                    self.stdout.write("  ⚠️  Step indicator mancante")
                
                if 'trattamentoForm' in content:
                    self.stdout.write("  ✅ Form trattamento presente")
                else:
                    self.stdout.write("  ⚠️  Form trattamento mancante")
                
            else:
                self.stdout.write(f"  ❌