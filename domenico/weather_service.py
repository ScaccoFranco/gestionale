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
        self.default_location = getattr(settings, 'WEATHER_LOCATION', 'Roatto, Piemonte, Italy')
        self.cache_timeout = 600  # 10 minuti
        self.timeout = 10  # 10 secondi timeout
        
    def get_current_weather(self, location=None):
        """Ottiene il meteo corrente con cache"""
        location = location or self.default_location
        cache_key = f"weather_current_{location.replace(' ', '_').replace(',', '_')}"
        
        # Controlla cache
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Weather data served from cache for {location}")
            return cached_data
            
        # Se non in cache, chiama API
        try:
            data = self._fetch_current_weather(location)
            
            # Salva in cache
            cache.set(cache_key, data, self.cache_timeout)
            logger.info(f"Weather data cached for {location}")
            
            return data
            
        except Exception as e:
            logger.error(f"Weather API error for {location}: {str(e)}")
            
            # Prova a restituire cache scaduta come fallback
            cached_data = cache.get(cache_key + '_backup')
            if cached_data:
                logger.warning(f"Serving stale weather data for {location}")
                cached_data['is_stale'] = True
                return cached_data
                
            raise e
    
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

# Istanza globale del servizio
weather_service = WeatherService()