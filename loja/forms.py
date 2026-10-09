from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.password_validation import password_validators_help_text_html, validate_password

from .services.contas import criar_usuario

User = get_user_model()
EMAIL_MAX = 150


class CheckoutForm(forms.Form):
    nome = forms.CharField(label="Nome completo", max_length=120)
    email = forms.EmailField(label="E-mail")
    telefone = forms.CharField(label="Telefone", max_length=20, required=False)
    cep = forms.CharField(label="CEP", max_length=9)
    endereco = forms.CharField(label="Endereço", max_length=200)
    cidade = forms.CharField(label="Cidade", max_length=80)
    uf = forms.CharField(label="UF", min_length=2, max_length=2)

    def clean_uf(self):
        return self.cleaned_data["uf"].upper()


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-mail", max_length=EMAIL_MAX,
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Senha", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "E-mail ou senha incorretos.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].lower()


class RecuperarSenhaForm(PasswordResetForm):
    email = forms.EmailField(
        label="E-mail", max_length=EMAIL_MAX,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )


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
        senha, confirmacao = dados.get("senha"), dados.get("senha2")
        if not senha:
            return dados
        if confirmacao and senha != confirmacao:
            self.add_error("senha2", "As senhas não são iguais.")
        elif confirmacao:
            self._validar_forca(senha, dados)
        return dados

    def _validar_forca(self, senha, dados):
        candidato = User(username=dados.get("email", ""), email=dados.get("email", ""), first_name=dados.get("nome", ""))
        try:
            validate_password(senha, candidato)
        except forms.ValidationError as erro:
            self.add_error("senha", erro)

    def save(self):
        dados = self.cleaned_data
        return criar_usuario(nome=dados["nome"], email=dados["email"], senha=dados["senha"])
