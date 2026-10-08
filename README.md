# EntrePatas

Pet shop online feito com Python, Django e SQL (SQLite em desenvolvimento). Front-end em templates Django e CSS puro, sem React.

## Funcionalidades

- Catálogo com categorias, busca, ordenação e página de produto
- Preço promocional e selo de desconto
- Carrinho na sessão e checkout que gera o pedido e baixa o estoque
- Painel administrativo (`/admin/`) para produtos, categorias e pedidos

## Como rodar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed            # dados de exemplo
.venv/bin/python manage.py createsuperuser # acesso ao /admin/
.venv/bin/python manage.py runserver
```

Testes: `.venv/bin/python manage.py test`

## Produção

Variáveis de ambiente:

| Variável | Exemplo |
| --- | --- |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | string longa e aleatória |
| `DJANGO_ALLOWED_HOSTS` | `www.seudominio.com,seudominio.com` |

Em produção troque o SQLite por PostgreSQL ou MySQL em `DATABASES` (`config/settings.py`), rode `collectstatic` e sirva com gunicorn atrás de um proxy HTTPS.

## Identidade visual

Azul `#17375E`, amarelo `#F2B544`, creme `#FFF9EE`. O logotipo ainda não está no projeto: salve os arquivos em `loja/static/loja/` e referencie em `loja/templates/loja/base.html`.
