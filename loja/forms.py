from django import forms

from .models import Pedido


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["nome", "email", "telefone", "cep", "endereco", "cidade", "uf"]
        labels = {
            "nome": "Nome completo",
            "email": "E-mail",
            "telefone": "Telefone",
            "cep": "CEP",
            "endereco": "Endereço",
            "cidade": "Cidade",
            "uf": "UF",
        }

    def clean_uf(self):
        return self.cleaned_data["uf"].upper()
