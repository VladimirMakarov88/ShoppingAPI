from django.db import models
from django.contrib.auth.models import User


class Shop(models.Model): # Магазин в системе

    name = models.CharField(max_length=100, verbose_name='Название')
    url = models.URLField(null=True, blank=True, verbose_name='Ссылка')
    filename = models.CharField(max_length=255, null=True, blank=True, verbose_name='Импортируемый файл')
    state = models.BooleanField(default=True, verbose_name='Прием заказов')

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Category(models.Model): # Категория товаров

    name = models.CharField(max_length=100, verbose_name='Наименование')
    shops = models.ManyToManyField(Shop, related_name='categories', blank=True, verbose_name='Магазины')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ('name',)
    
    def __str__(self):
        return self.name


class Product(models.Model): # Карточка товара без привязок к магазину
    
    name = models.CharField(max_length=200, verbose_name='Наименование')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Категория')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ('name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model): # Товар в конкретном магазине

    foreign_id = models.PositiveBigIntegerField(verbose_name='Внешний ID товара')
    model = models.CharField(max_length=100, blank=True, verbose_name='Артикул')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    recommended_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Рекомендованная цена')
    quantity = models.PositiveBigIntegerField(verbose_name='Количество')
    characteristics = models.JSONField(
        default=dict, blank=True,
        verbose_name='Характеристики',
        help_text='Настраиваемые поля',
    )
     
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_infos', verbose_name='Товар')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='product_infos', verbose_name='Магазин')

    class Meta:
        verbose_name = 'Информация о товаре'
        verbose_name_plural = 'Информация о товарах'
        unique_together = ('product', 'shop', 'foreign_id') # Протектимся ЗДЕСЬ от дублей при допустим очередном импорте YAML

    def __str__(self):
        return f'{self.product.name} — {self.shop.name} ({self.price} руб)'

    @property
    def is_available(self): # Можно ли заказать товар
        return self.quantity > 0 and self.shop.state


class Contact(models.Model): # Контакты пользователя
    class Type(models.TextChoices):
        PHONE = 'phone', 'Телефон'
        ADDRESS = 'address', 'Адрес'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts', verbose_name='Пользователь')
    type = models.CharField(max_length=10, choices=Type.choices, verbose_name='Тип')

    city = models.CharField(max_length=100, blank=True, verbose_name='Город')
    street = models.CharField(max_length=100, blank=True, verbose_name='Улица')
    house = models.CharField(max_length=100, blank=True, verbose_name='Дом')
    building = models.CharField(max_length=10, blank=True, verbose_name='Корпус')
    structure = models.CharField(max_length=10, blank=True, verbose_name='Строение')
    apartment = models.CharField(max_length=100, blank=True, verbose_name='Квартира')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'
        ordering = ('-id',)

    def __str__(self):
        if self.type == self.Type.PHONE:
            return f'{self.user.username}: {self.phone}'
        return f'{self.user.username}: {self.city}, {self.street} {self.house} {self.apartment}'


class Order(models.Model): # Заказ пользователя
    class Status(models.TextChoices):
        NEW = 'new_order', 'Новый заказ'
        CONFIRMED = 'confirmed', 'Подтвержден'
        PACKED = 'packed', 'Собран'
        SENT = 'sent', 'Отправлен'
        DELIVERED = 'delivered', 'Доставлен'
        CANCELED = 'canceled', 'Отменен'


    user = models.ForeignKey(User, on_delete=models.CASCADE,
        related_name='orders', verbose_name='Пользователь')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    status = models.CharField(max_length=20, choices=Status.choices,
        default=Status.NEW, verbose_name='Статус')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Контакт')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ('-created_at',)

    def __str__(self):
        return f'Заказ №{self.id} от {self.user.username} [{self.status}]'

    @property
    def total_sum(self): # Общая сумма заказа
        return sum(item.sum for item in self.items.all())


class OrderItem(models.Model): # Позиция заказа. Здесь конкретный товар в магазине и его конкретне количество

    quantity = models.PositiveIntegerField(verbose_name='Количество')
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
        related_name='items', verbose_name='Заказ')
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE,
        verbose_name='Информация о товаре')
    
    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов' 
        # Один товар в заказе будет одна строка. При повторном добавлении увеличиться quantity
        unique_together = ('order', 'product_info')

    def __str__(self):
        return f'{self.product_info.product.name} × {self.quantity}'

    @property
    def sum(self):
        return self.product_info.price * self.quantity