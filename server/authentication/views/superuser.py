# authentication/views.py
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import timedelta
import random
from ..models import User
from django.core.mail import send_mail
from django.views import View
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string


class SuperuserLoginView(LoginView):
    template_name = "admin/login_superuser.html"

    def form_valid(self, form):
        user = form.get_user()

        if user.is_superuser:
            # Generate OTP
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_expiration = timezone.now() + timedelta(minutes=5)
            user.save(update_fields=["otp", "otp_expiration"])

            html_message = render_to_string('email/admin_otp_email.html', {'otp': otp})
            send_mail(
            'Your OTP Code',
            f'Your OTP code is {otp}',
            'infiniteloops69@gmail.com',
            [user.email],
            fail_silently=False,
            html_message=html_message,
        )

            # Store user id in session (password already verified)
            self.request.session["pending_superuser_id"] = user.id
            return redirect("admin_otp_verify")

        return super().form_valid(form)


class SuperuserOTPVerifyView(View):
    template_name = "admin/otp_verify.html"

    def get(self, request):
        if "pending_superuser_id" not in request.session:
            return redirect("admin:login")  # agar direct aaya
        return render(request, self.template_name)

    def post(self, request):
        user_id = request.session.get("pending_superuser_id")
        otp_entered = request.POST.get("otp")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponseForbidden("Invalid session.")

        if user.otp == otp_entered and user.otp_expiration > timezone.now():
            # OTP sahi hai → session cleanup + login
            del request.session["pending_superuser_id"]
            from django.contrib.auth import login
            login(request, user)
            return redirect("/admin/")

        return render(request, self.template_name, {"error": "Invalid or expired OTP"})
