from rest_framework import permissions, viewsets, filters, status
from rest_framework.decorators import action
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Prefetch, F
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Shop, Category, Product, ProductInfo,
    Contact, Order, OrderItem,
)
from .serializers import (
    ShopSerializer, CategorySerializer,
    ProductSerializer, ContactSerializer,
    OrderSerializer, BasketAddSerializer,
)

class ProductViewSet(viewsets.ReadOnlyModelViewSet): # Каталог товаров с фильтрацией и поиском. Доступен без авторизации.
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'category__name']
    
    def get_queryset(self):
        params = self.request.query_params
        shop_id = params.get('shop_id')
        price_min = params.get('price_min')
        price_max = params.get('price_max')
        in_stock = params.get('in_stock')

        # queryset для вложенных product_infos
        product_infos_qs = ProductInfo.objects.select_related('shop')
        if shop_id:
            product_infos_qs = product_infos_qs.filter(shop_id=shop_id)
        if price_min:
            product_infos_qs = product_infos_qs.filter(price__gte=price_min)
        if price_max:
            product_infos_qs = product_infos_qs.filter(price__lte=price_max)
        if in_stock == 'true':
            product_infos_qs = product_infos_qs.filter(quantity__gt=0)
        
        # queryset с prefetch
        qs = Product.objects.prefetch_related(
            Prefetch('product_infos', queryset=product_infos_qs),
            'category',
        )

        # фильтры применяем к Product — чтобы не было товаров с пустым product_infos
        if shop_id:
            qs = qs.filter(product_infos__shop_id=shop_id)
        if price_min:
            qs = qs.filter(product_infos__price__gte=price_min)
        if price_max:
            qs = qs.filter(product_infos__price__lte=price_max)
        if in_stock == 'true':
            qs = qs.filter(product_infos__quantity__gt=0)

        return qs.distinct()


class CategoryViewSet(viewsets.ReadOnlyModelViewSet): # Список категорий. Доступен без авторизации
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ShopViewSet(viewsets.ReadOnlyModelViewSet): # Список активных магазинов. Доступен без авторизации
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    permission_classes = [permissions.AllowAny]


class ContactViewSet(viewsets.ModelViewSet): # CRUD контактов текущего пользователя
    serializer_class = ContactSerializer 
    
    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



class BasketView(viewsets.ViewSet): # Корзина пользователя
    permission_classes = [permissions.IsAuthenticated]

    def _get_basket(self, user): # Возвращает корзину пользователя, создавая её при необходимости
        basket, _ = Order.objects.get_or_create(
            user=user, status=Order.Status.NEW,
        )
        return basket

    def list(self, request): # GET /basket/ текущая корзина
        basket = self._get_basket(request.user)
        return Response(OrderSerializer(basket).data)

    def create(self, request): # POST /basket/ добавить товар
        serializer = BasketAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_info_id = serializer.validated_data['product_info_id']
        quantity = serializer.validated_data['quantity']

        product_info = ProductInfo.objects.filter(id=product_info_id).first()
        if product_info is None:
            return Response(
                {'error': 'Товар не найден'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not product_info.is_available:
            return Response(
                {'error': 'Товар недоступен'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        basket = self._get_basket(request.user)

        existing = OrderItem.objects.filter(
            order=basket, product_info=product_info,).first()
        already = existing.quantity if existing else 0

        if already + quantity > product_info.quantity:
            return Response(
                {'error': f'На складе только {product_info.quantity} шт. '
                        f'(в корзине уже {already})'},
                status=400,
        )

        item, created = OrderItem.objects.get_or_create(
            order=basket,
            product_info=product_info,
            defaults={'quantity': quantity},
        )
        if not created:
            OrderItem.objects.filter(pk=item.pk).update(
                quantity=F('quantity') + quantity,
            )

        basket.refresh_from_db()
        return Response(OrderSerializer(basket).data)

    @action(detail=False, methods=['delete']) # DELETE /basket/remove_item/?item_id=<int> удалить позицию
    def remove_item(self, request):
        basket = self._get_basket(request.user)
        item_id = request.query_params.get('item_id')

        deleted, _ = OrderItem.objects.filter(
            id=item_id, order=basket,
        ).delete()

        if not deleted:
            return Response(
                {'error': 'Позиция не найдена'},
                status=status.HTTP_404_NOT_FOUND,
            )

        basket.refresh_from_db()
        return Response(OrderSerializer(basket).data)


class OrderViewSet(viewsets.ReadOnlyModelViewSet): # Заказы пользователя
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = Order.objects.exclude(status=Order.Status.NEW).prefetch_related(
            'items__product_info__product',
            'items__product_info__shop',
        )
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs

    @action(detail=True, methods=['post']) # POST /orders/{pk}/confirm/ подтвердить заказ 
    def confirm(self, request, pk=None):
        try:
            order = Order.objects.get(
                id=pk, user=request.user, status=Order.Status.NEW,
            )
        except Order.DoesNotExist:
            return Response(
                {'error': 'Корзина не найдена'},
                status=status.HTTP_404_NOT_FOUND,
            )

        contact_id = request.data.get('contact_id')
        contact, error = self._validate_order(order, contact_id, request.user)
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        order.contact = contact
        order.status = Order.Status.CONFIRMED
        order.save()

        self._send_emails(order, contact)
        return Response(OrderSerializer(order).data)


    @action(detail=True,methods=['post'],permission_classes=[permissions.IsAdminUser],)
    def set_status(self, request, pk=None): # POST /orders/{pk}/set_status/ смена статуса админом
        order = self.get_object()
        new_status = request.data.get('status')

        valid = [c[0] for c in Order.Status.choices]
        if new_status not in valid:
            return Response({'error': f'Допустимые: {valid}'}, status=400)

        if order.status == Order.Status.NEW:
            return Response({'error': 'Нельзя менять статус корзины'}, status=400)
        if new_status == Order.Status.NEW:
            return Response({'error': 'Нельзя вернуть в статус "Новый"'}, status=400)
        if order.status in (Order.Status.DELIVERED, Order.Status.CANCELED):
            return Response(
                {'error': f'Заказ уже в финальном статусе: {order.get_status_display()}'},
                status=400,
            )

        old = order.get_status_display()
        order.status = new_status
        order.save(update_fields=['status'])
        self._send_status_email(order, old)
        return Response(OrderSerializer(order).data)


    @staticmethod
    def _send_status_email(order, old_status): # Письмо клиенту об изменении статуса заказа
        if not order.user.email:
            return

        send_mail(
            subject=f'Статус заказа №{order.id} изменён',
            message=(
                f'Статус вашего заказа изменён.\n'
                f'Было: {old_status}\n'
                f'Стало: {order.get_status_display()}\n'
                f'Сумма заказа: {order.total_sum} руб.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=True,
        )


    @staticmethod
    def _validate_order(order, contact_id, request_user): # Проверка заказа перед подтверждением
        if not contact_id:
            return None, 'contact_id обязателен'
        
        contact = Contact.objects.filter(id=contact_id, user=request_user).first()
        if contact is None:
            return None, 'Контакт не найден'

        if contact.type != Contact.Type.ADDRESS:
            return None, 'Для доставки нужен адрес, а не телефон'

        if not order.items.exists():
            return None, 'Корзина пуста'

        for item in order.items.all():
            if not item.product_info.is_available:
                return None, f'Товар «{item.product_info.product.name}» недоступен'
            if item.quantity > item.product_info.quantity:
                return None, (
                    f'Товара «{item.product_info.product.name}» не хватает '
                    f'(заказано {item.quantity}, в наличии {item.product_info.quantity})'
                )
        return contact, None

    @staticmethod
    def _send_emails(order, contact): # Письма при подтверждении заказа: клиенту и админу
        if not order.user.email:
            return
        if not settings.ADMIN_EMAIL:
            return
        
        send_mail(
            subject=f'Заказ №{order.id} подтверждён',
            message=(
                f'Ваш заказ на сумму {order.total_sum} руб. принят.\n'
                f'Контакт: {contact}'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=True,
        )
        send_mail(
            subject=f'Новый заказ №{order.id}',
            message=(
                f'Поступил новый заказ от {order.user.username}.\n'
                f'Сумма: {order.total_sum} руб.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )