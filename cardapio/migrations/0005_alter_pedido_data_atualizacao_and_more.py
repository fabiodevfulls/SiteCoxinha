# Generated by Django 5.2 on 2025-04-12 03:31

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cardapio', '0004_alter_produto_options_remove_produto_em_oferta_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pedido',
            name='data_atualizacao',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Última Atualização'),
        ),
        migrations.AlterField(
            model_name='pedido',
            name='data_pedido',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data do Pedido'),
        ),
        migrations.AlterField(
            model_name='produto',
            name='data_cadastro',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data de Cadastro'),
        ),
    ]
