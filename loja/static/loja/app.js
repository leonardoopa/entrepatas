/* EntrePatas — interações da loja (JavaScript puro, sem dependências). */
(function () {
  'use strict';

  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };
  var reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- Toasts ----------
  function toast(msg, erro) {
    var box = $('[data-toasts]');
    if (!box || !msg) return;
    var el = document.createElement('div');
    el.className = 'toast' + (erro ? ' toast--erro' : '');
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(function () {
      el.classList.add('saindo');
      setTimeout(function () { el.remove(); }, 300);
    }, 3500);
  }

  // ---------- Menu mobile ----------
  var menuBtn = $('[data-menu-toggle]');
  var menu = $('[data-menu]');
  if (menuBtn && menu) {
    menuBtn.addEventListener('click', function () {
      var aberto = menu.classList.toggle('is-aberto');
      menuBtn.setAttribute('aria-expanded', String(aberto));
    });
  }

  // ---------- Hero (carrossel de banners) ----------
  var TEMPO_HERO = 3500; // ms entre os slides

  $$('[data-hero]').forEach(function (hero) {
    var trilho = $('.hero__trilho', hero);
    var slides = $$('.hero__slide', hero);
    var caixaPontos = $('.hero__pontos', hero);
    var atual = 0, timer = null;

    hero.style.setProperty('--tempo', TEMPO_HERO + 'ms');
    var pontos = slides.map(function (_, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-label', 'Ir para o slide ' + (i + 1));
      b.addEventListener('click', function () { ir(i); iniciar(); });
      caixaPontos.appendChild(b);
      return b;
    });

    function ir(n) {
      atual = (n + slides.length) % slides.length;
      trilho.style.transform = 'translateX(' + (-atual * 100) + '%)';
      slides.forEach(function (s, i) {
        s.classList.toggle('is-ativo', i === atual);
        s.setAttribute('aria-hidden', String(i !== atual));
      });
      pontos.forEach(function (p, i) {
        p.classList.remove('is-ativo');
        if (i === atual) { void p.offsetWidth; p.classList.add('is-ativo'); } // reinicia a barra de progresso
      });
    }
    function iniciar() {
      parar();
      if (reduzMovimento || slides.length < 2) return;
      timer = setInterval(function () { ir(atual + 1); }, TEMPO_HERO);
    }
    function parar() { if (timer) { clearInterval(timer); timer = null; } }

    $$('.hero__seta', hero).forEach(function (b) {
      b.addEventListener('click', function () { ir(atual + Number(b.dataset.dir)); iniciar(); });
    });
    hero.addEventListener('mouseenter', parar);
    hero.addEventListener('mouseleave', iniciar);
    hero.addEventListener('focusin', parar);
    hero.addEventListener('focusout', iniciar);

    // Arrastar para trocar de slide (toque e mouse).
    var inicioX = null;
    hero.addEventListener('pointerdown', function (e) { inicioX = e.clientX; });
    hero.addEventListener('pointerup', function (e) {
      if (inicioX === null) return;
      var dx = e.clientX - inicioX;
      inicioX = null;
      if (Math.abs(dx) > 50) { ir(atual + (dx < 0 ? 1 : -1)); iniciar(); }
    });
    hero.addEventListener('pointercancel', function () { inicioX = null; });

    ir(0);
    iniciar();
  });

  // ---------- Carrosséis de produtos ----------
  $$('[data-carrossel]').forEach(function (car) {
    var pista = $('.carrossel__pista', car);
    var ant = $('.carrossel__seta--ant', car);
    var prox = $('.carrossel__seta--prox', car);

    function atualizar() {
      ant.disabled = pista.scrollLeft <= 4;
      prox.disabled = pista.scrollLeft + pista.clientWidth >= pista.scrollWidth - 4;
    }
    [ant, prox].forEach(function (b) {
      b.addEventListener('click', function () {
        pista.scrollBy({ left: Number(b.dataset.dir) * pista.clientWidth * 0.9, behavior: reduzMovimento ? 'auto' : 'smooth' });
      });
    });
    pista.addEventListener('scroll', atualizar, { passive: true });
    window.addEventListener('resize', atualizar);
    atualizar();
  });

  // ---------- Busca com sugestões ----------
  var campo = $('[data-busca]');
  var caixa = $('[data-sugestoes]');
  if (campo && caixa) {
    var urlSugestoes = document.body.dataset.urlSugestoes;
    var espera = null, req = null, itens = [], foco = -1;

    var fechar = function () { caixa.hidden = true; caixa.textContent = ''; itens = []; foco = -1; };

    var marcar = function (i) {
      itens.forEach(function (el, n) { el.classList.toggle('is-foco', n === i); });
      foco = i;
    };

    var desenhar = function (lista, termo) {
      caixa.textContent = '';
      itens = [];
      if (!lista.length) {
        var vazio = document.createElement('div');
        vazio.className = 'sugestoes__vazio';
        vazio.textContent = 'Nenhum produto encontrado.';
        caixa.appendChild(vazio);
      }
      lista.forEach(function (p) {
        var a = document.createElement('a');
        a.className = 'sugestao';
        a.href = p.url;
        var arte = document.createElement('span');
        arte.className = 'sugestao__arte';
        arte.innerHTML = p.arte; // HTML gerado e escapado pelo servidor
        var nome = document.createElement('span');
        nome.className = 'sugestao__nome';
        nome.textContent = p.nome;
        if (p.marca) {
          var marca = document.createElement('small');
          marca.textContent = p.marca;
          nome.appendChild(marca);
        }
        var preco = document.createElement('span');
        preco.className = 'sugestao__preco';
        preco.textContent = 'R$ ' + p.preco;
        a.appendChild(arte); a.appendChild(nome); a.appendChild(preco);
        caixa.appendChild(a);
        itens.push(a);
      });
      var todos = document.createElement('a');
      todos.className = 'sugestoes__todos';
      todos.href = campo.form.action + '?q=' + encodeURIComponent(termo);
      todos.textContent = 'Ver todos os resultados';
      caixa.appendChild(todos);
      itens.push(todos);
      foco = -1;
      caixa.hidden = false;
    };

    campo.addEventListener('input', function () {
      clearTimeout(espera);
      var termo = campo.value.trim();
      if (termo.length < 2) { fechar(); return; }
      espera = setTimeout(function () {
        if (req) req.abort();
        req = new AbortController();
        fetch(urlSugestoes + '?q=' + encodeURIComponent(termo), { signal: req.signal })
          .then(function (r) { return r.json(); })
          .then(function (d) { if (campo.value.trim() === termo) desenhar(d.itens, termo); })
          .catch(function () {});
      }, 200);
    });

    campo.addEventListener('keydown', function (e) {
      if (caixa.hidden) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); marcar((foco + 1) % itens.length); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); marcar((foco - 1 + itens.length) % itens.length); }
      else if (e.key === 'Enter' && foco >= 0) { e.preventDefault(); itens[foco].click(); }
      else if (e.key === 'Escape') { fechar(); }
    });
    document.addEventListener('click', function (e) {
      if (!caixa.contains(e.target) && e.target !== campo) fechar();
    });
  }

  // ---------- Gaveta (mini-carrinho) ----------
  var gaveta = $('[data-gaveta]');
  var fundo = $('.gaveta-fundo');
  var corpo = $('[data-gaveta-corpo]');
  var ultimoFoco = null;

  function atualizarContador(qtd) {
    $$('[data-carrinho-qtd]').forEach(function (b) {
      b.textContent = qtd;
      b.hidden = !qtd;
      b.classList.remove('pulo');
      void b.offsetWidth; // reinicia a animação
      b.classList.add('pulo');
    });
  }

  function abrirGaveta() {
    if (!gaveta) return;
    ultimoFoco = document.activeElement;
    fundo.hidden = false;
    gaveta.classList.add('is-aberta');
    gaveta.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    var fechar = $('.gaveta__fechar', gaveta);
    if (fechar) fechar.focus();
  }
  function fecharGaveta() {
    if (!gaveta) return;
    gaveta.classList.remove('is-aberta');
    gaveta.setAttribute('aria-hidden', 'true');
    fundo.hidden = true;
    document.body.style.overflow = '';
    if (ultimoFoco) ultimoFoco.focus();
  }
  $$('[data-gaveta-fechar]').forEach(function (el) { el.addEventListener('click', fecharGaveta); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && gaveta && gaveta.classList.contains('is-aberta')) fecharGaveta();
  });

  $$('[data-abrir-carrinho]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || !gaveta) return;
      e.preventDefault();
      corpo.textContent = 'Carregando…';
      abrirGaveta();
      fetch(document.body.dataset.urlMinicarrinho, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (r) { return r.json(); })
        .then(function (d) { corpo.innerHTML = d.html; })
        .catch(function () { window.location = link.href; });
    });
  });

  // ---------- Carrinho sem recarregar a página ----------
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.matches('[data-ajax-carrinho]') || !gaveta) return;
    e.preventDefault();
    var botao = $('button[type="submit"]', form);
    if (botao) botao.disabled = true;
    var dentroDaGaveta = gaveta.contains(form);

    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        atualizarContador(d.qtd);
        corpo.innerHTML = d.html;
        toast(d.mensagem, !d.ok);
        if (d.ok && !dentroDaGaveta) abrirGaveta();
      })
      .catch(function () { form.submit(); }) // sem JSON válido: segue o fluxo normal
      .then(function () { if (botao) botao.disabled = false; });
  });

  // ---------- Seletor de quantidade ----------
  $$('[data-stepper]').forEach(function (st) {
    var input = $('input', st);
    $$('[data-step]', st).forEach(function (b) {
      b.addEventListener('click', function () {
        var min = input.min === '' ? 0 : Number(input.min);
        var max = input.max === '' ? Infinity : Number(input.max);
        var novo = Math.min(max, Math.max(min, (Number(input.value) || 0) + Number(b.dataset.step)));
        if (novo !== Number(input.value)) {
          input.value = novo;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    });
  });
  $$('[data-auto-form]').forEach(function (form) {
    var espera = null;
    form.addEventListener('change', function () {
      clearTimeout(espera);
      espera = setTimeout(function () { form.submit(); }, 450);
    });
  });

  // ---------- Filtros ----------
  $$('[data-auto-enviar]').forEach(function (el) {
    el.addEventListener('change', function () { (el.form || $('#filtros')).submit(); });
  });
  var filtrosBtn = $('[data-filtros-toggle]');
  var filtros = $('[data-filtros]');
  if (filtrosBtn && filtros) {
    filtrosBtn.addEventListener('click', function () { filtros.classList.toggle('is-aberto'); });
  }

  // ---------- Abas ----------
  $$('[data-abas]').forEach(function (abas) {
    var botoes = $$('[data-aba]', abas);
    var paineis = $$('[data-painel]', abas);
    botoes.forEach(function (b) {
      b.addEventListener('click', function () {
        botoes.forEach(function (x) {
          var ativo = x === b;
          x.classList.toggle('is-ativo', ativo);
          x.setAttribute('aria-selected', String(ativo));
        });
        paineis.forEach(function (p) {
          var ativo = p.dataset.painel === b.dataset.aba;
          p.hidden = !ativo;
          p.classList.toggle('is-ativo', ativo);
        });
      });
    });
  });
})();
