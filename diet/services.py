from decimal import Decimal, ROUND_HALF_UP
from .models import Product

class ProductService:
    @staticmethod
    def normalize_to_1g(value: Decimal, total_mass: Decimal) -> Decimal:
        if not total_mass or total_mass <= 0:
            return Decimal('0.00000')
        return (value / total_mass).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP)

    @classmethod
    def _prepare_nutrition_data(cls, data, label_type, packaging_size):
        divider = Decimal('100.00') if label_type == 'EU' else packaging_size
        
        fields = ['kcal', 'protein', 'fat', 'carbohydrates']
        
        for field in fields:
            if field in data:
                raw_value = data.pop(field)
                data[f'{field}_1g'] = cls.normalize_to_1g(raw_value, divider)
        
        if 'sodium_salt' in data:
            raw_sodium_salt = data.pop('sodium_salt')
            if label_type == 'US':
                salt_g = (raw_sodium_salt / Decimal('1000')) * Decimal('2.5')
            else:
                salt_g = raw_sodium_salt
            
            data['salt_1g'] = cls.normalize_to_1g(salt_g, divider)

        return data

    @classmethod
    def create_product(cls, user, validated_data):
        label_type = validated_data.get('label_type')
        packaging_size = validated_data.get('packaging_size')
        
        processed_data = cls._prepare_nutrition_data(validated_data, label_type, packaging_size)
        return Product.objects.create(user=user, **processed_data)

    @classmethod
    def update_product(cls, instance, validated_data):
        label_type = validated_data.get('label_type', instance.label_type)
        packaging_size = validated_data.get('packaging_size', instance.packaging_size)

        processed_data = cls._prepare_nutrition_data(validated_data, label_type, packaging_size)

        for attr, value in processed_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance