# EntrePatas

Pet shop online feito com Python, Django e SQL (PostgreSQL no Docker, SQLite para uso local sem Docker). Front-end em templates Django, CSS e JavaScript puro, sem React.

## Funcionalidades

- Catálogo por animal e departamento, busca com sugestões, filtros, ordenação e paginação
- Preço promocional, parcelamento sem juros, avaliações e frete grátis acima de um valor
- Carrinho em gaveta lateral e checkout que gera o pedido e baixa o estoque
- Contas de cliente: cadastro, login com e-mail e senha, recuperação de senha por e-mail e histórico de pedidos
- Painel administrativo (`/admin/`) para produtos, categorias, departamentos e pedidos

## Rodando com Docker (recomendado)

Pré-requisito: Docker com Docker Compose.

```bash
docker compose up --build
```

Abra http://localhost:8431. A primeira subida cria o banco PostgreSQL, aplica as migrações e carrega o catálogo de demonstração. O código fica montado do disco, então o servidor recarrega ao salvar arquivos.

Comandos úteis:

```bash
docker compose exec web python manage.py createsuperuser   # acesso ao /admin/
docker compose exec web python manage.py test              # testes
docker compose exec web python manage.py seed --limpar     # recarrega o catálogo de demonstração
docker compose logs -f web                                 # logs (inclusive e-mails de recuperação de senha)
docker compose down                                        # para tudo (o banco é mantido)
docker compose down -v                                     # para tudo e apaga o banco
```

Para mudar a porta ou outras opções, copie `.env.example` para `.env`.

### E-mail de recuperação de senha

Sem configuração de SMTP, o e-mail com o link de recuperação é impresso no log (`docker compose logs web`). Para enviar e-mails de verdade, defina `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_USER`, `DJANGO_EMAIL_PASSWORD` e `DJANGO_DEFAULT_FROM_EMAIL` no `.env`. O link vale por 2 horas e só funciona uma vez.

## Produção / staging

Use o compose sem o arquivo de desenvolvimento (ele roda gunicorn, sem DEBUG):

```bash
cp .env.example .env     # preencha as variáveis abaixo
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml exec web python manage.py createsuperuser
```

| Variável | Para quê |
| --- | --- |
| `DJANGO_SECRET_KEY` | chave longa e aleatória (obrigatória sem DEBUG) |
| `DJANGO_ALLOWED_HOSTS` | domínios do site, ex.: `www.entrepatas.com,entrepatas.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | origens com https, ex.: `https://www.entrepatas.com` |
| `DJANGO_HTTPS=1` | site atrás de proxy HTTPS: cookies seguros |
| `POSTGRES_PASSWORD` | senha do banco (o padrão `entrepatas-dev` serve só para desenvolvimento) |
| `DJANGO_SEED=1` | carrega o catálogo de demonstração ao iniciar (não use em produção real) |

O container escuta na porta 8000 e não faz HTTPS: coloque um proxy (Caddy, Nginx, Traefik ou o do provedor) na frente para o certificado do domínio. Fotos enviadas pelo admin ficam no volume `media`.

## Sem Docker

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Usa SQLite (`db.sqlite3`) quando `POSTGRES_DB` não está definido.

## Identidade visual

Azul `#17375E`, amarelo `#F2B544`, creme `#FFF9EE`. Os arquivos do logotipo ficam em `loja/static/loja/` (`logo.png` para fundo azul, `icone.png`, `favicon.png`, `apple-touch-icon.png`).
