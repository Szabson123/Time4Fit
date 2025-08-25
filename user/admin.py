from django.contrib import admin
from .models import CentralUser


@admin.register(CentralUser)
class CentralUserAdmin(admin.ModelAdmin):
    list_display = ("email", "date_joined", "is_active", "is_staff", "is_superuser")
    readonly_fields = ("password",)
    search_fields = ("email",)
    list_filter = ("is_active", "is_staff", "is_superuser")
    ordering = ("-date_joined",)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if "password" in fields:
            fields.remove("password")
        return fields