from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from .models import Produto, Categoria, ItemCarrinho
from django.views.generic import ListView, DetailView

class ProdutoListView(ListView):
    model = Produto
    template_name = 'cardapio/menu.html'
    context_object_name = 'produtos'
    
    def get_queryset(self):
        categoria = self.request.GET.get('categoria')
        if categoria:
            return Produto.objects.filter(categoria__nome=categoria)
        return Produto.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        return context

class ProdutoDetailView(DetailView):
    model = Produto
    template_name = 'cardapio/detalhe_produto.html'
    context_object_name = 'produto'

def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    item, created = ItemCarrinho.objects.get_or_create(
        produto=produto,
        session_key=request.session.session_key,
        defaults={'quantidade': 1}
    )
    if not created:
        item.quantidade += 1
        item.save()
    return redirect('ver_carrinho')

def ver_carrinho(request):
    if not request.session.session_key:
        request.session.create()
    itens = ItemCarrinho.objects.filter(session_key=request.session.session_key)
    total = sum(item.subtotal() for item in itens)
    return render(request, 'cardapio/carrinho.html', {'itens': itens, 'total': total})

def remover_do_carrinho(request, item_id):
    item = get_object_or_404(ItemCarrinho, id=item_id)
    item.delete()
    return redirect('ver_carrinho')
