import csv
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from domenico.models import (
    Cliente, Cascina, Contoterzista, Prodotto, Terreno, 
    ContattoEmail, PrincipioAttivo
)

class Command(BaseCommand):
    help = 'Populate database from CSV files in files_csv directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without making changes'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip records that already exist in the database'
        )

    def find_best_cascina_match(self, cascina_name):
        """Find the best matching cascina using fuzzy string matching"""
        all_cascine = Cascina.objects.all()
        
        # First try exact match
        exact_match = all_cascine.filter(nome__iexact=cascina_name).first()
        if exact_match:
            return exact_match
        
        # Try to extract the cascina name from compound names like "Client Name - Cascina Name"
        if ' - ' in cascina_name:
            # Split on ' - ' and try the last part (should be cascina name)
            cascina_parts = cascina_name.split(' - ')
            for i in range(len(cascina_parts) - 1, -1, -1):  # Try from last to first
                part = cascina_parts[i].strip()
                if part:
                    exact_match = all_cascine.filter(nome__iexact=part).first()
                    if exact_match:
                        return exact_match
                    
                    # Try partial match on this part
                    partial_match = all_cascine.filter(nome__icontains=part).first()
                    if partial_match:
                        return partial_match
        
        # Try partial matches with original name
        partial_matches = all_cascine.filter(nome__icontains=cascina_name.split(' - ')[0])
        if partial_matches.exists():
            return partial_matches.first()
        
        # Try reverse partial match
        base_name = cascina_name.split(' - ')[0] if ' - ' in cascina_name else cascina_name
        reverse_matches = all_cascine.filter(nome__icontains=base_name)
        if reverse_matches.exists():
            return reverse_matches.first()
            
        return None

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.skip_existing = options['skip_existing']
        self.base_dir = 'files_csv'
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        
        try:
            with transaction.atomic():
                # Import in dependency order
                self.import_contoterzisti()
                self.import_prodotti()
                self.import_clienti()
                self.import_cascine()
                self.import_vigneti()
                # self.import_trattamenti()  # Complex, will implement after basic data
                
                if self.dry_run:
                    # Rollback transaction in dry run
                    transaction.set_rollback(True)
                    self.stdout.write(self.style.SUCCESS("DRY RUN COMPLETED"))
                else:
                    self.stdout.write(self.style.SUCCESS("IMPORT COMPLETED SUCCESSFULLY"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during import: {str(e)}"))
            raise

    def import_contoterzisti(self):
        """Import contractors from Contoterzisti-Grid view.csv"""
        file_path = os.path.join(self.base_dir, 'Contoterzisti-Grid view.csv')
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
            return
        
        self.stdout.write("Importing Contoterzisti...")
        created_count = 0
        skipped_count = 0
        
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                nome = row['Nome contoterzista'].strip()
                if not nome:
                    continue
                
                if self.skip_existing and Contoterzista.objects.filter(nome=nome).exists():
                    skipped_count += 1
                    continue
                
                if not self.dry_run:
                    contoterzista, created = Contoterzista.objects.get_or_create(
                        nome=nome,
                        defaults={'email': ''}
                    )
                    if created:
                        created_count += 1
                else:
                    self.stdout.write(f"  Would create Contoterzista: {nome}")
                    created_count += 1
        
        self.stdout.write(f"  Created: {created_count}, Skipped: {skipped_count}")

    def import_prodotti(self):
        """Import products from Prodotti-Grid view.csv"""
        file_path = os.path.join(self.base_dir, 'Prodotti-Grid view.csv')
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
            return
        
        self.stdout.write("Importing Prodotti...")
        created_count = 0
        skipped_count = 0
        
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                nome = row['Nome prodotto'].strip()
                if not nome:
                    continue
                
                if self.skip_existing and Prodotto.objects.filter(nome=nome).exists():
                    skipped_count += 1
                    continue
                
                principio_attivo_str = row.get('Principio attivo', '').strip()
                avversita = row.get('Avversità', '').strip()
                nr = row.get('N.R.', '').strip()
                unita_misura = row.get('Unità di misura', '').strip()
                
                if not self.dry_run:
                    prodotto, created = Prodotto.objects.get_or_create(
                        nome=nome,
                        defaults={
                            'descrizione': f"Avversità: {avversita}. N.R.: {nr}" if avversita or nr else '',
                            'unita_misura': unita_misura or 'L'
                        }
                    )
                    
                    # Handle principio attivo if provided
                    if created and principio_attivo_str:
                        principio_attivo, _ = PrincipioAttivo.objects.get_or_create(
                            nome=principio_attivo_str
                        )
                        prodotto.principi_attivi.add(principio_attivo)
                    
                    if created:
                        created_count += 1
                else:
                    self.stdout.write(f"  Would create Prodotto: {nome}")
                    created_count += 1
        
        self.stdout.write(f"  Created: {created_count}, Skipped: {skipped_count}")

    def import_clienti(self):
        """Import clients from Cliente-Grid view.csv"""
        file_path = os.path.join(self.base_dir, 'Cliente-Grid view.csv')
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
            return
        
        self.stdout.write("Importing Clienti...")
        created_count = 0
        skipped_count = 0
        
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                nome = row['Nome cliente'].strip()
                if not nome:
                    continue
                
                if self.skip_existing and Cliente.objects.filter(nome=nome).exists():
                    skipped_count += 1
                    continue
                
                if not self.dry_run:
                    cliente, created = Cliente.objects.get_or_create(nome=nome)
                    if created:
                        created_count += 1
                        
                        # Create email contacts if available
                        rivenditori = row.get('Rivenditori', '')
                        if rivenditori:
                            # This seems to be a contact name, we could create a default email
                            ContattoEmail.objects.create(
                                cliente=cliente,
                                nome=rivenditori.strip(),
                                email=f"{rivenditori.replace(' ', '').lower()}@example.com"
                            )
                else:
                    self.stdout.write(f"  Would create Cliente: {nome}")
                    created_count += 1
        
        self.stdout.write(f"  Created: {created_count}, Skipped: {skipped_count}")

    def import_cascine(self):
        """Import farms from Cascina-Grid view.csv"""
        file_path = os.path.join(self.base_dir, 'Cascina-Grid view.csv')
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
            return
        
        self.stdout.write("Importing Cascine...")
        created_count = 0
        skipped_count = 0
        
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                nome_cascina = row['Nome cascina'].strip()
                cliente_nome = row['Cliente'].strip()
                contoterzista_nome = row['Contoterzista'].strip()
                superficie_str = row.get('Superficie cascina', '0').strip()
                
                if not nome_cascina or not cliente_nome:
                    continue
                
                # Parse surface area
                try:
                    superficie = Decimal(superficie_str) if superficie_str else Decimal('0')
                except:
                    superficie = Decimal('0')
                
                # Find related objects
                try:
                    cliente = Cliente.objects.get(nome=cliente_nome)
                except Cliente.DoesNotExist:
                    self.stdout.write(f"  Warning: Cliente not found: {cliente_nome}")
                    continue
                
                contoterzista = None
                if contoterzista_nome:
                    try:
                        contoterzista = Contoterzista.objects.get(nome=contoterzista_nome)
                    except Contoterzista.DoesNotExist:
                        self.stdout.write(f"  Warning: Contoterzista not found: {contoterzista_nome}")
                
                if self.skip_existing and Cascina.objects.filter(nome=nome_cascina, cliente=cliente).exists():
                    skipped_count += 1
                    continue
                
                if not self.dry_run:
                    _, created = Cascina.objects.get_or_create(
                        nome=nome_cascina,
                        cliente=cliente,
                        defaults={
                            'contoterzista': contoterzista
                        }
                    )
                    if created:
                        created_count += 1
                else:
                    self.stdout.write(f"  Would create Cascina: {nome_cascina} for {cliente_nome}")
                    created_count += 1
        
        self.stdout.write(f"  Created: {created_count}, Skipped: {skipped_count}")

    def import_vigneti(self):
        """Import vineyards from Vigneto-Grid view.csv"""
        file_path = os.path.join(self.base_dir, 'Vigneto-Grid view.csv')
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
            return
        
        self.stdout.write("Importing Vigneti...")
        created_count = 0
        skipped_count = 0
        
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                nome_vigneto = row.get('Nome vigneto', '').strip()
                cascina_nome = row.get('Cascina', '').strip()  # This is the correct column with cascina names
                superficie_str = row.get('Superficie vigneto', '0').strip()
                # The vineyard name often contains the grape variety
                
                if not nome_vigneto or not cascina_nome:
                    continue
                
                # Parse surface area
                try:
                    superficie = Decimal(superficie_str) if superficie_str else Decimal('0')
                except:
                    superficie = Decimal('0')
                
                # Find cascina using fuzzy matching
                cascina = self.find_best_cascina_match(cascina_nome)
                if not cascina:
                    self.stdout.write(f"  Warning: Cascina not found: {cascina_nome}")
                    continue
                
                if self.skip_existing and Terreno.objects.filter(nome=nome_vigneto, cascina=cascina).exists():
                    skipped_count += 1
                    continue
                
                if not self.dry_run:
                    _, created = Terreno.objects.get_or_create(
                        nome=nome_vigneto,
                        cascina=cascina,
                        defaults={
                            'superficie': superficie
                        }
                    )
                    if created:
                        created_count += 1
                else:
                    self.stdout.write(f"  Would create Terreno: {nome_vigneto} in {cascina_nome}")
                    created_count += 1
        
        self.stdout.write(f"  Created: {created_count}, Skipped: {skipped_count}")

    def import_trattamenti(self):
        """Import treatments - complex data, implement later"""
        self.stdout.write("Trattamenti import not yet implemented (complex data structure)")
        pass