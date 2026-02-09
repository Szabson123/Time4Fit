from decimal import Decimal, ROUND_HALF_UP
from .models import Product

class ProductService:
    @staticmethod
    def normalize_to_1g(value: Decimal, total_mass: Decimal) -> Decimal:
        if not total_mass or total_mass <= 0:
            return Decimal('0.00000')
        return (value / total_mass).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP)

    @classmethod
    def create_product(cls, user, validated_data):
        label_type = validated_data.get('label_type')
        
        divider = Decimal('100.00') if label_type == 'EU' else validated_data.get('packaging_size')

        fields_to_normalize = ['kcal', 'protein', 'fat', 'carbohydrates']
        
        for field in fields_to_normalize:
            raw_value = validated_data.pop(field, Decimal('0'))
            validated_data[f'{field}_1g'] = cls.normalize_to_1g(raw_value, divider)
        
        if label_type == 'US':
            sodium_mg = validated_data.pop('sodium_salt', Decimal('0')) 
            salt_g = (sodium_mg / Decimal('1000')) * Decimal('2.5')
        else:
            salt_g = validated_data.pop('sodium_salt', Decimal('0'))
            
        validated_data['salt_1g'] = cls.normalize_to_1g(salt_g, divider)

        return Product.objects.create(user=user, **validated_data)
