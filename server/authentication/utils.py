# authentication/utils.py
import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings

def generate_and_send_otp(user):
    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.otp_expiration = timezone.now() + timedelta(minutes=5)
    user.save(update_fields=["otp", "otp_expiration"])

    send_mail(
        "Your Admin Panel OTP",
        f"Your OTP is {otp}. It will expire in 5 minutes.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
