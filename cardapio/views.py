from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PedidoItem, Produto, Categoria, ItemCarrinho, Usuario, Pedido
from .forms import CadastroForm
import mercadopago
import json
import logging
from django.db import transaction
from django.db.models import Q

# Log Configuration
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

# Views Protegidas
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
def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    
    # Define a chave de sessão para usuários não autenticados
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    # Usuário autenticado
    if request.user.is_authenticated:
        item, created = ItemCarrinho.objects.get_or_create(
            produto=produto,
            usuario=request.user,
            defaults={'quantidade': 1}
        )
    # Usuário anônimo (usa session_key)
    else:
        item, created = ItemCarrinho.objects.get_or_create(
            produto=produto,
            session_key=session_key,
            defaults={'quantidade': 1}
        )

    if not created:
        item.quantidade += 1
        item.save()
    
    return redirect('ver_carrinho')


@login_required
def meus_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-criado_em')
    return render(request, 'cardapio/pedidos.html', {'pedidos': pedidos})

@login_required
def ver_carrinho(request):
    if request.user.is_authenticated:
        itens = ItemCarrinho.objects.filter(usuario=request.user)
    else:
        session_key = request.session.session_key
        itens = ItemCarrinho.objects.filter(session_key=session_key)
    
    total = sum(item.subtotal() for item in itens)
    return render(request, 'cardapio/carrinho.html', {
        'itens': itens,
        'total': total
    })


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
    # Obtém a chave de sessão mesmo para usuários autenticados
    session_key = request.session.session_key
    
    # Busca o item por ID + usuário OU session_key
    item = get_object_or_404(
        ItemCarrinho,
        Q(id=item_id) & (Q(usuario=request.user) | Q(session_key=session_key)))
    
    item.delete()
    return redirect('ver_carrinho')  # Mantido conforme sua solicitação

def gerar_qrcode_pix(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
    payment_response = sdk.payment().get(pedido.codigo_transacao)
    
    if payment_response['status'] == 200:
        payment = payment_response['response']
        qr_code = payment['point_of_interaction']['transaction_data']['qr_code']
        qr_code_base64 = payment['point_of_interaction']['transaction_data']['qr_code_base64']
        
        return render(request, 'cardapio/qr_code.html', {
            'pedido': pedido,
            'qr_code': qr_code,
            'qr_code_base64': qr_code_base64
        })
    
    messages.error(request, "Erro ao gerar QR Code")
    return redirect('pagamento_falhou', pedido_id=pedido.id)
@login_required
def finalizar_compra(request):
    try:
        # Obter itens do carrinho (seu código existente)
        if request.user.is_authenticated:
            carrinho = ItemCarrinho.objects.filter(usuario=request.user)
        else:
            session_key = request.session.session_key
            carrinho = ItemCarrinho.objects.filter(session_key=session_key)

        if not carrinho.exists():
            messages.error(request, "Seu carrinho está vazio")
            return redirect('ver_carrinho')

        total = sum(item.subtotal() for item in carrinho)

        # Criar pedido
        pedido = Pedido.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            total=total,
            status='pending',
        )

        # Criar itens do pedido (seu código existente)
        for item in carrinho:
            PedidoItem.objects.create(
                pedido=pedido,
                produto=item.produto,
                quantidade=item.quantidade,
                preco_unitario=item.produto.preco
            )

        # Configurar SDK do Mercado Pago para PIX
        sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])

        # Criar pagamento PIX diretamente (não preferência)
        payment_data = {
            "transaction_amount": float(total),
            "payment_method_id": "pix",
            "payer": {
                "email": request.user.email if request.user.is_authenticated else "cliente@example.com",
                "first_name": request.user.first_name if request.user.is_authenticated else "Cliente",
                "last_name": request.user.last_name if request.user.is_authenticated else "Anônimo",
            },
            "notification_url": request.build_absolute_uri(reverse('webhook_mercadopago')),
            "description": f"Pedido #{pedido.id} - Lanchonete Delícia de Coxinha",
            "external_reference": str(pedido.id),
        }

        payment_response = sdk.payment().create(payment_data)

        if payment_response['status'] not in [200, 201]:
            error_msg = payment_response.get('response', {}).get('message', 'Erro desconhecido')
            raise Exception(f"Erro ao criar pagamento PIX: {error_msg}")

        payment_info = payment_response['response']
        
        # Atualizar pedido com dados do PIX
        pedido.codigo_transacao = payment_info['id']
        pedido.save()

        # Limpar carrinho
        carrinho.delete()

        # Redirecionar para a página de QR Code com os dados do PIX
        return redirect('mostrar_qrcode', pedido_id=pedido.id)

    except Exception as e:
        logger.error(f"Erro no checkout PIX: {str(e)}", exc_info=True)
        messages.error(request, f"Erro ao processar pagamento PIX: {str(e)}")
        return redirect('ver_carrinho')
    

def mostrar_qrcode(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
    payment_response = sdk.payment().get(pedido.codigo_transacao)
    
    if payment_response['status'] == 200:
        payment_data = payment_response['response']
        
        # Verificar se é PIX e tem dados de QR Code
        if (payment_data['payment_method_id'] == 'pix' and 
            'point_of_interaction' in payment_data and 
            'transaction_data' in payment_data['point_of_interaction']):
            
            qr_code = payment_data['point_of_interaction']['transaction_data']['qr_code']
            qr_code_base64 = payment_data['point_of_interaction']['transaction_data']['qr_code_base64']
            
            return render(request, 'cardapio/qr_code.html', {
                'pedido': pedido,
                'qr_code': qr_code,
                'qr_code_base64': qr_code_base64,
                'pix_data': payment_data['point_of_interaction']['transaction_data']
            })
    
    messages.error(request, "Não foi possível gerar o QR Code PIX")
    return redirect('pagamento_falhou', pedido_id=pedido.id)
    
@csrf_exempt
def webhook_mercadopago(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Notificação recebida: {data}")

            # Para notificações do tipo payment
            if data.get('type') == 'payment':
                payment_id = data.get('data', {}).get('id')
                if payment_id:
                    sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
                    payment = sdk.payment().get(payment_id)
                    
                    if payment['status'] == 200:
                        payment_data = payment['response']
                        pedido_id = payment_data.get('external_reference')
                        
                        if pedido_id:
                            try:
                                pedido = Pedido.objects.get(id=pedido_id)
                                
                                # Atualizar status conforme resposta do Mercado Pago
                                if payment_data['status'] == 'approved':
                                    pedido.status = 'paid'
                                    pedido.save()
                                    # Enviar e-mail de confirmação (opcional)
                                    # enviar_email_confirmacao(pedido)
                                elif payment_data['status'] == 'pending':
                                    pedido.status = 'pending'
                                    pedido.save()
                                elif payment_data['status'] in ['cancelled', 'rejected']:
                                    pedido.status = 'failed'
                                    pedido.save()
                                
                                return HttpResponse(status=200)
                            
                            except Pedido.DoesNotExist:
                                logger.error(f"Pedido {pedido_id} não encontrado")
                                return HttpResponse(status=404)
            
            return HttpResponse(status=200)
        
        except Exception as e:
            logger.error(f"Erro no webhook: {str(e)}")
            return HttpResponse(status=500)
    
    return HttpResponse(status=405)

def pagamento_aprovado(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Verificar status real no Mercado Pago
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
from django.http import JsonResponse

@csrf_exempt
def verificar_status_pagamento(request, pedido_id):
    if request.method == 'GET':
        try:
            pedido = Pedido.objects.get(id=pedido_id)
            
            # Se já tiver status, retornar
            if pedido.status in ['paid', 'failed']:
                return JsonResponse({'status': pedido.status})
            
            # Consultar Mercado Pago se ainda estiver pendente
            sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])
            payment = sdk.payment().get(pedido.codigo_transacao)
            
            if payment['status'] == 200:
                status_mp = payment['response']['status']
                if status_mp == 'approved':
                    pedido.status = 'paid'
                    pedido.save()
                elif status_mp in ['cancelled', 'rejected']:
                    pedido.status = 'failed'
                    pedido.save()
                
                return JsonResponse({'status': pedido.status})
            
            return JsonResponse({'status': pedido.status})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)