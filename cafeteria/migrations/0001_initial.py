# Generated by Django 5.2 on 2025-05-16 01:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemMenu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('descricao', models.TextField()),
                ('preco', models.DecimalField(decimal_places=2, max_digits=6)),
                ('categoria', models.CharField(max_length=50)),
                ('disponibilidade', models.BooleanField(default=True)),
                ('destaque', models.BooleanField(default=False)),
                ('imagem', models.ImageField(blank=True, upload_to='items/')),
                ('ingredientes', models.TextField(blank=True)),
                ('opcoes', models.JSONField(default=list)),
            ],
        ),
        migrations.CreateModel(
            name='Promocao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=100)),
                ('descricao', models.TextField()),
                ('desconto', models.DecimalField(decimal_places=2, max_digits=5)),
                ('data_inicio', models.DateField()),
                ('data_fim', models.DateField()),
                ('ativa', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Carrinho',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ItemCarrinho',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade', models.PositiveIntegerField(default=1)),
                ('preco_unitario', models.DecimalField(decimal_places=2, max_digits=6)),
                ('carrinho', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cafeteria.carrinho')),
                ('item_menu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cafeteria.itemmenu')),
            ],
        ),
    ]
