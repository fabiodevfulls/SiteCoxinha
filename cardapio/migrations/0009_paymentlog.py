# Generated by Django 5.2 on 2025-04-18 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cardapio', '0008_itemcarrinho_session_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_id', models.CharField(max_length=255, unique=True)),
                ('processed_at', models.DateTimeField(auto_now_add=True)),
                ('payload_hash', models.CharField(max_length=64)),
            ],
        ),
    ]
