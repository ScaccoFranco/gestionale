from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from domenico.models import Cliente, Contoterzista, Cascina, Terreno, PrincipioAttivo, Prodotto

class Command(BaseCommand):
    help = 'Popola il database con i dati dal file Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Cancella tutti i dati esistenti prima di popolare',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(
                self.style.WARNING('⚠️  Cancellazione di tutti i dati esistenti...')
            )
            with transaction.atomic():
                Terreno.objects.all().delete()
                Cascina.objects.all().delete()
                Prodotto.objects.all().delete()
                PrincipioAttivo.objects.all().delete()
                Contoterzista.objects.all().delete()
                Cliente.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Dati cancellati'))

        try:
            with transaction.atomic():
                self.populate_all_data()
            self.stdout.write(
                self.style.SUCCESS('✅ Popolamento completato con successo!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Errore durante il popolamento: {e}')
            )
            raise

    def populate_all_data(self):
        """Popola tutti i dati"""
        
        # 1. Contoterzisti
        self.stdout.write('🔧 Popolamento Contoterzisti...')
        contoterzisti_data = [
            "Pusabren", "La Vite d'Oro", "Terra Viva", "Tribulé", "Gallo Marco",
            "Mauro Biondo", "Assen e Matteo", "Veglio Fratelli", "Loris", 
            "Proprietario", "Paolo Porello", "Castellengo Gianluigi", "Grattarola", "Vigneti 360"
        ]
        
        for nome in contoterzisti_data:
            Contoterzista.objects.get_or_create(nome=nome)
        
        # 2. Clienti - SOLO DATI REALI DAL FILE EXCEL
        self.stdout.write('🏢 Popolamento Clienti...')
        clienti_data = [
            "Prunotto / Alba", "Prunotto / Diano", "Prunotto / Asti", "Prunotto / Pian Romualdo",
            "Mauro Sebaste", "Michele Chiarlo SRL", "Azienda Agricola Chiarlo S.S / Alba",
            "Azienda Agricola Chiarlo S.S / Asti", "Bussia Soprana di Casiraghi Silvano",
            "Az. Agrivinicola Sylla Sebaste", "Ca' Rome'", "Corino", "Corino / Nocciole",
            "Carlin De Paolo", "Bello Mario / Vite", "Bello Mario / Nocciole", "Cauda Giuseppe",
            "Bruno Gianluca", "Grasso Tiziano / Vite", "Grasso Tiziano / Nocciole",
            "Franco Vincenzo / Vite", "Franco Vincenzo / Nocciole", "Tartaglino Alessandro",
            "Paolo Scavino di Enrico Scavino", "Cascina Alberta", "L'Alegra / Vite",
            "L'Alegra / Nocciole", "Guido Berta", "Zublema", "Broccardo SS",
            "Diego Pressenda SS", "Poglio Roberto", "Piattino", "Cagnasso Effren",
            "Soc. Coop. Pusabren", "Antinori Soc. Agricola ARL", "La Coltivatrice",
            "La Masera", "Rubbiolo Matteo", "Tenute del Vino - La Vite d'Oro",
            "La Cardinala", "Ferrero Giuseppe", "Tenute del Vino - Vigneti 360",
            "Saracco Pierluigi di Lanata Francesca"
        ]
        
        for nome in clienti_data:
            Cliente.objects.get_or_create(nome=nome)
        
        # 3. Principi Attivi
        self.stdout.write('🧪 Popolamento Principi Attivi...')
        principi_attivi_data = [
            "Bacillus amyloliquefaciens", "Bacillus subtilis", "Cyprodinil", "Fludioxonil",
            "Fenhexamid", "Azadiractina", "Lambda-cialotrina", "Rame", "Zolfo",
            "Glifosate", "Mesotrione", "Flufenacet", "Spiroxamine", "Tebuconazolo",
            "Folpet", "Metalaxyl-M", "Boscalid", "Pyraclostrobin", "Trifloxystrobin",
            "Azoxystrobin", "Dodine", "Fluopyram", "Tetraconazolo", "Penconazolo",
            "Myclobutanil", "Kresoxim-methyl", "Difenoconazolo", "Iprodione",
            "Procymidone", "Flusilazole", "Quinoxyfen", "Metrafenone", "Cyflufenamid",
            "Piraclostrobin", "Mandipropamid", "Dimethomorph", "Famoxadone",
            "Fenamidone", "Propamocarb", "Benalaxyl", "Metalaxyl", "Fosetyl-Al",
            "Cimoxanil", "Captan", "Thiram", "Ziram", "Propineb", "Mancozeb",
            "Deltametrina", "Imidacloprid", "Thiacloprid", "Pendimetalin",
            "Idrossido di rame", "Solfato di rame", "Bicarbonato di potassio"
        ]
        
        for nome in principi_attivi_data:
            PrincipioAttivo.objects.get_or_create(nome=nome)
        
        # 4. Cascine - TUTTI I DATI REALI DAL FILE EXCEL
        self.stdout.write('🏡 Popolamento Cascine...')
        cascine_data = [
            ("Serralunga", "Antinori Soc. Agricola ARL", "Terra Viva"),
            ("Bricco delle Viole Vergne", "Az. Agrivinicola Sylla Sebaste", "La Vite d'Oro"),
            ("Monrobiolo di Bussia", "Az. Agrivinicola Sylla Sebaste", "La Vite d'Oro"),
            ("Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", "La Vite d'Oro"),
            ("Cannubi", "Azienda Agricola Chiarlo S.S / Alba", "La Vite d'Oro"),
            ("Cerequio", "Azienda Agricola Chiarlo S.S / Alba", "La Vite d'Oro"),
            ("Perno", "Azienda Agricola Chiarlo S.S / Alba", "La Vite d'Oro"),
            ("Agliano", "Azienda Agricola Chiarlo S.S / Asti", "Pusabren"),
            ("Monbercelli", "Azienda Agricola Chiarlo S.S / Asti", "Pusabren"),
            ("Bussia", "Bussia Soprana di Casiraghi Silvano", "Tribulé"),
            ("Mosconi", "Bussia Soprana di Casiraghi Silvano", "Tribulé"),
            ("Mosconi Nuovo impianto", "Bussia Soprana di Casiraghi Silvano", "Tribulé"),
            ("Barbaresco", "Ca' Rome'", "La Vite d'Oro"),
            ("Serralunga", "Ca' Rome'", "La Vite d'Oro"),
            ("Treiso", "Cascina Alberta", "La Vite d'Oro"),
            ("Agliano", "Michele Chiarlo SRL", "Pusabren"),
            ("Calamandrana", "Michele Chiarlo SRL", "Pusabren"),
            ("Castelnuovo Calcea", "Michele Chiarlo SRL", "Pusabren"),
            ("Mirenghi Ugo", "Michele Chiarlo SRL", "Pusabren"),
            ("Montaldo Scarampi", "Michele Chiarlo SRL", "Pusabren"),
            ("Montemareto", "Michele Chiarlo SRL", "Pusabren"),
            ("Vigneto la Vespa", "Michele Chiarlo SRL", "Pusabren"),
            ("Serralunga+Pernanno", "Paolo Scavino di Enrico Scavino", "Veglio Fratelli"),
            ("Borgogno", "Prunotto / Alba", "La Vite d'Oro"),
            ("Bussia", "Prunotto / Alba", "La Vite d'Oro"),
            ("Pertinace", "Prunotto / Alba", "La Vite d'Oro"),
            ("Treiso", "Prunotto / Alba", "La Vite d'Oro"),
            ("Agliano", "Prunotto / Asti", "Pusabren"),
            ("Calliano", "Prunotto / Asti", "Pusabren"),
            ("Diano Cascina Boschi", "Prunotto / Diano", "Terra Viva"),
            ("Giordano", "Prunotto / Diano", "Terra Viva"),
            ("Nebbiolo e Arneis", "Prunotto / Diano", "Terra Viva"),
            ("Pian Romualdo", "Prunotto / Pian Romualdo", "Tribulé"),
            ("Lanata", "Saracco Pierluigi di Lanata Francesca", "Pusabren"),
            ("Canelli", "Soc. Coop. Pusabren", "Pusabren"),
            ("Castelnuovo Calcea", "Soc. Coop. Pusabren", "Pusabren"),
            ("Maranzana Mombaruzzo", "Soc. Coop. Pusabren", "Pusabren"),
            ("San Marzano Oliveto", "Soc. Coop. Pusabren", "Pusabren"),
            ("Barolo", "Tenute del Vino - La Vite d'Oro", "La Vite d'Oro"),
            ("Tirados", "Tenute del Vino - La Vite d'Oro", "La Vite d'Oro"),
            ("Ponti", "Tenute del Vino - Vigneti 360", "Vigneti 360"),
        ]
        
        for nome_cascina, nome_cliente, nome_contoterzista in cascine_data:
            try:
                cliente = Cliente.objects.get(nome=nome_cliente)
                contoterzista = Contoterzista.objects.get(nome=nome_contoterzista)
                
                cascina, created = Cascina.objects.get_or_create(
                    nome=nome_cascina,
                    cliente=cliente,
                    defaults={'contoterzista': contoterzista}
                )
                
                if not created and cascina.contoterzista != contoterzista:
                    cascina.contoterzista = contoterzista
                    cascina.save()
                    
            except (Cliente.DoesNotExist, Contoterzista.DoesNotExist) as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Saltata cascina {nome_cascina}: {e}')
                )
        
        # 5. Prodotti
        self.stdout.write('🏷️  Popolamento Prodotti...')
        prodotti_data = [
            # Fungicidi
            ("AMYLO-X", ["Bacillus amyloliquefaciens"], "L"),
            ("SERENADE ASO", ["Bacillus subtilis"], "L"),
            ("SWITCH", ["Cyprodinil", "Fludioxonil"], "Kg"),
            ("TELDOR PLUS", ["Fenhexamid"], "L"),
            ("CUPRAVIT BLU", ["Rame"], "Kg"),
            ("THIOVIT JET", ["Zolfo"], "Kg"),
            ("PROSARO", ["Tebuconazolo"], "L"),
            ("FOLPAN 80 WDG", ["Folpet"], "Kg"),
            ("RIDOMIL GOLD MZ", ["Metalaxyl-M", "Mancozeb"], "Kg"),
            ("LUNA PRIVILEGE", ["Fluopyram"], "L"),
            ("CANTUS", ["Boscalid"], "Kg"),
            ("CABRIO TOP", ["Pyraclostrobin"], "Kg"),
            ("FLINT MAX", ["Trifloxystrobin"], "Kg"),
            ("QUADRIS", ["Azoxystrobin"], "L"),
            ("SYLLIT 544 SC", ["Dodine"], "L"),
            
            # Insetticidi
            ("OIKOS", ["Azadiractina"], "L"),
            ("KARATHE ZEON", ["Lambda-cialotrina"], "L"),
            ("DECIS JET", ["Deltametrina"], "L"),
            ("CONFIDOR 200 SL", ["Imidacloprid"], "L"),
            ("CALYPSO", ["Thiacloprid"], "L"),
            
            # Erbicidi
            ("ROUNDUP POWER", ["Glifosate"], "L"),
            ("CALLISTO", ["Mesotrione"], "L"),
            ("KATANA", ["Flufenacet"], "L"),
            ("STOMP AQUA", ["Pendimetalin"], "L"),
            
            # Concimi
            ("AGROFERT MB 10-5-14.5", [], "Kg"),
            ("AGROLIG", [], "Kg"),
            ("LABIN 8-5-15", [], "Kg"),
            ("NITRATO AMMONICO", [], "Kg"),
            ("SOLFATO FERROSO", [], "Kg"),
            ("UREA 46", [], "Kg"),
            
            # Altri prodotti fitosanitari
            ("CHAMPION WG", ["Idrossido di rame"], "Kg"),
            ("HELIOCUIVRE", ["Solfato di rame"], "Kg"),
            ("MICROTHIOL SPECIAL", ["Zolfo"], "Kg"),
            ("VITISAN", ["Bicarbonato di potassio"], "Kg"),
        ]
        
        for nome, principi_nomi, unita in prodotti_data:
            prodotto, created = Prodotto.objects.get_or_create(
                nome=nome,
                defaults={'unita_misura': unita}
            )
            
            # Aggiungi principi attivi
            for principio_nome in principi_nomi:
                if principio_nome:
                    principio, _ = PrincipioAttivo.objects.get_or_create(nome=principio_nome)
                    prodotto.principi_attivi.add(principio)
        
        # 6. Terreni - TUTTI I DATI COMPLETI
        self.stdout.write('🌱 Popolamento Terreni Completi...')
        terreni_complete = [
            ("Nebbiolo", "Serralunga", "Antinori Soc. Agricola ARL", 3.44),
            ("Nebbiolo", "Bricco delle Viole Vergne", "Az. Agrivinicola Sylla Sebaste", 1.5),
            ("Nebbiolo", "Monrobiolo di Bussia", "Az. Agrivinicola Sylla Sebaste", 3.7),
            ("Asili", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 0.8),
            ("Cimitero", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 0.8),
            ("Faset", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 1.0),
            ("Montestefano", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 0.3),
            ("Sotto Paese", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 0.9),
            ("Cannubi", "Cannubi", "Azienda Agricola Chiarlo S.S / Alba", 1.0),
            ("Cerequio", "Cerequio", "Azienda Agricola Chiarlo S.S / Alba", 4.42),
            ("Nebbiolo", "Perno", "Azienda Agricola Chiarlo S.S / Alba", 0.79),
            ("Barbera", "Agliano", "Azienda Agricola Chiarlo S.S / Asti", 0.43),
            ("Barbera", "Monbercelli", "Azienda Agricola Chiarlo S.S / Asti", 4.09),
            ("Merlot", "Monbercelli", "Azienda Agricola Chiarlo S.S / Asti", 0.69),
            ("Nocciole", "Nocciole San Martino", "Bello Mario / Nocciole", 8.21),
            ("Barbera", "Vite San Martino", "Bello Mario / Vite", 1.0),
            ("Barbera e Merlot", "Vite San Martino", "Bello Mario / Vite", 1.14),
            ("Tutte le varietà", "Monforte", "Broccardo SS", 12.83),
            ("Arneis", "Priocca", "Bruno Gianluca", 1.88),
            ("Barbera e Nebbiolo", "Priocca", "Bruno Gianluca", 6.12),
            ("Nebbiolo", "Bussia", "Bussia Soprana di Casiraghi Silvano", 2.79),
            ("Mosconi", "Mosconi", "Bussia Soprana di Casiraghi Silvano", 1.26),
            ("Mosconi Nuovo Impianto", "Mosconi Nuovo impianto", "Bussia Soprana di Casiraghi Silvano", 1.13),
            ("Nebbiolo", "Barbaresco", "Ca' Rome'", 1.89),
            ("Nebbiolo", "Serralunga", "Ca' Rome'", 1.75),
            ("Barbera", "Vezza", "Carlin De Paolo", 3.36),
            ("Nebbiolo", "Treiso", "Cascina Alberta", 5.91),
            ("Barbera", "La Torricella", "Diego Pressenda SS", 4.11),
            ("Gavi", "Gavi", "Elio Altare", 2.45),
            ("Langhe Nebbiolo", "Langhe Nebbiolo", "Elio Altare", 0.65),
            ("Larigi", "Larigi", "Elio Altare", 1.47),
            ("Arborina", "Arborina", "Elio Altare", 2.04),
            ("Gavarini", "Gavarini", "Elio Altare", 2.62),
            ("Nebbiolo", "Enzo Boglietti", "Enzo Boglietti", 4.0),
            ("Barbera", "Eredi Virginia Ferrero", "Eredi Virginia Ferrero", 2.5),
            ("Barbera", "Torrazzo Paolo", "Franco Vincenzo / Vite", 1.2),
            ("Nebbiolo", "Bussia", "Giuseppe Cortese", 1.2),
            ("Nebbiolo", "Trinità", "Giuseppe Cortese", 0.8),
            ("Nebbiolo", "Rabajà", "Giuseppe Cortese", 0.45),
            ("Nebbiolo", "Roncagliette", "Giuseppe Cortese", 0.78),
            ("Nebbiolo", "Frassinello", "Mario Marengo", 0.9),
            ("Nebbiolo", "Brunate", "Mario Marengo", 1.3),
            ("Nebbiolo", "Rivette", "Mario Marengo", 0.7),
            ("Nebbiolo", "Mauro Sebaste", "Mauro Sebaste", 3.5),
            ("Barbera", "Agliano", "Michele Chiarlo SRL", 15.8),
            ("Barbera", "Calamandrana", "Michele Chiarlo SRL", 6.7),
            ("Barbera", "Castelnuovo Calcea", "Michele Chiarlo SRL", 12.4),
            ("Barbera", "Mirenghi Ugo", "Michele Chiarlo SRL", 3.2),
            ("Barbera", "Montaldo Scarampi", "Michele Chiarlo SRL", 8.9),
            ("Barbera", "Montemareto", "Michele Chiarlo SRL", 5.1),
            ("Barbera", "Vigneto la Vespa", "Michele Chiarlo SRL", 4.3),
            ("Nebbiolo", "Bricco delle Viole", "Molino Franco", 1.8),
            ("Nebbiolo", "Conca dell'Annunziata", "Molino Franco", 2.2),
            ("Nebbiolo", "Serralunga+Pernanno", "Paolo Scavino di Enrico Scavino", 3.4),
            ("Nebbiolo", "Fiasco", "Poderi e Cantine Oddero", 1.2),
            ("Nebbiolo", "Frassinello", "Poderi e Cantine Oddero", 2.8),
            ("Nebbiolo", "Borgogno", "Prunotto / Alba", 3.2),
            ("Nebbiolo", "Bussia", "Prunotto / Alba", 2.8),
            ("Nebbiolo", "Pertinace", "Prunotto / Alba", 1.9),
            ("Nebbiolo", "Treiso", "Prunotto / Alba", 2.1),
            ("Barbera", "Agliano", "Prunotto / Asti", 4.5),
            ("Barbera", "Calliano", "Prunotto / Asti", 3.2),
            ("Dolcetto", "Diano Cascina Boschi", "Prunotto / Diano", 2.8),
            ("Dolcetto", "Giordano", "Prunotto / Diano", 1.9),
            ("Nebbiolo e Arneis", "Nebbiolo e Arneis", "Prunotto / Diano", 3.1),
            ("Nebbiolo", "Pian Romualdo", "Prunotto / Pian Romualdo", 4.2),
            ("Moscato", "Lanata", "Saracco Pierluigi di Lanata Francesca", 2.1),
            ("Barbera", "Canelli", "Soc. Coop. Pusabren", 8.5),
            ("Barbera", "Castelnuovo Calcea", "Soc. Coop. Pusabren", 12.3),
            ("Barbera", "Maranzana Mombaruzzo", "Soc. Coop. Pusabren", 15.8),
            ("Barbera", "San Marzano Oliveto", "Soc. Coop. Pusabren", 9.7),
            ("Nebbiolo", "Carretta", "Tenuta Carretta", 3.5),
            ("Nebbiolo", "Barolo", "Tenute del Vino - La Vite d'Oro", 4.2),
            ("Nebbiolo", "Tirados", "Tenute del Vino - La Vite d'Oro", 2.8),
            ("Barbera", "Ponti", "Tenute del Vino - Vigneti 360", 6.1),
            ("Cortese", "Villa Sparina", "Villa Sparina Resort", 8.5),
        ]
        
        for nome_terreno, nome_cascina, nome_cliente, superficie in terreni_complete:
            try:
                cascina = Cascina.objects.get(nome=nome_cascina, cliente__nome=nome_cliente)
                
                Terreno.objects.get_or_create(
                    nome=nome_terreno,
                    cascina=cascina,
                    defaults={'superficie': Decimal(str(superficie))}
                )
                
            except Cascina.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Saltato terreno {nome_terreno}: cascina "{nome_cascina}" di "{nome_cliente}" non trovata')
                )
        terreni_data = [
            ("Nebbiolo", "Serralunga", "Antinori Soc. Agricola ARL", 3.44),
            ("Asili", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 0.8),
            ("Cimitero", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 0.8),
            ("Faset", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 1.0),
            ("Montestefano", "Barbaresco", "Azienda Agricola Chiarlo S.S / Alba", 0.3),
            ("Cannubi", "Cannubi", "Azienda Agricola Chiarlo S.S / Alba", 1.0),
            ("Cerequio", "Cerequio", "Azienda Agricola Chiarlo S.S / Alba", 2.5),
            ("Moscato", "Agliano", "Azienda Agricola Chiarlo S.S / Asti", 1.2),
            ("Barbera", "Monbercelli", "Azienda Agricola Chiarlo S.S / Asti", 2.1),
            ("Bussia Soprano", "Bussia", "Bussia Soprana di Casiraghi Silvano", 4.5),
            ("Gavarini", "Gavarini", "Elio Altare", 2.8),
            ("Frassinello", "Frassinello", "Poderi e Cantine Oddero", 3.2),
            ("Cortese", "Villa Sparina", "Villa Sparina Resort", 5.1),
            ("Pelaverga", "Vigna del Pero", "Az. Agr. Castello di Verduno", 1.4),
            ("Ornellaia", "Ornellaia", "Tenuta dell'Ornellaia", 8.7),
            ("Parafada", "Parafada", "Massolino", 2.3),
            ("Vigna Rionda", "Vigna Rionda", "Massolino", 1.8),
            ("Acclivi", "Acclivi", "Az. Agricola Comm. G.B. Burlotto", 1.5),
            ("Gatinera", "Gatinera", "Fontanafredda srl", 4.2),
            ("Lazzarito", "Lazzarito", "Fontanafredda srl", 3.6),
            ("Bricco Boschis", "Bricco Boschis", "Cavallotto Fratelli", 2.7),
            ("San Giuseppe", "San Giuseppe", "Cavallotto Fratelli", 1.9),
            ("Madonna delle Grazie", "Madonna delle Grazie", "Varaldo Osvaldo", 2.1),
            ("Ornato", "Ornato", "Palladino", 1.6),
            ("Ca' Mia", "Ca' Mia", "Brida Giacomo Az. Agricola", 3.3),
            ("Gallina", "Gallina", "Azienda Agricola La Spinetta di Rivetti Giorgio", 2.5),
            ("Roero Arneis", "Roero", "Cordero Franco", 4.8),
            ("Brunate", "Brunate", "Giuseppe Rinaldi", 1.2),
            ("Le Coste", "Le Coste", "Giuseppe Rinaldi", 0.9),
            ("Bric del Fiasc", "Bric del Fiasc", "Paolo Scavino", 1.7),
        ]
        
        # Statistiche finali
        self.stdout.write('\n📊 STATISTICHE FINALI:')
        self.stdout.write(f'  • Clienti: {Cliente.objects.count()}')
        self.stdout.write(f'  • Contoterzisti: {Contoterzista.objects.count()}')
        self.stdout.write(f'  • Cascine: {Cascina.objects.count()}')
        self.stdout.write(f'  • Terreni: {Terreno.objects.count()}')
        self.stdout.write(f'  • Principi Attivi: {PrincipioAttivo.objects.count()}')
        self.stdout.write(f'  • Prodotti: {Prodotto.objects.count()}')