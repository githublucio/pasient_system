from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', _('Create')),
        ('UPDATE', _('Update')),
        ('DELETE', _('Delete')),
        ('LOGIN', _('Login')),
        ('LOGOUT', _('Logout')),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    module = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=255, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    changes = models.JSONField(null=True, blank=True) # Diff of changes

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        indexes = [
            models.Index(fields=['-timestamp'], name='idx_audit_ts'),
            models.Index(fields=['user', '-timestamp'], name='idx_audit_user_ts'),
            models.Index(fields=['module', '-timestamp'], name='idx_audit_module_ts'),
        ]

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action} - {self.module}"
