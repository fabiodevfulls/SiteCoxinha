from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.conf import settings

import mercadopago
import json
import logging

from .models import Produto, Categoria, ItemCarrinho, Usuario, Pedido, PedidoItem
from .forms import CadastroForm

logger = logging.getLogger(__name__)

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

@login_required
def ver_carrinho(request):
    session_key = request.session.session_key or request.session.create()
    itens = ItemCarrinho.objects.filter(usuario=request.user) if request.user.is_authenticated else ItemCarrinho.objects.filter(session_key=session_key)
    total = sum(item.subtotal() for item in itens)
    return render(request, 'cardapio/carrinho.html', {'itens': itens, 'total': total})

@login_required
def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    session_key = request.session.session_key or request.session.create()

    filtro = {'produto': produto}
    if request.user.is_authenticated:
        filtro['usuario'] = request.user
    else:
        filtro['session_key'] = session_key

    item, created = ItemCarrinho.objects.get_or_create(**filtro, defaults={'quantidade': 1})
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
    session_key = request.session.session_key
    item = get_object_or_404(ItemCarrinho, Q(id=item_id) & (Q(usuario=request.user) | Q(session_key=session_key)))
    item.delete()
    return redirect('ver_carrinho')
@login_required
def meus_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-criado_em')
    return render(request, 'cardapio/pedidos.html', {'pedidos': pedidos})


@login_required
def finalizar_compra(request):
    try:
        session_key = request.session.session_key or request.session.create()
        carrinho = ItemCarrinho.objects.filter(usuario=request.user) if request.user.is_authenticated else ItemCarrinho.objects.filter(session_key=session_key)

        if not carrinho.exists():
            messages.error(request, "Seu carrinho está vazio")
            return redirect('ver_carrinho')

        total = sum(item.subtotal() for item in carrinho)

        pedido = Pedido.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            total=total,
            status='pending',
        )

        for item in carrinho:
            PedidoItem.objects.create(
                pedido=pedido,
                produto=item.produto,
                quantidade=item.quantidade,
                preco_unitario=item.produto.preco
            )

        sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])

        payment_data = {
            "transaction_amount": float(total),
            "payment_method_id": "pix",
            "payer": {
                "email": request.user.email if request.user.is_authenticated else "cliente@example.com",
                "first_name": request.user.first_name if request.user.is_authenticated else "Cliente",
            },
            "notification_url": request.build_absolute_uri(reverse('webhook_mercadopago')),
            "description": f"Pedido #{pedido.id}",
            "external_reference": str(pedido.id),
        }

        payment_response = sdk.payment().create(payment_data)

        if payment_response['status'] not in [200, 201]:
            raise Exception(payment_response.get('response', {}).get('message', 'Erro desconhecido'))

        payment_info = payment_response['response']
        pedido.codigo_transacao = payment_info['id']
        pedido.save()

        carrinho.delete()

        return JsonResponse({'redirect_url': reverse('mostrar_qrcode', args=[pedido.id])})

    except Exception as e:
        logger.error(f"Erro no checkout: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Erro ao processar pagamento'}, status=500)

def mostrar_qrcode(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
    payment = sdk.payment().get(pedido.codigo_transacao)

    if payment['status'] == 200:
        data = payment['response']
        if data['payment_method_id'] == 'pix':
            qr = data['point_of_interaction']['transaction_data']
            return render(request, 'cardapio/qr_code.html', {
                'pedido': pedido,
                'qr_code': qr['qr_code'],
                'qr_code_base64': qr['qr_code_base64'],
                'pix_data': qr
            })

    messages.error(request, "Não foi possível gerar o QR Code PIX")
    return redirect('pagamento_falhou', pedido_id=pedido.id)
@login_required
def finalizar_compra(request):
    try:
        session_key = request.session.session_key or request.session.create()
        carrinho = ItemCarrinho.objects.filter(usuario=request.user) if request.user.is_authenticated else ItemCarrinho.objects.filter(session_key=session_key)

        if not carrinho.exists():
            messages.error(request, "Seu carrinho está vazio")
            return redirect('ver_carrinho')

        total = sum(item.subtotal() for item in carrinho)

        print("Total do pedido:", total)

        pedido = Pedido.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            total=total,
            status='pending',
        )

        for item in carrinho:
            PedidoItem.objects.create(
                pedido=pedido,
                produto=item.produto,
                quantidade=item.quantidade,
                preco_unitario=item.produto.preco
            )

        print("Pedido criado:", pedido.id)

        sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])

        payment_data = {
            "transaction_amount": float(total),
            "payment_method_id": "pix",
            "payer": {
                "email": request.user.email if request.user.is_authenticated else "cliente@example.com",
                "first_name": request.user.first_name or "Cliente",
            },
            "notification_url": request.build_absolute_uri(reverse('webhook_mercadopago')),
            "description": f"Pedido #{pedido.id}",
            "external_reference": str(pedido.id),
        }

        print("Dados de pagamento:", payment_data)

        payment_response = sdk.payment().create(payment_data)

        print("Resposta do Mercado Pago:", payment_response)

        if payment_response['status'] not in [200, 201]:
            raise Exception(payment_response.get('response', {}).get('message', 'Erro desconhecido no Mercado Pago'))

        payment_info = payment_response['response']
        pedido.codigo_transacao = payment_info['id']
        pedido.save()

        carrinho.delete()

        return JsonResponse({'redirect_url': reverse('mostrar_qrcode', args=[pedido.id])})

    except Exception as e:
        print("Erro ao finalizar compra:", str(e))  # ou logger.error
        return JsonResponse({'error': f'Erro ao processar pagamento: {str(e)}'}, status=500)


@csrf_exempt
def webhook_mercadopago(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Notificação recebida: {data}")

            if data.get('type') == 'payment':
                payment_id = data.get('data', {}).get('id')
                if payment_id:
                    sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
                    payment = sdk.payment().get(payment_id)

                    if payment['status'] == 200:
                        response = payment['response']
                        pedido_id = response.get('external_reference')
                        if pedido_id:
                            pedido = Pedido.objects.filter(id=pedido_id).first()
                            if pedido:
                                status = response['status']
                                if status == 'approved':
                                    pedido.status = 'paid'
                                elif status == 'pending':
                                    pedido.status = 'pending'
                                elif status in ['cancelled', 'rejected']:
                                    pedido.status = 'failed'
                                pedido.save()
                                return HttpResponse(status=200)
            return HttpResponse(status=200)
        except Exception as e:
            logger.error(f"Erro no webhook: {str(e)}")
            return HttpResponse(status=500)
    return HttpResponse(status=405)
def pagamento_aprovado(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
    payment_info = sdk.payment().get(pedido.codigo_transacao)

    if payment_info['status'] == 200:
        pedido.status = payment_info['response']['status']
        pedido.save()

    return render(request, 'cardapio/pagamento_aprovado.html', {
        'pedido': pedido,
        'payment_info': payment_info.get('response', {})
    })

def pagamento_falhou(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.status = 'failed'
    pedido.save()
    return render(request, 'cardapio/pagamento_falhou.html', {'pedido': pedido})

def pagamento_pendente(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.status = 'pending'
    pedido.save()
    return render(request, 'cardapio/pagamento_pendente.html', {'pedido': pedido})

@csrf_exempt
def verificar_status_pagamento(request, pedido_id):
    if request.method == 'GET':
        try:
            pedido = Pedido.objects.get(id=pedido_id)
            if pedido.status in ['paid', 'failed']:
                return JsonResponse({'status': pedido.status})

            sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
            payment = sdk.payment().get(pedido.codigo_transacao)

            if payment['status'] == 200:
                status_mp = payment['response']['status']
                if status_mp == 'approved':
                    pedido.status = 'paid'
                elif status_mp in ['cancelled', 'rejected']:
                    pedido.status = 'failed'
                pedido.save()

                return JsonResponse({'status': pedido.status})
            return JsonResponse({'status': pedido.status})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método não permitido'}, status=405)
