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
@login_required
def finalizar_compra(request):
    try:
        if request.user.is_authenticated:
            carrinho = ItemCarrinho.objects.filter(usuario=request.user)
        else:
            session_key = request.session.session_key
            carrinho = ItemCarrinho.objects.filter(session_key=session_key)

        total = sum(item.subtotal() for item in carrinho)

        # Cria o pedido antes da preferência
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=total,
            status='pending',  # Mantenha o status como 'pending' até a finalização
        )

        # Cria os itens do pedido
        pedido_itens = []
        for item in carrinho:
            pedido_itens.append(PedidoItem(
                pedido=pedido,
                produto=item.produto,
                quantidade=item.quantidade,
                preco_unitario=item.produto.preco
            ))
        PedidoItem.objects.bulk_create(pedido_itens)

        sdk = mercadopago.SDK(settings.MERCADOPAGO['ACCESS_TOKEN'])

        # Agora que temos o ID do pedido, podemos usá-lo nos back_urls
        preference_data = {
            "items": [{
                "title": f"Pedido - {request.user.username}",
                "quantity": 1,
                "unit_price": float(total),
                "currency_id": "BRL"
            }],
            "payer": {
                "name": request.user.username,
                "email": request.user.email
            },
            "back_urls": {
                "success": request.build_absolute_uri(reverse('pagamento_aprovado', args=[pedido.id])),
                "failure": request.build_absolute_uri(reverse('pagamento_falhou', args=[pedido.id])),
                "pending": request.build_absolute_uri(reverse('pagamento_pendente', args=[pedido.id]))
            },
            "auto_return": "approved",
            "payment_methods": {
                "excluded_payment_types": [{"id": "credit_card"}],
                "default_payment_method": "pix"  # Defina o método de pagamento como PIX
            }
        }

        # Cria a preferência no Mercado Pago
        preference_response = sdk.preference().create(preference_data)

        if 'status' not in preference_response or preference_response['status'] not in [200, 201]:
            raise Exception("Erro ao criar preferência no Mercado Pago")

        # Atualiza o código da transação agora que temos a preferência
        pedido.codigo_transacao = preference_response["response"]["id"]
        pedido.save()

        # Limpa o carrinho
        carrinho.delete()

        # Redireciona para o Mercado Pago (sandbox ou produção)
        return redirect(preference_response["response"]["sandbox_init_point"])

    except Exception as e:
        logger.error(f"Erro no processo de pagamento: {str(e)}", exc_info=True)
        messages.error(request, f"Erro ao processar pagamento: {str(e)}")
        return redirect('ver_carrinho')

@csrf_exempt
def webhook_mercadopago(request):
    if request.method == 'GET':
        return HttpResponse("🔧 Webhook pronto para receber notificações.", status=200)

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            logger.info("🔔 Webhook recebido: %s", payload)

            pagamento_status = payload.get('status', None)
            pedido_id = payload.get('data', {}).get('id', None)
            if pedido_id:
                pedido = Pedido.objects.get(id=pedido_id)
                if pagamento_status == "approved":
                    pedido.status = "paid"
                    pedido.save()

            return HttpResponse(status=200)
        except Exception as e:
            logger.error("Erro no webhook: %s", str(e))
            return HttpResponse(status=400)

    return HttpResponse(status=405)


def pagamento_aprovado(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'cardapio/pagamento_aprovado.html', {'pedido': pedido})

def pagamento_falhou(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'cardapio/pagamento_falhou.html', {'pedido': pedido})

def pagamento_pendente(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'cardapio/pagamento_pendente.html', {'pedido': pedido})
