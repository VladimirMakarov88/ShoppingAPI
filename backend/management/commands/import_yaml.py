import yaml
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from backend.models import Shop, Category, Product, ProductInfo


# Поля YAML, которые НЕ идут в characteristics
STANDARD_FIELDS = {
    'id', 'category', 'model', 'name',
    'price', 'price_rrc', 'quantity',
}


NO_CHARACTERISTIC_FIELDS = STANDARD_FIELDS | {'parameters'}


class Command(BaseCommand):
    help = 'Импорт из YAML-файла'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            type=str,
            help='Путь к YAML-файлу',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        if not file_path.exists():
            raise CommandError(f'Файл не найден: {file_path}')

        with open(file_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            raise CommandError('Файл пуст или не является YAML')

        shop_name = data.get('shop')
        if not shop_name:
            raise CommandError('В YAML отсутствует поле "shop"')

        self.stdout.write(f'Импорт из "{file_path}" для магазина "{shop_name}"...')

        with transaction.atomic():
            shop, shop_created = Shop.objects.get_or_create(
                name=shop_name,
                defaults={
                    'filename': str(file_path),
                    'state': True,
                },
            )
            if shop_created:
                self.stdout.write(self.style.SUCCESS(f'  + Магазин: {shop.name}'))
            else:
                shop.filename = str(file_path)
                shop.save(update_fields=['filename'])
                self.stdout.write(f'  = Магазин уже существует: {shop.name}')


            categories_map = {}
            for cat in data.get('categories', []):
                category, cat_created = Category.objects.get_or_create(
                    id=cat['id'],
                    defaults={'name': cat['name']},
                )
                if not cat_created and category.name != cat['name']:
                    category.name = cat['name']
                    category.save(update_fields=['name'])
                category.shops.add(shop)
                categories_map[cat['id']] = category

            self.stdout.write(
                self.style.SUCCESS(f'  + Категорий обработано: {len(categories_map)}')
            )

            created_count = 0
            updated_count = 0

            for item in data.get('goods', []):
                category = categories_map.get(item['category'])
                if category is None:
                    self.stderr.write(
                        f'  ! Пропущен товар id={item["id"]}: '
                        f'категория {item["category"]} не найдена'
                    )
                    continue

                product, _ = Product.objects.get_or_create(
                    name=item['name'],
                    category=category,
                )

                characteristics = item.get('parameters', {}).copy()


                for k, v in item.items():
                    if k not in STANDARD_FIELDS and k != 'parameters':
                        characteristics[k] = v

                _, pi_created = ProductInfo.objects.update_or_create(
                    product=product,
                    shop=shop,
                    foreign_id=item['id'],
                    defaults={
                        'model': item.get('model', ''),
                        'price': item['price'],
                        'recommended_price': item['price_rrc'],
                        'quantity': item['quantity'],
                        'characteristics': characteristics,
                    },
                )

                if pi_created:
                    created_count += 1
                else:
                    updated_count += 1