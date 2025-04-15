from django import forms
from .models import Usuario

class CadastroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password', 'telefone', 
                 'cep', 'cidade', 'rua', 'numero', 'complemento']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nome de Usuário'
        self.fields['email'].label = 'E-mail'
        self.fields['telefone'].label = 'Telefone (WhatsApp)'
        
        # Novos labels para endereço
        self.fields['cep'].label = 'CEP'
        self.fields['cidade'].label = 'Cidade'
        self.fields['rua'].label = 'Rua'
        self.fields['numero'].label = 'Número'
        self.fields['complemento'].label = 'Complemento'

        # Adicione placeholders se quiser
        self.fields['cep'].widget.attrs.update({'placeholder': '00000-000'})
        self.fields['numero'].widget.attrs.update({'placeholder': 'Nº'})

  
class PagamentoForm(forms.Form):
    METODO_PAGAMENTO = [
        ('pix', 'PIX'),
        ('cartao', 'Cartão de Crédito'),
    ]

    metodo = forms.ChoiceField(
        choices=METODO_PAGAMENTO,
        widget=forms.RadioSelect,
        label='Método de Pagamento'
    )
    
    # Campos específicos para cartão
    numero_cartao = forms.CharField(
        required=False,
        label='Número do Cartão',
        widget=forms.TextInput(attrs={'data-card': 'true'})
    )
    validade = forms.CharField(
        required=False,
        label='Validade (MM/AA)',
        widget=forms.TextInput(attrs={'placeholder': 'MM/AA'})
    )
    cvv = forms.CharField(
        required=False,
        label='CVV',
        widget=forms.PasswordInput(render_value=True, attrs={'maxlength': '4'})
    )     