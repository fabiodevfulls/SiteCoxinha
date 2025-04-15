from django.contrib.auth.models import AnonymousUser
from .models import ItemCarrinho

class CarrinhoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.session.session_key:
            request.session.create()
        
        try:
            # Versão simplificada SEM verificação do campo 'usuario'
            if hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
                carrinho_count = ItemCarrinho.objects.filter(
                    session_key=request.session.session_key
                ).count()
            else:
                carrinho_count = ItemCarrinho.objects.filter(
                    session_key=request.session.session_key
                ).count()
                
        except Exception as e:
            # Log opcional (pode remover se quiser)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro no CarrinhoMiddleware: {str(e)}", exc_info=True)
            
            carrinho_count = 0
        
        request.session['carrinho_count'] = carrinho_count or 0
        return self.get_response(request)