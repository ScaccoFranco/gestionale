from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from domenico.models import ActivityLog
from domenico.activity_logging import cleanup_old_logs, get_activity_stats

class Command(BaseCommand):
    help = 'Pulisce i log di attività vecchi e mostra statistiche'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Numero di giorni di log da mantenere (default: 90)'
        )
        
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Mostra solo le statistiche senza eliminare nulla'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Elimina senza chiedere conferma'
        )

    def handle(self, *args, **options):
        days_to_keep = options['days']
        stats_only = options['stats_only']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS('🧹 Gestione Log Attività Sistema Gestionale')
        )
        self.stdout.write('=' * 60)
        
        # Mostra statistiche correnti
        self.show_current_stats()
        
        if stats_only:
            self.stdout.write('\n✅ Solo statistiche richieste, nessuna eliminazione.')
            return
        
        # Calcola quanti log verrebbero eliminati
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        logs_to_delete = ActivityLog.objects.filter(timestamp__lt=cutoff_date).count()
        
        if logs_to_delete == 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Nessun log da eliminare (tutti più recenti di {days_to_keep} giorni)')
            )
            return
        
        self.stdout.write(f'\n📊 LOG DA ELIMINARE:')
        self.stdout.write(f'  • Data limite: {cutoff_date.strftime("%d/%m/%Y %H:%M")}')
        self.stdout.write(f'  • Log da eliminare: {logs_to_delete}')
        self.stdout.write(f'  • Giorni di retention: {days_to_keep}')
        
        # Chiedi conferma se non forzato
        if not force:
            self.stdout.write('')
            confirm = input('⚠️  Continuare con l\'eliminazione? (s/N): ')
            if confirm.lower() not in ['s', 'si', 'y', 'yes']:
                self.stdout.write(self.style.WARNING('❌ Operazione annullata.'))
                return
        
        # Esegui pulizia
        self.stdout.write('\n🔄 Eliminazione in corso...')
        
        try:
            deleted_count = cleanup_old_logs(days_to_keep)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Eliminati {deleted_count} log di attività.')
            )
            
            # Mostra statistiche aggiornate
            self.stdout.write('\n📊 STATISTICHE AGGIORNATE:')
            self.show_current_stats()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Errore durante l\'eliminazione: {str(e)}')
            )

    def show_current_stats(self):
        """Mostra statistiche correnti dei log"""
        try:
            # Statistiche base
            total_logs = ActivityLog.objects.count()
            
            # Log degli ultimi 7 giorni
            week_ago = timezone.now() - timedelta(days=7)
            logs_week = ActivityLog.objects.filter(timestamp__gte=week_ago).count()
            
            # Log degli ultimi 30 giorni
            month_ago = timezone.now() - timedelta(days=30)
            logs_month = ActivityLog.objects.filter(timestamp__gte=month_ago).count()
            
            # Log più vecchio e più recente
            oldest_log = ActivityLog.objects.order_by('timestamp').first()
            newest_log = ActivityLog.objects.order_by('-timestamp').first()
            
            self.stdout.write(f'\n📊 STATISTICHE ATTUALI LOG:')
            self.stdout.write(f'  • Totali nel database: {total_logs}')
            self.stdout.write(f'  • Ultimi 7 giorni: {logs_week}')
            self.stdout.write(f'  • Ultimi 30 giorni: {logs_month}')
            
            if oldest_log:
                self.stdout.write(f'  • Log più vecchio: {oldest_log.timestamp.strftime("%d/%m/%Y %H:%M")}')
            
            if newest_log:
                self.stdout.write(f'  • Log più recente: {newest_log.timestamp.strftime("%d/%m/%Y %H:%M")}')
            
            # Top 5 tipi di attività
            from django.db.models import Count
            top_activities = ActivityLog.objects.values('activity_type').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            if top_activities:
                self.stdout.write(f'\n🏆 TOP 5 TIPI ATTIVITÀ:')
                for i, activity in enumerate(top_activities, 1):
                    activity_display = dict(ActivityLog.ACTIVITY_TYPES).get(
                        activity['activity_type'], 
                        activity['activity_type']
                    )
                    self.stdout.write(f'  {i}. {activity_display}: {activity["count"]}')
            
            # Statistiche dettagliate degli ultimi 7 giorni
            stats_7_days = get_activity_stats(7)
            if stats_7_days['activities_by_day']:
                self.stdout.write(f'\n📈 ATTIVITÀ GIORNALIERE (ultimi 7 giorni):')
                for day_stat in stats_7_days['activities_by_day']:
                    date_str = day_stat['date'].strftime('%d/%m/%Y')
                    self.stdout.write(f'  • {date_str}: {day_stat["count"]} attività')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Errore nel calcolo statistiche: {str(e)}')
            )
