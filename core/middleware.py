try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

class TimezoneMiddleware(MiddlewareMixin):
    """Automatically set timezone based on user preference"""
    
    def process_request(self, request):
        if PYTZ_AVAILABLE and request.user.is_authenticated:
            try:
                user_timezone = request.user.timezone
                timezone.activate(pytz.timezone(user_timezone))
            except:
                timezone.deactivate()
        else:
            timezone.deactivate()