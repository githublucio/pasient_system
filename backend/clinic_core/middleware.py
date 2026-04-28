import time
import threading
from collections import defaultdict

from django.utils import translation
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from administration.models import AuditLog

class DefaultTetumMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If no language is explicitly set via session or cookie, default to 'tet'
        language = request.session.get('django_language') or request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        
        if not language:
            # Check if current path already has a language prefix
            # If not, and it's not a static/media/admin path, we could force tet
            # However, standard LocaleMiddleware should handle i18n_patterns.
            pass
            
        response = self.get_response(request)
        return response

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We can attach the request to a thread-local if we want to log internal model changes with the user
        # But for basics, we track login/logout below via signals
        response = self.get_response(request)
        return response

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        action='LOGIN',
        module='AUTH',
        ip_address=get_client_ip(request),
        object_repr=f"User {user.username} logged in"
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        AuditLog.objects.create(
            user=user,
            action='LOGOUT',
            module='AUTH',
            ip_address=get_client_ip(request),
            object_repr=f"User {user.username} logged out"
        )


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https://images.unsplash.com https://*.render.com https://unpkg.com; "
            "connect-src 'self' https://unpkg.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(self), microphone=(self), geolocation=()'
        return response


class LoginRateLimitMiddleware:
    """Rate limit login attempts to prevent brute force attacks."""
    
    _lock = threading.Lock()
    _attempts = defaultdict(list)  # ip -> [timestamps]
    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 300  # 5 minutes
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/accounts/login/' and request.method == 'POST':
            ip = get_client_ip(request)
            now = time.time()
            
            with self._lock:
                # Clean old attempts
                self._attempts[ip] = [t for t in self._attempts[ip] if now - t < self.WINDOW_SECONDS]
                
                if len(self._attempts[ip]) >= self.MAX_ATTEMPTS:
                    from django.http import HttpResponse
                    return HttpResponse(
                        '<h3>Too many login attempts. Please try again in 5 minutes.</h3>',
                        status=429,
                        content_type='text/html'
                    )
                
                self._attempts[ip].append(now)
        
        response = self.get_response(request)
        
        # If login was successful, clear attempts
        if request.path == '/accounts/login/' and request.method == 'POST':
            if hasattr(request, 'user') and request.user.is_authenticated:
                ip = get_client_ip(request)
                with self._lock:
                    self._attempts.pop(ip, None)
        
        return response
