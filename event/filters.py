import django_filters
from .models import Event
from decimal import Decimal

class EventListFilter(django_filters.FilterSet):
    is_free = django_filters.BooleanFilter(method='filter_is_free')

    def filter_is_free(self, queryset, name, value):
        if value:
            return queryset.filter(additional_info__price=0)
        return queryset.exclude(additional_info__price=0)
    
    class Meta:
        model = Event
        fields = ['is_free', 'title']