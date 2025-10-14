from rest_framework.permissions import BasePermission

class IsEventAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.event.author == request.user
    

class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True

        return obj.author == request.user