from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from domenico.models import Cliente, Terreno, Prodotto, Contoterzista, ActivityLog

class Command(BaseCommand):
    help = 'Genera dati di test per i log di attività'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Numero di log di test da generare (default: 50)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(
            self.style.SUCCESS(f'🧪 Generazione {count} log di test...')
        )
        
        # Tipi di attività per test
        activity_types = [
            'cliente_created',
            'terreno_created', 
            'prodotto_created',
            'contoterzista_created',
            'trattamento_created',
            'comunicazione_sent'
        ]
        
        # Genera log casuali negli ultimi 30 giorni
        start_date = timezone.now() - timedelta(days=30)
        
        created_count = 0
        
        for i in range(count):
            # Data casuale negli ultimi 30 giorni
            random_days = random.randint(0, 30)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            
            timestamp = start_date + timedelta(
                days=random_days,
                hours=random_hours,
                minutes=random_minutes
            )
            
            # Tipo attività casuale
            activity_type = random.choice(activity_types)
            
            # Genera titolo e descrizione
            titles = {
                'cliente_created': [
                    'Nuovo cliente: Azienda Test {i}',
                    'Cliente aggiunto: Test Farm {i}',
                    'Registrazione cliente: Agricola {i}'
                ],
                'terreno_created': [
                    'Nuovo terreno: Campo {i}',
                    'Terreno aggiunto: Vigna {i}',
                    'Registrazione terreno: Lotto {i}'
                ],
                'prodotto_created': [
                    'Nuovo prodotto: Prodotto Test {i}',
                    'Prodotto registrato: Fitosanitario {i}',
                    'Aggiunto prodotto: Trattamento {i}'
                ]
            }
            
            title_templates = titles.get(activity_type, ['Attività Test {i}'])
            title = random.choice(title_templates).format(i=i+1)
            
            description = f'Descrizione di test per {title} generata automaticamente'
            
            # Crea il log
            ActivityLog.objects.create(
                activity_type=activity_type,
                title=title,
                description=description,
                timestamp=timestamp,
                extra_data={
                    'test_data': True,
                    'generated_at': timezone.now().isoformat(),
                    'batch_id': f'test_batch_{timezone.now().strftime("%Y%m%d_%H%M%S")}'
                }
            )
            
            created_count += 1
            
            if (i + 1) % 10 == 0:
                self.stdout.write(f'  ✅ Generati {i + 1}/{count} log...')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Generati {created_count} log di test con successo!')
        )
        
        self.stdout.write('\n📊 Riepilogo:')
        self.stdout.write(f'  • Periodo: {start_date.strftime("%d/%m/%Y")} - {timezone.now().strftime("%d/%m/%Y")}')
        self.stdout.write(f'  • Log totali nel database: {ActivityLog.objects.count()}')
        self.stdout.write(f'  • Log di test creati: {ActivityLog.objects.filter(extra_data__test_data=True).count()}')