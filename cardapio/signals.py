from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import ItemCarrinho

@receiver(user_logged_in)
def transferir_carrinho_ao_login(sender, request, user, **kwargs):
    session_key = request.session.session_key
    if session_key:
        # Transfere itens da sessão para o usuário logado
        ItemCarrinho.objects.filter(session_key=session_key).update(
            usuario=user,
            session_key=None
        )