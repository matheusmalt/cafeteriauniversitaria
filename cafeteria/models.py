from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ItemMenu(models.Model):
    """
    Representa um item do cardápio da cafeteria, como bebidas ou alimentos.
    """
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=6, decimal_places=2)
    categoria = models.CharField(
        max_length=50,
        choices=[
            ('Bebidas', 'Bebidas'),
            ('Alimentos', 'Alimentos'),
            ('Sobremesas', 'Sobremesas'),
        ]
    )
    descricao = models.TextField()
    disponibilidade = models.BooleanField(default=True)
    destaque = models.BooleanField(default=False)
    imagem = models.ImageField(upload_to='items/', blank=True, null=True)
    ingredientes = models.TextField(blank=True)
    opcoes = models.JSONField(default=list)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Item do Cardápio"
        verbose_name_plural = "Itens do Cardápio"

class Carrinho(models.Model):
    """
    Representa o carrinho de compras de um cliente.
    """
    cliente = models.ForeignKey(User, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrinho de {self.cliente.email}"

    class Meta:
        verbose_name = "Carrinho"
        verbose_name_plural = "Carrinhos"

class ItemCarrinho(models.Model):
    """
    Representa um item específico no carrinho, com quantidade e preço unitário.
    """
    carrinho = models.ForeignKey(Carrinho, on_delete=models.CASCADE)
    item_menu = models.ForeignKey(ItemMenu, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=6, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    def __str__(self):
        return f"{self.quantidade}x {self.item_menu.nome}"

    class Meta:
        verbose_name = "Item do Carrinho"
        verbose_name_plural = "Itens do Carrinho"

class Promocao(models.Model):
    """
    Representa uma promoção ativa na cafeteria, com desconto e período de validade.
    """
    titulo = models.CharField(max_length=100)
    desconto = models.DecimalField(max_digits=5, decimal_places=2)  # Ex.: 10.00 para 10%
    data_inicio = models.DateField()
    data_fim = models.DateField()
    descricao = models.TextField()
    ativa = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo

    @property
    def is_valida(self):
        """
        Verifica se a promoção está ativa e dentro do período de validade.
        """
        today = timezone.now().date()
        return self.ativa and self.data_inicio <= today <= self.data_fim

    class Meta:
        verbose_name = "Promoção"
        verbose_name_plural = "Promoções"

class Pedido(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PREPARACAO', 'Em Preparação'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    cliente = models.ForeignKey(User, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    metodo_entrega = models.CharField(max_length=50, blank=True)
    endereco_entrega = models.TextField(blank=True)
    metodo_pagamento = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f'Pedido #{self.id} - {self.cliente.email}'

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

class PedidoItem(models.Model):
    """
    Representa um item específico em um pedido, com quantidade e preço unitário.
    """
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    item_menu = models.ForeignKey(ItemMenu, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=6, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    def __str__(self):
        return f"{self.quantidade}x {self.item_menu.nome} no Pedido #{self.pedido.id}"

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'