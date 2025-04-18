import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.conf import settings
import mercadopago
from .models import Produto, Categoria, ItemCarrinho, Usuario, Pedido, PedidoItem
from .forms import CadastroForm

logger = logging.getLogger(__name__)

# Views de Autenticação
class CustomLoginView(LoginView):
    template_name = 'cardapio/login.html'
    redirect_authenticated_user = True

class CadastroView(CreateView):
    model = Usuario
    form_class = CadastroForm
    template_name = 'cardapio/cadastro.html'
    success_url = '/'

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

def custom_logout(request):
    logout(request)
    return redirect('login')

# Views de Produtos
class ProdutoListView(LoginRequiredMixin, ListView):
    model = Produto
    template_name = 'cardapio/menu.html'
    context_object_name = 'produtos'
    login_url = '/login/'

    def get_queryset(self):
        categoria = self.request.GET.get('categoria')
        queryset = super().get_queryset()
        return queryset.filter(categoria__nome=categoria) if categoria else queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        return context

class ProdutoDetailView(LoginRequiredMixin, DetailView):
    model = Produto
    template_name = 'cardapio/detalhe_produto.html'
    context_object_name = 'produto'
    login_url = '/login/'

# Views de Carrinho
@login_required
def ver_carrinho(request):
    itens = ItemCarrinho.objects.filter(usuario=request.user)
    total = sum(item.subtotal() for item in itens)
    return render(request, 'cardapio/carrinho.html', {'itens': itens, 'total': total})

@login_required
def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    item, created = ItemCarrinho.objects.get_or_create(
        produto=produto,
        usuario=request.user,
        defaults={'quantidade': 1}
    )
    if not created:
        item.quantidade += 1
        item.save()
    return redirect('ver_carrinho')

@login_required
def aumentar_quantidade(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id, usuario=request.user)
    item.quantidade += 1
    item.save()
    return redirect('ver_carrinho')

@login_required
def diminuir_quantidade(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id, usuario=request.user)
    if item.quantidade > 1:
        item.quantidade -= 1
        item.save()
    return redirect('ver_carrinho')

@login_required
def remover_do_carrinho(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id, usuario=request.user)
    item.delete()
    return redirect('ver_carrinho')

# Views de Pedidos e Pagamento
@login_required
def meus_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-criado_em')
    return render(request, 'cardapio/pedidos.html', {'pedidos': pedidos})

@login_required
def finalizar_compra(request):
    try:
        carrinho = ItemCarrinho.objects.filter(usuario=request.user)
        if not carrinho.exists():
            return JsonResponse({'error': 'Seu carrinho está vazio'}, status=400)

        total = sum(item.subtotal() for item in carrinho)

        pedido = Pedido.objects.create(
            usuario=request.user,
            total=total,
            status='pending'
        )

        for item in carrinho:
            PedidoItem.objects.create(
                pedido=pedido,
                produto=item.produto,
                quantidade=item.quantidade,
                preco_unitario=item.produto.preco
            )

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        
        payment_data = {
            "transaction_amount": float(total),
            "payment_method_id": "pix",
            "payer": {
                "email": request.user.email,
                "first_name": request.user.first_name or "Cliente",
            },
            "notification_url": request.build_absolute_uri(reverse('webhook_mercadopago')),
            "description": f"Pedido #{pedido.id}",
            "external_reference": str(pedido.id),
        }

        payment_response = sdk.payment().create(payment_data)

        if payment_response['status'] not in [200, 201]:
            error_msg = payment_response.get('response', {}).get('message', 'Erro no Mercado Pago')
            raise Exception(error_msg)

        payment = payment_response['response']
        pedido.codigo_transacao = payment['id']
        pedido.save()

        carrinho.delete()

        return JsonResponse({
            'success': True,
            'redirect_url': reverse('pagamento_pix', args=[pedido.id])
        })

    except Exception as e:
        logger.error(f"Erro ao finalizar compra: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'redirect_url': reverse('pagamento_falhou', args=[pedido.id])
        }, status=500)

@login_required
def pagamento_pix(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    
    try:
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        payment = sdk.payment().get(pedido.codigo_transacao)
        
        if payment['status'] != 200:
            raise Exception("Erro ao consultar pagamento")
            
        payment_data = payment['response']
        
        if payment_data.get('status') == 'approved':
            return redirect('pagamento_aprovado', pedido_id=pedido.id)
            
        qr_data = payment_data.get('point_of_interaction', {}).get('transaction_data', {})
        
        if not qr_data.get('qr_code_base64'):
            raise Exception("QR Code não gerado")
        
        return render(request, 'cardapio/pagamento_pix.html', {
            'pedido': pedido,
            'qr_code': qr_data.get('qr_code', ''),
            'qr_code_base64': qr_data['qr_code_base64'],
            'pix_data': qr_data
        })
        
    except Exception as e:
        logger.error(f"Erro no pagamento PIX: {str(e)}")
        messages.error(request, f"Erro ao processar PIX: {str(e)}")
        return redirect('pagamento_falhou', pedido_id=pedido.id)

@login_required
def pagamento_aprovado(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    return render(request, 'cardapio/pagamento_aprovado.html', {'pedido': pedido})

@login_required
def pagamento_falhou(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    pedido.status = 'failed'
    pedido.save()
    return render(request, 'cardapio/pagamento_falhou.html', {'pedido': pedido})

@login_required
def pagamento_pendente(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    return render(request, 'cardapio/pagamento_pendente.html', {'pedido': pedido})

@csrf_exempt
def webhook_mercadopago(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            payment_id = data['data']['id']
            
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            payment = sdk.payment().get(payment_id)
            
            if payment['status'] != 200:
                return HttpResponse(status=400)
                
            payment_data = payment['response']
            pedido = Pedido.objects.get(id=payment_data['external_reference'])
            
            if payment_data['status'] == 'approved':
                pedido.status = 'paid'
            elif payment_data['status'] in ['cancelled', 'rejected']:
                pedido.status = 'failed'
                
            pedido.save()
            return HttpResponse(status=200)
            
        except Exception as e:
            logger.error(f"Erro no webhook: {str(e)}")
            return HttpResponse(status=500)
    
    return HttpResponse(status=405)

@login_required
def verificar_status_pagamento(request, pedido_id):
    if request.method == 'GET':
        try:
            pedido = Pedido.objects.get(id=pedido_id)
            return JsonResponse({'status': pedido.status})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método não permitido'}, status=405)