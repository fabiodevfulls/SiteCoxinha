import json
import logging
import hashlib
import hmac
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import mercadopago
from .models import Produto, Categoria, ItemCarrinho, Usuario, Pedido, PedidoItem
from .forms import CadastroForm
from django.contrib.auth.views import LoginView
from .models import Produto, Categoria, ItemCarrinho, Pedido, PedidoItem, PaymentLog
from datetime import datetime, timedelta
from django.http import HttpResponse, HttpResponseNotFound
import os
from .models import Pedido, PaymentLog
from .utils import validate_mercadopago_signature

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
class ProdutoListView(ListView):
    model = Produto
    template_name = 'cardapio/menu.html'
    context_object_name = 'produtos'
    

    def get_queryset(self):
        categoria = self.request.GET.get('categoria')
        queryset = super().get_queryset()
        return queryset.filter(categoria__nome=categoria) if categoria else queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        return context

class ProdutoDetailView(DetailView):
    model = Produto
    template_name = 'cardapio/detalhe_produto.html'
    context_object_name = 'produto'


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
def finalizar_compra(request, pedido_id=None):
    try:
        sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])

        if pedido_id:
            pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

            if pedido.status == 'paid':
                return JsonResponse({
                    'error': 'Este pedido já foi pago',
                    'redirect_url': reverse('pagamento_aprovado', args=[pedido.id])
                }, status=400)

            if pedido.codigo_transacao:
                sdk.payment().cancel(pedido.codigo_transacao)
        else:
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

        # Construir lista de itens do pedido
        items = []
        for item in pedido.pedidoitem_set.all():
            items.append({
                "id": str(item.produto.id),
                "title": item.produto.nome,
                "description": item.produto.descricao or "Sem descrição",
                "category_id": "food",  # categoria genérica
                "quantity": item.quantidade,
                "unit_price": float(item.preco_unitario),
                "currency_id": "BRL"
            })

        payment_data = {
            "transaction_amount": float(pedido.total),
            "payment_method_id": "pix",
            "payer": {
                "email": request.user.email,
                "first_name": request.user.first_name or "Cliente",
                "last_name": request.user.last_name or "Anônimo"
            },
            "items": items,
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

        if not pedido_id:
            carrinho.delete()

        return JsonResponse({
            'success': True,
            'redirect_url': reverse('pagamento_pix', args=[pedido.id])
        })

    except Exception as e:
        logger.error(f"Erro ao finalizar compra: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': str(e),
            'redirect_url': reverse('pagamento_falhou', args=[pedido.id]) if 'pedido' in locals() else reverse('ver_carrinho')
        }, status=500)

def validate_mercadopago_signature(payload, signature):
    """Valida a assinatura do webhook do Mercado Pago"""
    if not settings.MERCADOPAGO_WEBHOOK_SECRET:
        logger.warning("MERCADOPAGO_WEBHOOK_SECRET não configurado - skipping signature validation")
        return True
    
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET.encode()
    expected_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

    
@login_required
def pagamento_pix(request, pedido_id):
    """
    View aprimorada com validações adicionais:
    - Verifica se o usuário é dono do pedido
    - Verifica se o pedido já foi pago
    - Verifica timeout de pagamento
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Validação 1: Verifica se o usuário é dono do pedido
    if pedido.usuario != request.user:
        messages.error(request, "Você não tem permissão para acessar este pedido.")
        return redirect('meus_pedidos')
    
    # Validação 2: Verifica se o pedido já foi pago
    if pedido.status == 'paid':
        messages.info(request, "Este pedido já foi pago.")
        return redirect('pagamento_aprovado', pedido_id=pedido.id)
    
    # Validação 3: Verifica timeout de pagamento (30 minutos)
    tempo_decorrido = datetime.now(pedido.criado_em.tzinfo) - pedido.criado_em
    if tempo_decorrido > timedelta(minutes=30):
        pedido.status = 'expired'
        pedido.save()
        messages.error(request, "Tempo para pagamento expirado. Por favor, inicie um novo pedido.")
        return redirect('pagamento_falhou', pedido_id=pedido.id)
    
    try:
        sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
        payment = sdk.payment().get(pedido.codigo_transacao)
        
        if payment['status'] != 200:
            raise Exception("Erro ao consultar pagamento no Mercado Pago")
            
        payment_data = payment['response']
        
        # Se o pagamento já foi aprovado, redireciona
        if payment_data.get('status') == 'approved':
            pedido.status = 'paid'
            pedido.save()
            return redirect('pagamento_aprovado', pedido_id=pedido.id)
            
        # Se o pagamento falhou, atualiza status
        if payment_data.get('status') in ['cancelled', 'rejected']:
            pedido.status = 'failed'
            pedido.save()
            return redirect('pagamento_falhou', pedido_id=pedido.id)
        
        # Gera novo QR code se o anterior expirou
        qr_data = payment_data.get('point_of_interaction', {}).get('transaction_data', {})
        if not qr_data.get('qr_code_base64'):
            # Se não tem QR code válido, cria novo pagamento
            return finalizar_compra(request, pedido_id=pedido.id)
        
        return render(request, 'cardapio/pagamento_pix.html', {
            'pedido': pedido,
            'qr_code': qr_data.get('qr_code', ''),
            'qr_code_base64': qr_data['qr_code_base64'],
            'pix_data': qr_data,
            'minutes_left': 30 - tempo_decorrido.seconds // 60
        })
        
    except Exception as e:
        logger.error(f"Erro no pagamento PIX - Pedido {pedido.id}: {str(e)}")
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
    """
    Webhook com:
    - Validação opcional de assinatura (ativa apenas fora do DEBUG)
    - Idempotência via hash do payload
    - Tolerância para testes no modo DEBUG
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        # Verificação opcional da assinatura
        signature = request.headers.get('X-Signature')
        if signature and not validate_mercadopago_signature(request.body, signature):
            logger.warning("Assinatura do webhook inválida")
            return HttpResponse(status=403)

        # Parse do payload JSON
        try:
            data = json.loads(request.body)
            payment_id = data['data']['id']
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Erro ao parsear payload: {e}")
            return HttpResponse(status=400)

        # Verificar idempotência
        payload_hash = hashlib.sha256(request.body).hexdigest()
        if PaymentLog.objects.filter(payload_hash=payload_hash).exists():
            logger.info(f"Webhook duplicado ignorado - Payment ID: {payment_id}")
            return HttpResponse(status=200)

        # Registrar log do webhook
        PaymentLog.objects.create(
            payment_id=payment_id,
            payload_hash=payload_hash
        )

        # Consultar pagamento na API do Mercado Pago
        sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
        payment = sdk.payment().get(payment_id)

        if payment['status'] != 200:
            logger.warning(f"Pagamento não encontrado no Mercado Pago: {payment_id}")
            if settings.DEBUG:
                return HttpResponse(status=200)
            return HttpResponse(status=400)

        payment_data = payment['response']

        # Buscar pedido via external_reference
        try:
            pedido = Pedido.objects.get(id=payment_data['external_reference'])
        except (KeyError, Pedido.DoesNotExist) as e:
            logger.error(f"Pedido não encontrado para o pagamento {payment_id}: {e}")
            return HttpResponse(status=404)

        # Atualizar status do pedido
        status_pagamento = payment_data['status']
        if status_pagamento == 'approved':
            pedido.status = 'paid'
        elif status_pagamento in ['cancelled', 'rejected']:
            pedido.status = 'failed'
        elif status_pagamento == 'pending':
            pedido.status = 'pending'

        pedido.save()
        logger.info(f"Status do pedido {pedido.id} atualizado para {pedido.status}")

        return HttpResponse(status=200)

    except Exception as e:
        logger.error(f"Erro inesperado no webhook: {e}", exc_info=True)
        return HttpResponse(status=500)


@login_required
def verificar_status_pagamento(request, pedido_id):
    if request.method == 'GET':
        try:
            pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
            return JsonResponse({
                'status': pedido.status,
                'pedido_id': pedido.id,
                'total': pedido.total
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'status': 'error'
            }, status=500)
    return JsonResponse({'error': 'Método não permitido'}, status=405)

def serve_favicon(request):
    """
    View personalizada para servir o favicon.ico
    """
    # Caminho para o favicon na pasta static
    favicon_path = os.path.join(settings.STATIC_ROOT, 'img', 'favicon.ico')
    
    # Verifica se o arquivo existe
    if os.path.exists(favicon_path):
        try:
            with open(favicon_path, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/x-icon')
        except IOError:
            return HttpResponseNotFound()
    return HttpResponseNotFound()