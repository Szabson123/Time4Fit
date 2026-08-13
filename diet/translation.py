from modeltranslation.translator import TranslationOptions, register
from .models import Product, ProductServingUnit


@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ('package_name',)

