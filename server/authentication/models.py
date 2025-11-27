from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
# from .managers import CustomUserManager
from django.utils import timezone
from .managers import CustomUserManager
class User(AbstractBaseUser,PermissionsMixin):
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=500) 
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expiration = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)  
    is_staff = models.BooleanField(default=False)  
    date_joined = models.DateTimeField(default=timezone.now)  
    is_superuser = models.BooleanField(default=False)
    aadhar_number = models.CharField(max_length=14, default= False, null=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    is_doctor = models.BooleanField(default=False)
    is_medical_store = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    objects = CustomUserManager()
    def __str__(self):
        return self.email
    
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('password_reset', 'Password Reset'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email if self.user else 'Unknown'} - {self.action} at {self.timestamp}"

