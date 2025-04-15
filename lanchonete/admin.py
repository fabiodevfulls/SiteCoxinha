from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

# Personalização global do admin
admin.site.site_header = '🍗 Administração Coxinhas Delícia'
admin.site.site_title = 'Sistema de Gerenciamento'
admin.site.index_title = 'Painel de Controle'

class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        # Personaliza o nome do app principal
        app_list[0]['name'] = '📋 Cardápio'
        return app_list

admin.site = CustomAdminSite(name='customadmin')