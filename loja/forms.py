from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import password_validators_help_text_html, validate_password

from .models import Pedido

User = get_user_model()
EMAIL_MAX = 150  # o e-mail é gravado no campo username (150 caracteres)


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


class LoginForm(AuthenticationForm):
    """Login com e-mail e senha."""

    username = forms.EmailField(
        label="E-mail", max_length=EMAIL_MAX,
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Senha", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "E-mail ou senha incorretos.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].lower()


class CadastroForm(forms.Form):
    nome = forms.CharField(label="Nome", max_length=80)
    email = forms.EmailField(label="E-mail", max_length=EMAIL_MAX)
    senha = forms.CharField(
        label="Senha", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validators_help_text_html(),
    )
    senha2 = forms.CharField(
        label="Confirmar senha", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean(self):
        dados = super().clean()
        senha, senha2 = dados.get("senha"), dados.get("senha2")
        if senha and senha2 and senha != senha2:
            self.add_error("senha2", "As senhas não são iguais.")
        elif senha:
            usuario = User(username=dados.get("email", ""), email=dados.get("email", ""),
                           first_name=dados.get("nome", ""))
            try:
                validate_password(senha, usuario)
            except forms.ValidationError as erro:
                self.add_error("senha", erro)
        return dados

    def save(self):
        d = self.cleaned_data
        return User.objects.create_user(
            username=d["email"], email=d["email"], password=d["senha"], first_name=d["nome"],
        )
