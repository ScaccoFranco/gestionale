import requests
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class WeatherService:
    """Servizio per gestire le chiamate WeatherAPI con cache e gestione errori"""
    
    def __init__(self):
        # Configurazione - AGGIUNGI QUESTE IMPOSTAZIONI AL TUO settings.py
        self.api_key = getattr(settings, 'WEATHER_API_KEY', '')
        self.base_url = 'https://api.weatherapi.com/v1'
        self.default_location = getattr(settings, 'WEATHER_LOCATION', 'Alba, Piemonte, Italy')
        self.cache_timeout = 600  # 10 minuti
        self.timeout = 10  # 10 secondi timeout
        
    
    def get_current_weather(self, location=None):
        """Ottiene il meteo corrente con cache migliorata"""
        location = location or self.default_location
        
        # Normalizza il nome della località per la cache
        location_normalized = location.strip().lower()
        cache_key = f"weather_current_{location_normalized.replace(' ', '_').replace(',', '_')}"
        
        logger.info(f"🌍 Richiesta meteo per: '{location}' (cache key: {cache_key})")
        
        # Controlla cache
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"📦 Weather data served from cache for {location}")
            # Aggiungi flag per indicare che viene dalla cache
            cached_data['from_cache'] = True
            cached_data['cache_key'] = cache_key
            return cached_data
            
        # Se non in cache, chiama API
        try:
            logger.info(f"🌐 Calling WeatherAPI for fresh data: {location}")
            data = self._fetch_current_weather(location)
            
            # Aggiungi metadati
            data['from_cache'] = False
            data['cache_key'] = cache_key
            data['requested_location'] = location
            
            # Salva in cache
            cache.set(cache_key, data, self.cache_timeout)
            logger.info(f"💾 Weather data cached for {location} (key: {cache_key})")
            
            return data
            
        except Exception as e:
            logger.error(f"Weather API error for {location}: {str(e)}")
            
            # Prova a restituire cache scaduta come fallback
            cached_data = cache.get(cache_key + '_backup')
            if cached_data:
                logger.warning(f"Serving stale weather data for {location}")
                cached_data['is_stale'] = True
                cached_data['from_cache'] = True
                return cached_data
                
            raise e

    # Aggiungi anche questo metodo per debug
    def clear_location_cache(self, location):
        """Cancella la cache per una località specifica"""
        location_normalized = location.strip().lower()
        cache_key = f"weather_current_{location_normalized.replace(' ', '_').replace(',', '_')}"
        
        # Cancella cache principale e backup
        cache.delete(cache_key)
        cache.delete(cache_key + '_backup')
        
        logger.info(f"🗑️ Cache cleared for location: {location} (key: {cache_key})")
        return cache_key

    def get_all_cached_locations(self):
        """Restituisce tutte le località in cache (per debug)"""
        # Questo funziona solo con alcuni backend di cache
        try:
            if hasattr(cache, '_cache'):
                all_keys = cache._cache.keys()
                weather_keys = [k for k in all_keys if k.startswith('weather_current_')]
                return weather_keys
        except:
            pass
        return []
    
    def _fetch_current_weather(self, location):
        """Chiamata diretta all'API WeatherAPI"""
        if not self.api_key:
            raise ValueError("WEATHER_API_KEY non configurata nelle impostazioni Django")
            
        url = f"{self.base_url}/current.json"
        params = {
            'key': self.api_key,
            'q': location,
            'lang': 'it',
            'aqi': 'no'
        }
        
        logger.info(f"Fetching weather data for {location}")
        
        response = requests.get(url, params=params, timeout=self.timeout)
        
        if response.status_code == 401:
            raise ValueError("API Key WeatherAPI non valida")
        elif response.status_code == 400:
            raise ValueError(f"Località '{location}' non trovata")
        elif response.status_code != 200:
            raise ValueError(f"Errore API WeatherAPI: {response.status_code}")
            
        data = response.json()
        
        # Arricchisci i dati con informazioni aggiuntive
        data['fetched_at'] = datetime.now().isoformat()
        data['is_stale'] = False
        
        # Salva backup per fallback
        cache_key = f"weather_current_{location.replace(' ', '_').replace(',', '_')}_backup"
        cache.set(cache_key, data, self.cache_timeout * 6)  # Backup per 1 ora
        
        return data
    
    def get_treatment_advice(self, weather_data):
        """Genera consigli per trattamenti basati sui dati meteo"""
        current = weather_data.get('current', {})
        
        wind_speed = current.get('wind_kph', 0)
        humidity = current.get('humidity', 0)
        temperature = current.get('temp_c', 0)
        is_day = current.get('is_day', 1)
        condition_code = current.get('condition', {}).get('code', 1000)
        
        # Logica consigli
        if wind_speed > 15:
            return {
                'text': 'Vento forte - Evitare trattamenti',
                'level': 'bad',
                'icon': 'fa-wind',
                'details': f'Vento a {wind_speed} km/h troppo forte per irrorazioni'
            }
        elif humidity > 85:
            return {
                'text': 'Umidità alta - Attendere condizioni migliori', 
                'level': 'warning',
                'icon': 'fa-tint',
                'details': f'Umidità al {humidity}% può ridurre efficacia'
            }
        elif temperature < 5 or temperature > 30:
            return {
                'text': 'Temperatura non ottimale per trattamenti',
                'level': 'warning', 
                'icon': 'fa-thermometer-half',
                'details': f'Temperatura di {temperature}°C non ideale'
            }
        elif not is_day:
            return {
                'text': 'Preferibile trattare durante le ore diurne',
                'level': 'warning',
                'icon': 'fa-moon',
                'details': 'Evitare trattamenti notturni quando possibile'
            }
        elif self._is_rain_condition(condition_code):
            return {
                'text': 'Condizioni di pioggia - Rimandare trattamenti',
                'level': 'bad',
                'icon': 'fa-cloud-rain',
                'details': 'Precipitazioni in corso o previste'
            }
        elif wind_speed < 5 and humidity < 70 and 10 <= temperature <= 25 and is_day:
            return {
                'text': 'Condizioni ideali per trattamenti',
                'level': 'good',
                'icon': 'fa-check-circle',
                'details': f'Vento: {wind_speed} km/h, Umidità: {humidity}%, Temp: {temperature}°C'
            }
        else:
            return {
                'text': 'Condizioni accettabili per trattamenti',
                'level': 'neutral',
                'icon': 'fa-info-circle',
                'details': 'Verificare condizioni locali prima del trattamento'
            }
    
    def _is_rain_condition(self, condition_code):
        """Verifica se il codice condizione indica pioggia"""
        rain_codes = [
            1063, 1150, 1153, 1168, 1171, 1180, 1183, 1186, 1189, 1192, 1195,
            1198, 1201, 1240, 1243, 1246, 1273, 1276
        ]
        return condition_code in rain_codes


    def _fetch_current_weather(self, location):
        """Chiamata diretta all'API WeatherAPI con debug località"""
        if not self.api_key:
            raise ValueError("WEATHER_API_KEY non configurata nelle impostazioni Django")
            
        url = f"{self.base_url}/current.json"
        params = {
            'key': self.api_key,
            'q': location,
            'lang': 'it',
            'aqi': 'no'
        }
        
        logger.info(f"🌍 Richiesta meteo per: '{location}'")
        logger.info(f"🔗 URL chiamata: {url}")
        logger.info(f"📋 Parametri: {params}")
        
        response = requests.get(url, params=params, timeout=self.timeout)
        
        if response.status_code == 401:
            raise ValueError("API Key WeatherAPI non valida")
        elif response.status_code == 400:
            logger.error(f"❌ Località '{location}' non trovata dalla API WeatherAPI")
            raise ValueError(f"Località '{location}' non trovata")
        elif response.status_code != 200:
            raise ValueError(f"Errore API WeatherAPI: {response.status_code}")
            
        data = response.json()
        
        # Debug: mostra cosa ha trovato l'API
        found_location = data.get('location', {})
        logger.info(f"✅ API ha trovato:")
        logger.info(f"   - Nome: {found_location.get('name')}")
        logger.info(f"   - Regione: {found_location.get('region')}")
        logger.info(f"   - Paese: {found_location.get('country')}")
        logger.info(f"   - Coordinate: {found_location.get('lat')}, {found_location.get('lon')}")
        
        # Arricchisci i dati con informazioni aggiuntive
        data['fetched_at'] = datetime.now().isoformat()
        data['is_stale'] = False
        data['requested_location'] = location
        
        # Salva backup per fallback
        cache_key_backup = f"weather_current_{location.replace(' ', '_').replace(',', '_')}_backup"
        cache.set(cache_key_backup, data, self.cache_timeout * 2)  # Cache backup più lunga
        
        return data

    def test_multiple_locations(self, locations_list):
        """Testa più località per capire cosa restituisce l'API"""
        results = {}
        
        for location in locations_list:
            try:
                logger.info(f"🧪 Test località: {location}")
                data = self._fetch_current_weather(location)
                
                found = data.get('location', {})
                results[location] = {
                    'success': True,
                    'found_name': found.get('name'),
                    'found_region': found.get('region'),
                    'found_country': found.get('country'),
                    'coordinates': f"{found.get('lat')}, {found.get('lon')}"
                }
                
            except Exception as e:
                results[location] = {
                    'success': False,
                    'error': str(e)
                }
                
        return results

    def debug_location_search(self, search_term):
        """Debug per capire come WeatherAPI interpreta le ricerche"""
        
        # Testa diverse varianti della località
        test_locations = [
            search_term,
            f"{search_term}, Italy",
            f"{search_term}, Piemonte",
            f"{search_term}, Piemonte, Italy",
            f"{search_term}, TO",
            f"{search_term}, Turin"
        ]
        
        logger.info(f"🔍 Debug ricerca località per: {search_term}")
        
        results = self.test_multiple_locations(test_locations)
        
        return results

# Istanza globale del servizio
weather_service = WeatherService()