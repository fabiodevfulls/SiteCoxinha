import json
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import hashlib

class Usuario(AbstractUser):
    endereco = models.TextField(blank=True)
    telefone = models.CharField(max_length=15, default='')
    cep = models.CharField(max_length=9, verbose_name='CEP', default='00000-000')
    cidade = models.CharField(max_length=100, default='Não informado')
    rua = models.CharField(max_length=200, default='Não informado')
    numero = models.CharField(max_length=10, default='S/N')
    complemento = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

class Produto(models.Model):
    nome = models.CharField(max_length=100, verbose_name='Nome do Produto')
    descricao = models.TextField(verbose_name='Descrição', blank=True, null=True)
    preco = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Preço',
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    categoria = models.ForeignKey('Categoria', on_delete=models.SET_NULL, null=True, blank=True)
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)
    disponivel = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.nome} - R$ {self.preco}"

    class Meta:
        verbose_name = 'Produto'
        ordering = ['nome']

class ItemCarrinho(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)  # <--- NOVO CAMPO
    
    def subtotal(self):
        return self.produto.preco * self.quantidade

    
class Pedido(models.Model):
    METODO_PAGAMENTO = [
        ('pix', 'PIX'),
        ('cartao', 'Cartão de Crédito'),
        ('mercado_pago', 'Mercado Pago')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('approved', 'Aprovado'),
        ('rejected', 'Rejeitado'),
        ('refunded', 'Reembolsado'),
        ('processing', 'Processando')
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data_pedido = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    codigo_transacao = models.CharField(max_length=100, unique=True, blank=True, null=True)
    codigo_pix = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.username}"

    class Meta:
        verbose_name = 'Pedido'
        ordering = ['-data_pedido']

class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.preco_unitario * self.quantidade
    





class PaymentLog(models.Model):
    payment_id = models.CharField(max_length=255, unique=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    payload_hash = models.CharField(max_length=64)  # Para armazenar SHA-256 do payload

    @classmethod
    def create_from_payment(cls, payment_id, payload):
        payload_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        return cls.objects.create(payment_id=payment_id, payload_hash=payload_hash)