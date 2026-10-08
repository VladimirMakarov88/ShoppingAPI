from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, CategoryViewSet, ShopViewSet,
    ContactViewSet, BasketView, OrderViewSet,
)

router = DefaultRouter()

router.register('products', ProductViewSet, basename='products')
router.register('categories', CategoryViewSet, basename='categories')
router.register('shops', ShopViewSet, basename='shops')
router.register('contacts', ContactViewSet, basename='contacts')
router.register('basket', BasketView, basename='basket')
router.register('orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls)),
]