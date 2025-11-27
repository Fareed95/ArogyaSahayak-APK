from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AuditLog


# ✅ Register User model in admin
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2'),
        }),
    )


# ✅ Register AuditLog model in admin
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    list_filter = ('action', 'user')
    search_fields = ('user__email', 'user__name', 'ip_address')
    ordering = ('-timestamp',)


# ✅ Admin branding
admin.site.site_header = "Arogya Sahayak Administrator"
admin.site.site_title = "Arogya Sahayak Admin Portal"
admin.site.index_title = "Welcome to Arogya Sahayak Admin Dashboard"
admin.site.site_footer = "This inventory system is proudly made by Crodlin Technology"
