from django.core.management.base import BaseCommand
from django.db import transaction
from domenico.models import Cliente, ContattoEmail

class Command(BaseCommand):
    help = 'Popola contatti email di esempio per i clienti esistenti'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Cancella tutti i contatti email esistenti prima di popolare',
        )
        parser.add_argument(
            '--test-data',
            action='store_true',
            help='Aggiunge anche dati di test con email fittizie',
        )
        parser.add_argument(
            '--show-stats',
            action='store_true',
            help='Mostra statistiche dettagliate dopo il popolamento',
        )

    def handle(self, *args, **options):
        # Statistiche iniziali
        self.stdout.write(self.style.SUCCESS('=== POPOLAMENTO CONTATTI EMAIL ===\n'))
        
        stats_iniziali = {
            'clienti': Cliente.objects.count(),
            'contatti_prima': ContattoEmail.objects.count(),
            'clienti_con_contatti_prima': Cliente.objects.filter(contatti_email__isnull=False).distinct().count()
        }
        
        self.stdout.write("📊 Statistiche iniziali:")
        self.stdout.write(f"  • Clienti totali: {stats_iniziali['clienti']}")
        self.stdout.write(f"  • Contatti esistenti: {stats_iniziali['contatti_prima']}")
        self.stdout.write(f"  • Clienti con contatti: {stats_iniziali['clienti_con_contatti_prima']}")
        
        if options['reset']:
            self.stdout.write(
                self.style.WARNING('\n⚠️  Cancellazione di tutti i contatti email esistenti...')
            )
            ContattoEmail.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Contatti email cancellati'))

        try:
            with transaction.atomic():
                self.populate_contatti_reali()
                
                if options['test_data']:
                    self.populate_contatti_test()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Errore durante il popolamento: {e}')
            )
            raise

        # Statistiche finali
        stats_finali = {
            'contatti_dopo': ContattoEmail.objects.count(),
            'clienti_con_contatti_dopo': Cliente.objects.filter(contatti_email__isnull=False).distinct().count()
        }
        
        self.stdout.write('\n📈 STATISTICHE FINALI:')
        self.stdout.write(f"  • Contatti totali: {stats_finali['contatti_dopo']}")
        self.stdout.write(f"  • Clienti con contatti: {stats_finali['clienti_con_contatti_dopo']}")
        self.stdout.write(f"  • Contatti aggiunti: {stats_finali['contatti_dopo'] - stats_iniziali['contatti_prima']}")
        
        if options['show_stats']:
            self.show_detailed_stats()
        
        self.stdout.write(self.style.SUCCESS('\n✅ Popolamento contatti email completato con successo!'))
        self.stdout.write('\n🌐 Per gestire i contatti vai su: http://localhost:8000/contatti-email/')

    def populate_contatti_reali(self):
        """Popola contatti email reali basati sui dati esistenti"""
        self.stdout.write('📧 Popolamento contatti email reali...')
        
        # Mappa dei contatti reali per cliente
        contatti_mapping = {
            # Prunotto
            "Prunotto / Alba": [
                {
                    "nome": "Marco Bianchi",
                    "email": "marco.bianchi@prunotto.it"
                },
                {
                    "nome": "Elena Rossi",
                    "email": "elena.rossi@prunotto.it"
                }
            ],
            "Prunotto / Asti": [
                {
                    "nome": "Giuseppe Verdi",
                    "email": "giuseppe.verdi@prunotto.it"
                }
            ],
            
            # Michele Chiarlo
            "Michele Chiarlo SRL": [
                {
                    "nome": "Alberto Chiarlo",
                    "email": "alberto@chiarlo.it"
                },
                {
                    "nome": "Stefano Costa",
                    "email": "stefano.costa@chiarlo.it"
                }
            ],
            
            # Azienda Agricola Chiarlo
            "Azienda Agricola Chiarlo S.S / Alba": [
                {
                    "nome": "Claudio Fenocchio",
                    "email": "claudio@chiarloalba.it"
                }
            ],
            
            # Antinori
            "Antinori Soc. Agricola ARL": [
                {
                    "nome": "Francesco Marengo",
                    "email": "f.marengo@antinori.it"
                },
                {
                    "nome": "Anna Ferrero",
                    "email": "a.ferrero@antinori.it"
                }
            ],
            
            # Paolo Scavino
            "Paolo Scavino di Enrico Scavino": [
                {
                    "nome": "Enrico Scavino",
                    "email": "enrico@scavino.com"
                }
            ],
            
            # Mauro Sebaste
            "Mauro Sebaste": [
                {
                    "nome": "Mauro Sebaste",
                    "email": "mauro@sebaste.it"
                },
                {
                    "nome": "Tiziana Sebaste",
                    "email": "tiziana@sebaste.it"
                }
            ]
        }
        
        contatti_creati = 0
        
        for nome_cliente, contatti in contatti_mapping.items():
            try:
                cliente = Cliente.objects.get(nome=nome_cliente)
                
                for contatto_data in contatti:
                    contatto, created = ContattoEmail.objects.get_or_create(
                        cliente=cliente,
                        email=contatto_data['email'],
                        defaults={
                            'nome': contatto_data['nome']
                        }
                    )
                    
                    if created:
                        contatti_creati += 1
                        self.stdout.write(f"  ✅ {contatto.nome} - {cliente.nome}")
                
            except Cliente.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  Cliente '{nome_cliente}' non trovato")
                )
        
        self.stdout.write(f"  ✅ Creati {contatti_creati} contatti email reali")

    def populate_contatti_test(self):
        """Popola contatti email di test per sviluppo"""
        self.stdout.write('🧪 Popolamento contatti email di test...')
        
        # Prendi i primi 10 clienti che non hanno contatti
        clienti_senza_contatti = Cliente.objects.filter(
            contatti_email__isnull=True
        ).distinct()[:10]
        
        ruoli_test = [
            "Contoterzista",
            "Agronomo", 
            "Responsabile Vigneti",
            "Direttore Tecnico",
            "Responsabile Trattamenti",
            "Consulente Agrario"
        ]
        
        contatti_test_creati = 0
        
        for i, cliente in enumerate(clienti_senza_contatti):
            # Crea 1-3 contatti per cliente
            num_contatti = min(3, max(1, (i % 3) + 1))
            
            for j in range(num_contatti):
                nome_base = f"Test{i+1}Contatto{j+1}"
                email_base = f"test.{cliente.nome.lower().replace(' ', '.')}.{j+1}@example.com"
                
                contatto = ContattoEmail.objects.create(
                    cliente=cliente,
                    nome=f"{nome_base} {cliente.nome}",
                    email=email_base
                )
                
                contatti_test_creati += 1
                self.stdout.write(f"  ✅ {contatto.nome} (TEST)")
        
        self.stdout.write(f"  ✅ Creati {contatti_test_creati} contatti email di test")


    def show_detailed_stats(self):
        """Mostra statistiche dettagliate"""
        self.stdout.write('\n📋 STATISTICHE DETTAGLIATE:')
        
        
        # Clienti con più contatti
        from django.db.models import Count
        clienti_top = Cliente.objects.annotate(
            num_contatti=Count('contatti_email')
        ).filter(num_contatti__gt=0).order_by('-num_contatti')[:5]
        
        self.stdout.write('\n🏆 TOP 5 CLIENTI PER NUMERO CONTATTI:')
        for cliente in clienti_top:
            self.stdout.write(f"  • {cliente.nome}: {cliente.num_contatti} contatti")
        

