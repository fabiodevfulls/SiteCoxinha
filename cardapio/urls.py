from django.urls import path
from . import views
from .views import CustomLoginView, CadastroView, custom_logout, finalizar_compra, webhook_mercadopago

urlpatterns = [
    path('', views.ProdutoListView.as_view(), name='menu'),
    
    path('produto/<int:pk>/', views.ProdutoDetailView.as_view(), name='detalhe_produto'),
    path('adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('remover/<int:item_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('cadastro/', CadastroView.as_view(), name='cadastro'),
    path('logout/', custom_logout, name='logout'),
    path('meus-pedidos/', views.meus_pedidos, name='meus_pedidos'),
    path('carrinho/aumentar/<int:item_id>/', views.aumentar_quantidade, name='aumentar_quantidade'),
    path('carrinho/diminuir/<int:item_id>/', views.diminuir_quantidade, name='diminuir_quantidade'),


    
    # Corrigido: URL para finalizar a compra
    path('finalizar-compra/', finalizar_compra, name='finalizar_compra'),

    # Webhook para o Mercado Pago
    path('webhook/mercadopago/', webhook_mercadopago, name='webhook_mercadopago'),

    # URLs de pagamento com ID do pedido
    path('pagamento/sucesso/<int:pedido_id>/', views.pagamento_aprovado, name='pagamento_aprovado'),
    path('pagamento/falhou/<int:pedido_id>/', views.pagamento_falhou, name='pagamento_falhou'),
    path('pagamento/pendente/<int:pedido_id>/', views.pagamento_pendente, name='pagamento_pendente'),
]
