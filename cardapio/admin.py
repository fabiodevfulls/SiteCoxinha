from django.contrib import admin
from django.db.models import Field
from .models import ItemCarrinho, Produto, Categoria,Usuario # Importe todos os models que precisam do admin

class ItemCarrinhoAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        """Exibe campos dinamicamente, mostrando 'usuario' apenas se existir no modelo"""
        fields = ['id', 'produto', 'quantidade', 'session_key', 'subtotal']
        if any(field.name == 'usuario' for field in ItemCarrinho._meta.get_fields()):
            fields.insert(3, 'usuario')  # Adiciona após a quantidade
        return fields

    # Filtros e buscas seguros
    def get_list_filter(self, request):
        base_filters = ['produto']
        if 'usuario' in [f.name for f in ItemCarrinho._meta.get_fields()]:
            base_filters.append('usuario')
        return base_filters

    search_fields = ['produto__nome', 'session_key']

    # Calcula subtotal (opcional)
    def subtotal(self, obj):
        return f"R$ {obj.produto.preco * obj.quantidade:.2f}"
    subtotal.short_description = 'Subtotal'



# Registra todos os models
admin.site.register(ItemCarrinho, ItemCarrinhoAdmin)
admin.site.register(Produto)
admin.site.register(Categoria)
admin.site.register(Usuario)