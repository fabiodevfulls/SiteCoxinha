from django.urls import path
from . import views

urlpatterns = [
    # URLs de Produtos e Carrinho
    path('', views.ProdutoListView.as_view(), name='menu'),
    path('produto/<int:pk>/', views.ProdutoDetailView.as_view(), name='detalhe_produto'),
    path('adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('remover/<int:item_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('carrinho/aumentar/<int:item_id>/', views.aumentar_quantidade, name='aumentar_quantidade'),
    path('carrinho/diminuir/<int:item_id>/', views.diminuir_quantidade, name='diminuir_quantidade'),
    
    # URLs de Autenticação
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('cadastro/', views.CadastroView.as_view(), name='cadastro'),
    path('logout/', views.custom_logout, name='logout'),
    
    # URLs de Pedidos e Pagamento
    path('meus-pedidos/', views.meus_pedidos, name='meus_pedidos'),
    path('finalizar-compra/', views.finalizar_compra, name='finalizar_compra'),
    path('pagamento/pix/<int:pedido_id>/', views.pagamento_pix, name='pagamento_pix'),
    path('pagamento/aprovado/<int:pedido_id>/', views.pagamento_aprovado, name='pagamento_aprovado'),
    path('pagamento/falhou/<int:pedido_id>/', views.pagamento_falhou, name='pagamento_falhou'),
    path('pagamento/pendente/<int:pedido_id>/', views.pagamento_pendente, name='pagamento_pendente'),
    
    # API e Webhooks
    path('api/verificar-status/<int:pedido_id>/', views.verificar_status_pagamento, name='verificar_status'),
    path('webhook/mercadopago/', views.webhook_mercadopago, name='webhook_mercadopago'),
    
    # Static Files
    path('favicon.ico', views.serve, {'path': 'img/favicon.ico'}),
]