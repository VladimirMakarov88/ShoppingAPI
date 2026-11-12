from rest_framework import serializers
from .models import Shop, Category, Product, ProductInfo, Contact, Order, OrderItem


class ShopSerializer(serializers.ModelSerializer): # Сериализатор магазина
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state')


class CategorySerializer(serializers.ModelSerializer): # Сериализатор категории
    class Meta:
        model = Category
        fields = ('id', 'name')


class ProductInfoSerializer(serializers.ModelSerializer): # Сериализатор предложения товара в магазине
    shop = ShopSerializer(read_only=True)
    class Meta:
        model = ProductInfo
        fields = ('id', 'shop', 'price', 'recommended_price',
            'quantity', 'characteristics', 'model',)


class ProductSerializer(serializers.ModelSerializer): # Сериализатор товара
    product_infos = ProductInfoSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'product_infos')


class ContactSerializer(serializers.ModelSerializer): # Сериализатор контакта
    
    MAX_ADDRESSES = 5
    
    class Meta:
        model = Contact
        fields = (
            'id', 'type', 'city', 'street', 'house',
            'building', 'structure', 'apartment', 'phone',
        )
        read_only_fields = ('id',)
     

    def validate(self, attrs):
        contact_type = attrs.get('type', getattr(self.instance, 'type', None))
        user = self.context['request'].user
        
        if contact_type == Contact.Type.PHONE:
            phone = attrs.get('phone', getattr(self.instance, 'phone', ''))
            if not phone:
                raise serializers.ValidationError(
                    {'phone': 'Телефон обязателен'}
                )
        elif contact_type == Contact.Type.ADDRESS:
            city = attrs.get('city', getattr(self.instance, 'city', ''))
            street = attrs.get('street', getattr(self.instance, 'street', ''))
            house = attrs.get('house', getattr(self.instance, 'house', ''))
            if not all([city, street, house]):
                raise serializers.ValidationError(
                    {'city': 'Для адреса обязательны: город, улица, дом'}
                )

        if contact_type == Contact.Type.PHONE:
            qs = Contact.objects.filter(user=user, type=Contact.Type.PHONE)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    'У пользователя может быть только один телефон'
                )
        elif contact_type == Contact.Type.ADDRESS:
            qs = Contact.objects.filter(user=user, type=Contact.Type.ADDRESS)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.count() >= self.MAX_ADDRESSES:
                raise serializers.ValidationError(
                    f'Не более {self.MAX_ADDRESSES} адресов'
                )
        return attrs


class OrderItemSerializer(serializers.ModelSerializer): # Сериализатор позиции заказа
    product_info = ProductInfoSerializer(read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'total')

    def get_total(self, obj):
        return obj.sum


class OrderSerializer(serializers.ModelSerializer): # Сериализатор заказа
    items = OrderItemSerializer(many=True, read_only=True)
    total_sum = serializers.SerializerMethodField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'created_at', 'status', 'items', 'total_sum', 'contact',)

    def get_total_sum(self, obj):
        return obj.total_sum


class BasketAddSerializer(serializers.Serializer): # Входные данные для добавления товара в корзину. Валидируем только входные данные, без привязки к модели
    product_info_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)