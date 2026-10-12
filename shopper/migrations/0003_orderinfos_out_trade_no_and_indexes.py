from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopper', '0002_alter_cartinfos_commodityinfos_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartinfos',
            name='user_id',
            field=models.IntegerField(db_index=True, verbose_name='用户ID'),
        ),
        migrations.AlterField(
            model_name='orderinfos',
            name='user_id',
            field=models.IntegerField(db_index=True, verbose_name='用户ID'),
        ),
        migrations.AddField(
            model_name='orderinfos',
            name='out_trade_no',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True, verbose_name='订单号'),
        ),
    ]
