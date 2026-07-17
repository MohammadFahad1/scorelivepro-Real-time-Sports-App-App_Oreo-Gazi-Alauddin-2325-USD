from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from .models import FanProfile, AdminProfile, OneTimePassword, UserActivity

User = get_user_model()

class FanProfileInline(admin.StackedInline):
    model = FanProfile
    can_delete = False
    verbose_name_plural = 'Fan Profile'
    fk_name = 'user'

class AdminProfileInline(admin.StackedInline):
    model = AdminProfile
    can_delete = False
    verbose_name_plural = 'Admin Profile'
    fk_name = 'user'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    readonly_fields = ('date_joined', 'last_login')

    list_display = ('email', 'first_name', 'last_name', 'get_role', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('groups', 'is_staff', 'is_active', 'date_joined')
    
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'profile_image')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        if obj.groups.filter(name='Admin').exists():
            return [AdminProfileInline(self.model, self.admin_site)]
        return [FanProfileInline(self.model, self.admin_site)]

    def get_role(self, obj):
        if obj.groups.filter(name='Admin').exists():
            return 'Admin'
        return 'Fan'
    get_role.short_description = 'Role'

@admin.register(OneTimePassword)
class OneTimePasswordAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('otp', 'created_at')

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__email', 'details', 'ip_address')
    readonly_fields = ('user', 'action', 'details', 'ip_address', 'timestamp')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser