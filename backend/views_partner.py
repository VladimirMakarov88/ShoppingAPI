from pathlib import Path
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Shop, Order, User
from .serializers import ShopSerializer, OrderSerializer
from .services import import_yaml_file


class IsShopUser(permissions.BasePermission):
    # Разрешение только для пользователей с type='shop'
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.type == User.Type.SHOP
        )


class PartnerShopView(viewsets.ModelViewSet):
    # Управление магазином поставщика
    serializer_class = ShopSerializer
    permission_classes = [IsShopUser]

    def get_queryset(self):
        return Shop.objects.filter(user=self.request.user)

    @action(detail=False, methods=['patch'])
    
    def toggle_state(self, request):
        # PATCH /api/v1/partner/shop/toggle_state/ — вкл/выкл приём заказов.
        shop = self.get_queryset().first()
        if not shop:
            return Response({'error': 'У вас нет магазина'}, status=404)
        shop.state = not shop.state
        shop.save(update_fields=['state'])
        return Response(ShopSerializer(shop).data)


class PartnerUpdateView(viewsets.ViewSet):
    # Импорт прайса поставщиком через API
    permission_classes = [IsShopUser]

    def create(self, request):
        # POST /api/v1/partner/update/ с {"file_path": "data/shop1.yaml"}
        file_path = request.data.get('file_path')
        if not file_path:
            return Response({'error': 'file_path обязателен'}, status=400)

        try:
            stats = import_yaml_file(Path(file_path), shop_user=request.user)
        except FileNotFoundError as e:
            return Response({'error': str(e)}, status=404)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)

        return Response({'Status': True, **stats}, status=201)


class PartnerOrderViewSet(viewsets.ReadOnlyModelViewSet):
    # Заказы, содержащие товары магазина поставщика
    serializer_class = OrderSerializer
    permission_classes = [IsShopUser]

    def get_queryset(self):
        return Order.objects.filter(
            items__product_info__shop__user=self.request.user,
        ).exclude(status=Order.Status.NEW).distinct()