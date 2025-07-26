from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Q
from domenico.models import Cliente, Cascina, Terreno, Trattamento, Contoterzista, Prodotto

class Command(BaseCommand):
    help = 'Debug e verifica dello stato del database per la pagina aziende'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='Crea dati di test se il database è vuoto',
        )
        parser.add_argument(
            '--fix-data',
            action='store_true',
            help='Corregge eventuali problemi nei dati',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== DEBUG DATABASE AZIENDE ===\n'))
        
        # Verifica stato del database
        self.check_database_status()
        
        # Se richiesto, crea dati di test
        if options['create_test_data']:
            self.create_test_data()
        
        # Se richiesto, corregge i dati
        if options['fix_data']:
            self.fix_data_issues()
        
        # Verifica finale
        self.test_aziende_view_data()

    def check_database_status(self):
        """Verifica lo stato del database"""
        self.stdout.write("📊 Stato del Database:")
        
        stats = {
            'Clienti': Cliente.objects.count(),
            'Cascine': Cascina.objects.count(),
            'Terreni': Terreno.objects.count(),
            'Contoterzisti': Contoterzista.objects.count(),
            'Prodotti': Prodotto.objects.count(),
            'Trattamenti': Trattamento.objects.count(),
        }
        
        for entity, count in stats.items():
            color = self.style.SUCCESS if count > 0 else self.style.WARNING
            self.stdout.write(f"  • {entity}: {color(count)}")
        
        # Verifica relazioni
        self.stdout.write("\n🔗 Verifica Relazioni:")
        
        cascine_senza_cliente = Cascina.objects.filter(cliente__isnull=True).count()
        terreni_senza_cascina = Terreno.objects.filter(cascina__isnull=True).count()
        cascine_senza_contoterzista = Cascina.objects.filter(contoterzista__isnull=True).count()
        
        if cascine_senza_cliente > 0:
            self.stdout.write(f"  ⚠️  Cascine senza cliente: {self.style.WARNING(cascine_senza_cliente)}")
        
        if terreni_senza_cascina > 0:
            self.stdout.write(f"  ⚠️  Terreni senza cascina: {self.style.WARNING(terreni_senza_cascina)}")
        
        if cascine_senza_contoterzista > 0:
            self.stdout.write(f"  ⚠️  Cascine senza contoterzista: {self.style.WARNING(cascine_senza_contoterzista)}")
        
        if cascine_senza_cliente == 0 and terreni_senza_cascina == 0:
            self.stdout.write(f"  ✅ Tutte le relazioni sono corrette")

    def create_test_data(self):
        """Crea dati di test se necessario"""
        self.stdout.write("\n🔧 Creazione dati di test...")
        
        # Crea contoterzisti se non esistono
        if Contoterzista.objects.count() == 0:
            contoterzisti = [
                Contoterzista.objects.create(
                    nome="Marco Verdi",
                    telefono="333-1234567",
                    email="marco.verdi@email.com"
                ),
                Contoterzista.objects.create(
                    nome="Giuseppe Bianchi",
                    telefono="333-7654321",
                    email="giuseppe.bianchi@email.com"
                ),
                Contoterzista.objects.create(
                    nome="Andrea Rossi",
                    telefono="333-9876543",
                    email="andrea.rossi@email.com"
                )
            ]
            self.stdout.write(f"  ✅ Creati {len(contoterzisti)} contoterzisti")
        
        # Crea clienti se non esistono
        if Cliente.objects.count() == 0:
            clienti = [
                Cliente.objects.create(nome="Azienda Agricola Domenico Franco"),
                Cliente.objects.create(nome="Vigneti del Piemonte S.r.l."),
                Cliente.objects.create(nome="Cascina San Lorenzo"),
                Cliente.objects.create(nome="Azienda Vinicola Barbera"),
            ]
            self.stdout.write(f"  ✅ Creati {len(clienti)} clienti")
        
        # Crea cascine se non esistono
        if Cascina.objects.count() == 0:
            clienti = Cliente.objects.all()
            contoterzisti = Contoterzista.objects.all()
            
            cascine_data = [
                ("Vigna Alta", clienti[0], contoterzisti[0] if contoterzisti else None),
                ("Vigna Bassa", clienti[0], contoterzisti[0] if contoterzisti else None),
                ("Cascina Centrale", clienti[1], contoterzisti[1] if contoterzisti else None),
                ("Tenuta Sud", clienti[1], contoterzisti[1] if contoterzisti else None),
                ("San Lorenzo Alto", clienti[2], contoterzisti[2] if contoterzisti else None),
                ("Barbera Principale", clienti[3], contoterzisti[0] if contoterzisti else None),
            ]
            
            cascine = []
            for nome, cliente, contoterzista in cascine_data:
                cascina = Cascina.objects.create(
                    nome=nome,
                    cliente=cliente,
                    contoterzista=contoterzista
                )
                cascine.append(cascina)
            
            self.stdout.write(f"  ✅ Creati {len(cascine)} cascine")
        
        # Crea terreni se non esistono
        if Terreno.objects.count() == 0:
            cascine = Cascina.objects.all()
            
            terreni_data = [
                ("Vigna 1", cascine[0], 2.5),
                ("Vigna 2", cascine[0], 3.2),
                ("Vigna 3", cascine[1], 1.8),
                ("Vigna 4", cascine[1], 4.1),
                ("Campo Nord", cascine[2], 5.0),
                ("Campo Sud", cascine[2], 3.7),
                ("Tenuta Est", cascine[3], 6.2),
                ("Vigna Storica", cascine[4], 2.9),
                ("Barbera Classic", cascine[5], 4.8),
            ]
            
            terreni = []
            for nome, cascina, superficie in terreni_data:
                terreno = Terreno.objects.create(
                    nome=nome,
                    cascina=cascina,
                    superficie=superficie
                )
                terreni.append(terreno)
            
            self.stdout.write(f"  ✅ Creati {len(terreni)} terreni")
        
        # Crea prodotti se non esistono
        if Prodotto.objects.count() == 0:
            prodotti = [
                Prodotto.objects.create(
                    nome="Fungicida Sistemico A",
                    unita_misura="L"
                ),
                Prodotto.objects.create(
                    nome="Insetticida B",
                    unita_misura="L"
                ),
                Prodotto.objects.create(
                    nome="Erbicida Selettivo C",
                    unita_misura="L"
                ),
            ]
            self.stdout.write(f"  ✅ Creati {len(prodotti)} prodotti")

    def fix_data_issues(self):
        """Corregge problemi comuni nei dati"""
        self.stdout.write("\n🔧 Correzione problemi nei dati...")
        
        fixed_count = 0
        
        # Assegna contoterzisti mancanti
        cascine_senza_contoterzista = Cascina.objects.filter(contoterzista__isnull=True)
        if cascine_senza_contoterzista.exists():
            primo_contoterzista = Contoterzista.objects.first()
            if primo_contoterzista:
                cascine_senza_contoterzista.update(contoterzista=primo_contoterzista)
                fixed_count += cascine_senza_contoterzista.count()
                self.stdout.write(f"  ✅ Assegnato contoterzista a {cascine_senza_contoterzista.count()} cascine")
        
        if fixed_count > 0:
            self.stdout.write(f"  ✅ Corretti {fixed_count} problemi")
        else:
            self.stdout.write("  ✅ Nessun problema trovato")

    def test_aziende_view_data(self):
        """Testa la struttura dati per la view aziende"""
        self.stdout.write("\n🧪 Test struttura dati per view aziende...")
        
        try:
            # Simula la query della view aziende
            clienti = Cliente.objects.prefetch_related(
                'cascine__terreni',
                'cascine__contoterzista',
                'trattamenti'
            ).annotate(
                superficie_totale=Sum('cascine__terreni__superficie'),
                trattamenti_programmati=Count(
                    'trattamenti', 
                    filter=Q(trattamenti__stato='programmato')
                ),
                trattamenti_comunicati=Count(
                    'trattamenti', 
                    filter=Q(trattamenti__stato='comunicato')
                )
            ).order_by('nome')
            
            self.stdout.write(f"  ✅ Query clienti eseguita con successo: {clienti.count()} clienti")
            
            # Verifica la struttura dati
            aziende_tree = []
            for cliente in clienti:
                cliente_data = {
                    'id': cliente.id,
                    'nome': cliente.nome,
                    'superficie_totale': cliente.superficie_totale or 0,
                    'trattamenti_programmati': cliente.trattamenti_programmati,
                    'trattamenti_comunicati': cliente.trattamenti_comunicati,
                    'cascine': []
                }
                
                for cascina in cliente.cascine.all():
                    superficie_cascina = sum(terreno.superficie for terreno in cascina.terreni.all())
                    
                    cascina_data = {
                        'id': cascina.id,
                        'nome': cascina.nome,
                        'superficie_totale': superficie_cascina,
                        'contoterzista': cascina.contoterzista.nome if cascina.contoterzista else None,
                        'terreni': list(cascina.terreni.all())
                    }
                    
                    cliente_data['cascine'].append(cascina_data)
                
                aziende_tree.append(cliente_data)
            
            self.stdout.write(f"  ✅ Struttura aziende_tree creata con successo: {len(aziende_tree)} aziende")
            
            # Stampa un riassunto
            for azienda in aziende_tree:
                self.stdout.write(f"    • {azienda['nome']}: {len(azienda['cascine'])} cascine, {azienda['superficie_totale']:.1f} ha")
                for cascina in azienda['cascine']:
                    terreni_count = len(cascina['terreni'])
                    contoterzista = cascina['contoterzista'] or 'Non assegnato'
                    self.stdout.write(f"      - {cascina['nome']}: {terreni_count} terreni, {cascina['superficie_totale']:.1f} ha, {contoterzista}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Errore nel test: {str(e)}"))
            return False
        
        self.stdout.write(self.style.SUCCESS("\n✅ Tutti i test superati! La pagina aziende dovrebbe funzionare correttamente."))
        return True