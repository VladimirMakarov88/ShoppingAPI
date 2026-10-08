from django.contrib import admin

from .models import Shop, Category, Product, ProductInfo, Contact, Order, OrderItem


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'state', 'url')
    list_filter = ('state',)
    search_fields = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    filter_horizontal = ('shops',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'shop', 'price', 'quantity')
    list_filter = ('shop', 'product__category')
    search_fields = ('product__name', 'model')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'city', 'phone')
    list_filter = ('type',)
    search_fields = ('user__username', 'phone')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_info', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'status', 'contact')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product_info', 'quantity')
    list_filter = ('order__status',)