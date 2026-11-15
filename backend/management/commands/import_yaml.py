from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from backend.services import import_yaml_file


class Command(BaseCommand):
    help = 'Импорт из YAML-файла'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str)

    def handle(self, *args, **options):
        try:
            stats = import_yaml_file(Path(options['file']))
        except (FileNotFoundError, ValueError) as e:
            raise CommandError(str(e))

        self.stdout.write(self.style.SUCCESS(
            f'Импорт завершён: магазин «{stats["shop"]}», '
            f'создано {stats["created"]}, обновлено {stats["updated"]}'
        ))