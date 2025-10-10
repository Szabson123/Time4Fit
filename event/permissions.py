from rest_framework import permissions

class IsEventAuthor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.event.author == request.user