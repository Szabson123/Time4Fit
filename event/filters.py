import django_filters
from .models import Event
from decimal import Decimal
from django.db.models import Q

class EventListFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search')
    is_free = django_filters.BooleanFilter(method='filter_is_free')

    def filter_search(self, queryset, name, value):
        words = value.split()

        q = Q()
        for word in words:
            q |= Q(title__icontains=word)
            q |= Q(category__name__icontains=word)

        return queryset.filter(q).distinct()

    def filter_is_free(self, queryset, name, value):
        if value:
            return queryset.filter(additional_info__price=0)
        return queryset.exclude(additional_info__price=0)

    class Meta:
        model = Event
        fields = ['search', 'is_free']