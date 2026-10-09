# EntrePatas

Pet shop online feito com Python, Django e SQL (PostgreSQL no Docker, SQLite para uso local sem Docker). Front-end em templates Django, CSS e JavaScript puro, sem React.

## Funcionalidades

- Catálogo por animal e departamento, busca com sugestões, filtros, ordenação e paginação
- Preço promocional, parcelamento sem juros, avaliações e frete grátis acima de um valor
- Carrinho em gaveta lateral e checkout que gera o pedido e baixa o estoque
- Contas de cliente: cadastro, login com e-mail e senha, recuperação de senha por e-mail e histórico de pedidos
- Painel administrativo (`/admin/`) para produtos, categorias, departamentos e pedidos

## Arquitetura

```
loja/
  models/        entidades e regras simples do domínio (catalogo.py, pedidos.py)
  selectors/     consultas de leitura (filtros, busca, menu, destaques)
  services/      regras de negócio: carrinho, frete, resumo de compra, checkout, contas
  views/         camada HTTP fina: lê a requisição, chama services/selectors, devolve a resposta
  forms.py       validação de entrada
  signals.py     logs de autenticação
  templates/, static/loja/js/   interface (JavaScript em módulos, sem bibliotecas)
config/          settings e configuração de logs
```

Regras de dependência: `views` dependem de `services` e `selectors`; `services` e `selectors` dependem de `models`; nada em `services` conhece `request`, `HttpResponse` ou templates.

- **Responsabilidade única:** cada módulo faz uma coisa (o carrinho guarda itens, o resumo calcula totais, o checkout cria o pedido).
- **Aberto/fechado e inversão de dependência:** o frete é uma `PoliticaFrete` injetada em `montar_resumo` e `finalizar_pedido`. Para outra regra de frete basta criar uma nova classe com `calcular()`, sem mexer nas views nem no checkout.
- **Testes:** `loja/tests/` tem um módulo por área; os serviços são testados sem passar pelas views.

## Fotos reais na cena da home

A cena "Tudo para cães e gatos" usa desenhos por padrão. Para usar fotos de verdade:

1. Junte pelo menos 6 fotos por animal (12 é o ideal) e coloque em `fotos-originais/caes` e `fotos-originais/gatos`. Use apenas fotos que você tem direito de usar (suas, do cliente ou de bancos com licença comercial, como Unsplash, Pexels e Pixabay). Imagens de memes têm dono e não devem ser usadas.
2. Rode o preparo, que recorta em quadrado, reduz e converte para WebP:

```bash
docker compose exec web python manage.py preparar_fotos_cena fotos-originais/caes caes
docker compose exec web python manage.py preparar_fotos_cena fotos-originais/gatos gatos
```

As fotos vão para `loja/static/loja/cena/<animal>/` e aparecem na home como adesivos redondos. Com menos de 6 fotos de um lado, esse lado continua com os desenhos.

## Logs

Os logs vão para a saída padrão (`docker compose logs -f web`) no formato `data nível logger evento chave=valor`. O nível vem de `DJANGO_LOG_LEVEL` (padrão `INFO`; use `DEBUG` para ver cada alteração do carrinho).

| Evento | Nível |
| --- | --- |
| `pedido_criado`, `usuario_criado`, `login_ok`, `logout`, `senha_redefinida`, `recuperacao_senha_solicitada`, `carrinho_produto_adicionado`, `busca_sem_resultado` | INFO |
| `login_falhou`, `checkout_item_indisponivel`, `carrinho_produto_sem_estoque`, `pedido_acesso_negado`, `seed_limpeza` | WARNING |
| `carrinho_item_definido`, `carrinho_item_removido` | DEBUG |

Os logs guardam ids, IP e termos de busca sem resultado; nunca e-mails de contas, senhas ou tokens.

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
