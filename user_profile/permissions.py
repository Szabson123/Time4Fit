from rest_framework.permissions import BasePermission


class OnlyOwnerOfProfileCanModify(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.profile.user == request.user
    
class OnlyOnwerOfTrainerProfile(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.trainerprofile.profile.user == request.user