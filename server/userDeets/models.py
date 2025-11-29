from django.db import models
from authentication.models import User

class UserDeets(models.Model):
    userid = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, related_name="user_details", on_delete=models.CASCADE)
    username = models.CharField(max_length=50)
    phoneNo = models.CharField(max_length=14, blank=True, null=True)  
    email =models.EmailField()
    address = models.TextField(blank=True, null=True, help_text="User's address (optional)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fcm_token=models.TextField(null=True,blank=True)
    def __str__(self):
        return f"{self.username} ({self.user.email})"

    
class Medicine(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medicines')
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    manufacturer = models.CharField(max_length=100, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

class Dose(models.Model):
    dose_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    dose_time = models.TimeField(auto_now=False, auto_now_add=False)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='doses')

    def __str__(self):
        return self.dose_name
