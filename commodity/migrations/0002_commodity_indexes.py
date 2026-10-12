from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('commodity', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commodityinfos',
            name='types',
            field=models.CharField(db_index=True, max_length=100, verbose_name='商品类型'),
        ),
        migrations.AlterField(
            model_name='commodityinfos',
            name='sold',
            field=models.IntegerField(db_index=True, verbose_name='已售数量'),
        ),
    ]
