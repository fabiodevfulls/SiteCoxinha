from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProdutoListView.as_view(), name='menu'),
    path('produto/<int:pk>/', views.ProdutoDetailView.as_view(), name='detalhe_produto'),
    path('adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('remover/<int:item_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
]