import { $ } from './dom.js';

const ESPERA_MS = 200;
const TAMANHO_MINIMO = 2;

function criarSugestao(produto) {
  const link = document.createElement('a');
  link.className = 'sugestao';
  link.href = produto.url;

  const arte = document.createElement('span');
  arte.className = 'sugestao__arte';
  arte.innerHTML = produto.arte;

  const nome = document.createElement('span');
  nome.className = 'sugestao__nome';
  nome.textContent = produto.nome;
  if (produto.marca) {
    const marca = document.createElement('small');
    marca.textContent = produto.marca;
    nome.appendChild(marca);
  }

  const preco = document.createElement('span');
  preco.className = 'sugestao__preco';
  preco.textContent = `R$ ${produto.preco}`;

  link.append(arte, nome, preco);
  return link;
}

export function iniciarBusca() {
  const campo = $('[data-busca]');
  const caixa = $('[data-sugestoes]');
  if (!campo || !caixa) return;

  const urlSugestoes = document.body.dataset.urlSugestoes;
  let espera = null;
  let requisicao = null;
  let itens = [];
  let foco = -1;

  const fechar = () => { caixa.hidden = true; caixa.textContent = ''; itens = []; foco = -1; };

  const marcar = (indice) => {
    itens.forEach((item, i) => item.classList.toggle('is-foco', i === indice));
    foco = indice;
  };

  function desenhar(produtos, termo) {
    caixa.textContent = '';
    if (!produtos.length) {
      const vazio = document.createElement('div');
      vazio.className = 'sugestoes__vazio';
      vazio.textContent = 'Nenhum produto encontrado.';
      caixa.appendChild(vazio);
    }
    itens = produtos.map(criarSugestao);
    caixa.append(...itens);

    const todos = document.createElement('a');
    todos.className = 'sugestoes__todos';
    todos.href = `${campo.form.action}?q=${encodeURIComponent(termo)}`;
    todos.textContent = 'Ver todos os resultados';
    caixa.appendChild(todos);
    itens.push(todos);

    foco = -1;
    caixa.hidden = false;
  }

  function buscar(termo) {
    requisicao?.abort();
    requisicao = new AbortController();
    fetch(`${urlSugestoes}?q=${encodeURIComponent(termo)}`, { signal: requisicao.signal })
      .then((resposta) => resposta.json())
      .then((dados) => { if (campo.value.trim() === termo) desenhar(dados.itens, termo); })
      .catch(() => {});
  }

  campo.addEventListener('input', () => {
    clearTimeout(espera);
    const termo = campo.value.trim();
    if (termo.length < TAMANHO_MINIMO) return fechar();
    espera = setTimeout(() => buscar(termo), ESPERA_MS);
  });

  campo.addEventListener('keydown', (e) => {
    if (caixa.hidden) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); marcar((foco + 1) % itens.length); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); marcar((foco - 1 + itens.length) % itens.length); }
    else if (e.key === 'Enter' && foco >= 0) { e.preventDefault(); itens[foco].click(); }
    else if (e.key === 'Escape') fechar();
  });

  document.addEventListener('click', (e) => {
    if (!caixa.contains(e.target) && e.target !== campo) fechar();
  });
}
