import yaml
from pathlib import Path
from django.db import transaction
from .models import Shop, Category, Product, ProductInfo


NON_CHARACTERISTIC_FIELDS = {
    'id', 'category', 'model', 'name',
    'price', 'price_rrc', 'quantity', 'parameters',
}


def import_yaml_file(file_path: Path, shop_user=None):
    # Импорт товаров из YAML
    if not file_path.exists():
        raise FileNotFoundError(f'Файл не найден: {file_path}')

    data = yaml.safe_load(file_path.read_text(encoding='utf-8'))
    if not data:
        raise ValueError('Файл пуст или не является YAML')

    shop_name = data.get('shop')
    if not shop_name:
        raise ValueError('В YAML отсутствует поле "shop"')

    with transaction.atomic():
        defaults = {'filename': str(file_path), 'state': True}
        if shop_user:
            defaults['user'] = shop_user

        shop, _ = Shop.objects.get_or_create(name=shop_name, defaults=defaults)

        # Если магазин уже был, то привязываем владельца, если его нет
        if shop_user and not shop.user:
            shop.user = shop_user
            shop.save(update_fields=['user'])

        # Категории
        categories_map = {}
        for cat in data.get('categories', []):
            category, _ = Category.objects.update_or_create(
                id=cat['id'], defaults={'name': cat['name']},
            )
            category.shops.add(shop)
            categories_map[cat['id']] = category

        # Товары
        created, updated = 0, 0
        for item in data.get('goods', []):
            category = categories_map.get(item['category'])
            if not category:
                continue

            product, _ = Product.objects.get_or_create(
                name=item['name'], category=category,
            )

            # Характеристики = parameters + все нестандартные поля
            characteristics = {
                k: v for k, v in item.items()
                if k not in NON_CHARACTERISTIC_FIELDS
            }
            characteristics.update(item.get('parameters', {}))

            _, is_created = ProductInfo.objects.update_or_create(
                product=product, shop=shop, foreign_id=item['id'],
                defaults={
                    'model': item.get('model', ''),
                    'price': item['price'],
                    'recommended_price': item['price_rrc'],
                    'quantity': item['quantity'],
                    'characteristics': characteristics,
                },
            )
            created += is_created
            updated += not is_created

    return {
        'shop': shop.name,
        'created': created,
        'updated': updated,
        'total': created + updated,
    }