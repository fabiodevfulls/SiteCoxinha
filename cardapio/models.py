from django.db import models

from django.db import models
from django.core.validators import MinValueValidator

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    imagem = models.ImageField(upload_to='produtos/')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    em_oferta = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nome

class ItemCarrinho(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    def subtotal(self):
        return self.produto.preco * self.quantidade