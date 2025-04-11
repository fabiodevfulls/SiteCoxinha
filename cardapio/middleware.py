from django.contrib.auth.models import User
from .models import ItemCarrinho  # Import relativo pois estão no mesmo app

class CarrinhoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.session.session_key:
            request.session.create()
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            carrinho_count = ItemCarrinho.objects.filter(usuario=request.user).count()
        else:
            carrinho_count = ItemCarrinho.objects.filter(
                session_key=request.session.session_key
            ).count()
        
        request.session['carrinho_count'] = carrinho_count
        return self.get_response(request)