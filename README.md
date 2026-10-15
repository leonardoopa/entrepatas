# EntrePatas

Site do pet shop online feito com Python e Django. Front-end em templates Django, CSS e JavaScript puro, sem React.

O site **não tem catálogo próprio**. Produtos, preços, estoque, vitrines da home e pedidos vivem no [backoffice](../backoffice_entre_patas) e chegam por API REST. O banco do site guarda apenas contas de clientes e sessões.

```
Navegador ──► Site (Django) ──► API do backoffice (Bearer) ──► PostgreSQL do backoffice
```

## Funcionalidades

- Catálogo por animal e departamento, busca com sugestões, filtros, ordenação e paginação
- Página do produto com variações (tamanho ou peso), preço promocional, parcelamento sem juros e frete grátis acima de um valor
- Home com as vitrines definidas no backoffice (ofertas, mais vendidos, destaques)
- Carrinho em gaveta lateral e checkout que envia o pedido ao backoffice, que baixa o estoque
- Contas de cliente: cadastro, login com e-mail e senha, recuperação de senha por e-mail e "Meus pedidos" (lidos do backoffice)
- Página de manutenção (503) quando o backoffice está fora e não há cache

## Arquitetura (MVC)

O projeto separa o **back-end** (`loja/` e `config/`, só Python) do **front-end** (`frontend/`, só templates, CSS, JavaScript e imagens).

```
config/                    settings, urls raiz e configuração de logs
loja/                      back-end
  models/                  M: entidades do domínio (dataclasses) e erros de negócio, sem HTTP
  repositories/            M: acesso a dados
    contratos.py           contratos (Protocol) de catálogo e pedidos
    backoffice/            implementação: cliente HTTP, mapeamento JSON para models, cache, erros
    fabrica.py             monta os repositórios (obter_catalogo, obter_pedidos)
  services/                M: regras de negócio (carrinho, frete, resumo, checkout, contas, consulta do catálogo)
  controllers/             C: recebem a requisição, chamam services e repositories, escolhem o template
    forms.py               validação da entrada
    middleware.py          "backoffice fora do ar" vira a página 503
    signals.py             logs de autenticação
  presenters/              dados prontos para a tela (cena da home, menu e contador do carrinho)
  urls.py                  rotas da loja
  tests/                   espelha as camadas: controllers/, services/, repositories/, presenters/, support/
frontend/                  V: tudo o que o navegador recebe
  templates/
    layouts/               base, cabeçalho, menu, rodapé, gaveta do carrinho
    componentes/           peças reutilizáveis (card, carrossel, hero, cena, totais...)
    paginas/               uma pasta por área: catalogo, carrinho, checkout, contas, erros
    emails/                texto dos e-mails
  static/
    css/                   base.css, layout/, componentes/, paginas/
    js/                    main.js, nucleo/ (utilidades), componentes/, paginas/
    img/                   logotipo, ícones e fotos da cena
```

Regras de dependência (a seta aponta para quem é usado):

```
controllers -> services -> repositories -> models
controllers -> presenters -> services, repositories, models
repositories/backoffice implementa repositories/contratos
templates recebem o contexto pronto de controllers e presenters
```

- `models` não importa nada do projeto. `services` e `controllers` nunca falam com `requests`: só `repositories/backoffice/` conhece HTTP e JSON.
- Controllers e presenters pedem dados por `from loja.repositories import obter_catalogo, obter_pedidos`; não importam o adaptador.
- Nenhum service conhece `request`, `HttpResponse` ou templates. A leitura do `QueryDict` (filtros da listagem) fica no controller.
- Template não consulta nada: recebe tudo do controller ou dos presenters (`context_processors`).
- Cada CSS e cada JavaScript pertence a um componente ou a uma página, e as media queries ficam junto do componente. Para um estilo novo, crie o arquivo e liste-o em `frontend/templates/layouts/estilos.html`.
- **Inversão de dependência:** trocar o backoffice por outra fonte é escrever outra implementação dos contratos; controllers e services não mudam.
- **Aberto/fechado:** o frete é uma `PoliticaFrete` injetada em `montar_resumo` e `finalizar_pedido`.
- **Preço sempre do backoffice:** o site envia SKU e quantidade; o backoffice calcula o preço de cada item.
- **Pedido idempotente:** o número do pedido é gerado e guardado na sessão antes de chamar o backoffice. Se a resposta se perder, repetir o envio devolve o mesmo pedido, sem baixar o estoque duas vezes.
- **Cliente:** conta logada usa o id do usuário; visitante usa `visitante:<e-mail>`.

### Cache e queda do backoffice

Respostas de catálogo ficam em cache por 30 segundos (`BACKOFFICE_CACHE_SEGUNDOS`), então uma mudança de preço no backoffice aparece no site em até 30 segundos. Cada resposta também fica guardada por 1 hora: se o backoffice cair, o site continua servindo a última versão conhecida (log `catalogo_servido_do_cache_antigo`). Sem cache, a página mostra o aviso de manutenção com `503` e `Retry-After`. Leituras tentam de novo em caso de falha de rede; o envio de pedido não tenta de novo sozinho.

- **Testes:** `loja/tests/` espelha as camadas. Os testes usam um `BackofficeFalso` (`tests/support/fabricas.py`) que imita a API em memória; `tests/repositories/contrato/*.json` guarda respostas reais da API para garantir que o mapeamento continua válido.

## Fotos reais na cena da home

A cena "Tudo para cães e gatos" usa desenhos por padrão. Para usar fotos de verdade:

1. Junte pelo menos 6 fotos por animal (12 é o ideal) e coloque em `fotos-originais/caes` e `fotos-originais/gatos`. Use apenas fotos que você tem direito de usar (suas, do cliente ou de bancos com licença comercial, como Unsplash, Pexels e Pixabay). Imagens de memes têm dono e não devem ser usadas.
2. Rode o preparo, que recorta em quadrado, reduz e converte para WebP:

```bash
docker compose exec web python manage.py preparar_fotos_cena fotos-originais/caes caes
docker compose exec web python manage.py preparar_fotos_cena fotos-originais/gatos gatos
```

As fotos vão para `frontend/static/img/cena/<animal>/` e aparecem na home como adesivos redondos. Com menos de 6 fotos de um lado, esse lado continua com os desenhos.

## Logs

Os logs vão para a saída padrão (`docker compose logs -f web`) no formato `data nível logger evento chave=valor`. O nível vem de `DJANGO_LOG_LEVEL` (padrão `INFO`; use `DEBUG` para ver cada alteração do carrinho).

| Evento | Nível |
| --- | --- |
| `pedido_criado`, `usuario_criado`, `login_ok`, `logout`, `senha_redefinida`, `recuperacao_senha_solicitada`, `carrinho_produto_adicionado`, `busca_sem_resultado` | INFO |
| `login_falhou`, `checkout_item_indisponivel`, `checkout_recusado`, `carrinho_produto_sem_estoque`, `pedido_acesso_negado`, `backoffice_inacessivel`, `backoffice_recusou`, `catalogo_servido_do_cache_antigo`, `menu_indisponivel` | WARNING |
| `site_sem_backoffice` | ERROR |
| `carrinho_item_definido`, `carrinho_item_removido` | DEBUG |

Os logs guardam ids, IP e termos de busca sem resultado; nunca e-mails de contas, senhas nem a chave da API.

## Rodando com Docker (recomendado)

Pré-requisitos: Docker com Docker Compose e o **backoffice rodando** (porta 8500), porque o site não tem catálogo próprio.

1. Suba o backoffice (no projeto `backoffice_entre_patas`) e crie uma chave de API do site:

```bash
docker compose up -d --build
docker compose exec web python manage.py criar_chave_api site-dev site
```

A chave aparece uma única vez. No banco do backoffice fica só o hash.

2. No projeto do site, copie `.env.example` para `.env` e cole a chave em `BACKOFFICE_API_KEY` (o compose recusa subir sem ela). Depois:

```bash
docker compose up --build
```

Abra http://localhost:8431. A primeira subida cria o banco PostgreSQL do site e aplica as migrações. O código fica montado do disco, então o servidor recarrega ao salvar arquivos. O site fala com o backoffice em `http://host.docker.internal:8500/api/v1` (`BACKOFFICE_URL`).

Comandos úteis:

```bash
docker compose exec web python manage.py createsuperuser   # acesso ao /admin/ (só contas de clientes)
docker compose exec web python manage.py test              # testes (não precisam do backoffice)
docker compose logs -f web                                 # logs (inclusive e-mails de recuperação de senha)
docker compose down                                        # para tudo (o banco é mantido)
docker compose down -v                                     # para tudo e apaga o banco
```

Produtos, preços, estoque e vitrines se editam no backoffice (http://localhost:8500), não aqui.

### E-mail de recuperação de senha

Sem configuração de SMTP, o e-mail com o link de recuperação é impresso no log (`docker compose logs web`). Para enviar e-mails de verdade, defina `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_USER`, `DJANGO_EMAIL_PASSWORD` e `DJANGO_DEFAULT_FROM_EMAIL` no `.env`. O link vale por 2 horas e só funciona uma vez.

## Produção / staging

Use o compose sem o arquivo de desenvolvimento (ele roda gunicorn, sem DEBUG):

```bash
cp .env.example .env     # preencha as variáveis abaixo
docker compose -f docker-compose.yml up -d --build
```

| Variável | Para quê |
| --- | --- |
| `DJANGO_SECRET_KEY` | chave longa e aleatória (obrigatória sem DEBUG) |
| `DJANGO_ALLOWED_HOSTS` | domínios do site, ex.: `www.entrepatas.com,entrepatas.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | origens com https, ex.: `https://www.entrepatas.com` |
| `DJANGO_HTTPS=1` | site atrás de proxy HTTPS: cookies seguros |
| `POSTGRES_PASSWORD` | senha do banco (o padrão `entrepatas-dev` serve só para desenvolvimento) |
| `BACKOFFICE_URL` | URL da API do backoffice, ex.: `https://backoffice.entrepatas.com/api/v1` |
| `BACKOFFICE_API_KEY` | chave com escopo `site`, criada no backoffice (obrigatória) |
| `BACKOFFICE_TIMEOUT` | segundos de espera por resposta (padrão 5) |
| `BACKOFFICE_CACHE_SEGUNDOS` | validade do cache do catálogo (padrão 30) |

O container escuta na porta 8000 e não faz HTTPS: coloque um proxy (Caddy, Nginx, Traefik ou o do provedor) na frente para o certificado do domínio. Fotos enviadas pelo admin ficam no volume `media`.

## Sem Docker

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export BACKOFFICE_URL=http://localhost:8500/api/v1 BACKOFFICE_API_KEY=<chave>
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Usa SQLite (`db.sqlite3`) para contas e sessões quando `POSTGRES_DB` não está definido.

## Identidade visual

Azul `#17375E`, amarelo `#F2B544`, creme `#FFF9EE`. Os arquivos do logotipo ficam em `frontend/static/img/` (`logo.png` para fundo azul, `icone.png`, `favicon.png`, `apple-touch-icon.png`).
