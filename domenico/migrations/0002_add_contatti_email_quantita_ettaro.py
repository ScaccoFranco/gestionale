from django.db import migrations, models
import django.db.models.deletion
import django.core.validators

class Migration(migrations.Migration):

    dependencies = [
        ('domenico', '0001_initial'),
    ]

    operations = [
        # Rinomina il campo quantita in quantita_per_ettaro
        migrations.RenameField(
            model_name='trattamentoprodotto',
            old_name='quantita',
            new_name='quantita_per_ettaro',
        ),
        
        # Aggiorna l'help text del campo
        migrations.AlterField(
            model_name='trattamentoprodotto',
            name='quantita_per_ettaro',
            field=models.DecimalField(
                decimal_places=3, 
                help_text='Quantità per ettaro', 
                max_digits=10, 
                validators=[django.core.validators.MinValueValidator(0.001)]
            ),
        ),
        
        # Aggiorna il __str__ method nel model
        migrations.AlterModelOptions(
            name='trattamentoprodotto',
            options={
                'verbose_name': 'Prodotto del Trattamento', 
                'verbose_name_plural': 'Prodotti del Trattamento'
            },
        ),
        
        # Crea il modello ContattoEmail
        migrations.CreateModel(
            name='ContattoEmail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Nome del contatto', max_length=200)),
                ('email', models.EmailField(help_text='Indirizzo email del contatto', max_length=254)),
                ('ruolo', models.CharField(blank=True, help_text='Es: Contoterzista, Agronomo, Responsabile', max_length=100)),
                ('telefono', models.CharField(blank=True, max_length=20)),
                ('attivo', models.BooleanField(default=True, help_text='Se deselezionato, non riceverà le comunicazioni')),
                ('priorita', models.IntegerField(default=1, help_text='1=Alta priorità, 2=Media, 3=Bassa (per ordinare i contatti)')),
                ('note', models.TextField(blank=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contatti_email', to='domenico.cliente')),
            ],
            options={
                'verbose_name': 'Contatto Email',
                'verbose_name_plural': 'Contatti Email',
                'ordering': ['priorita', 'nome'],
            },
        ),
        
        # Crea il modello ComunicazioneTrattamento
        migrations.CreateModel(
            name='ComunicazioneTrattamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_invio', models.DateTimeField(auto_now_add=True)),
                ('destinatari', models.TextField(help_text='Lista email destinatari (separati da virgola)')),
                ('oggetto', models.CharField(max_length=500)),
                ('corpo_email', models.TextField()),
                ('allegati', models.TextField(blank=True, help_text='Lista percorsi allegati (separati da virgola)')),
                ('inviato_con_successo', models.BooleanField(default=False)),
                ('errore', models.TextField(blank=True)),
                ('trattamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comunicazioni', to='domenico.trattamento')),
            ],
            options={
                'verbose_name': 'Comunicazione Trattamento',
                'verbose_name_plural': 'Comunicazioni Trattamenti',
                'ordering': ['-data_invio'],
            },
        ),
    ]