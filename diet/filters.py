from rest_framework.filters import BaseFilterBackend
from django.db.models import Q
from .models import Allergen 

class SmartHybridSearchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search_param = request.query_params.get('search', '')
        
        if not search_param:
            return queryset
        
        terms = [term.strip() for term in search_param.replace(',', ' ').split() if term.strip()]
        
        if not terms:
            return queryset
        
        include_fields = ['title', 'category__name', 'barcode']

        for term in terms:
            is_allergen = Allergen.objects.filter(name__icontains=term).exists()

            if is_allergen:
                queryset = queryset.exclude(allergens__name__icontains=term)
            else:
                term_query = Q()
                for field in include_fields:
                    lookup = f"{field}__icontains"
                    term_query |= Q(**{lookup: term})
                
                queryset = queryset.filter(term_query)

        return queryset.distinct()