from modeltranslation.translator import register, TranslationOptions
from .models import Packaging, ProductCategory, DishCategory, DietType

@register(Packaging)
class PackagingTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(ProductCategory)
class ProductCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(DishCategory)
class DishCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(DietType)
class DietTypeTranslationOptions(TranslationOptions):
    fields = ('name',)

