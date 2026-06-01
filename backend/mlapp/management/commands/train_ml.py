from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '训练价格预测与热度分类模型'

    def handle(self, *args, **options):
        from mlapp.train_models import main
        main()
        self.stdout.write(self.style.SUCCESS('模型训练完成'))
