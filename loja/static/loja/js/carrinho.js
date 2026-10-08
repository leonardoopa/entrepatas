import { $$ } from './dom.js';
import {
  abrirGaveta, definirConteudoGaveta, gavetaContem, gavetaDisponivel,
} from './gaveta.js';
import { toast } from './toast.js';

const CABECALHOS = { 'X-Requested-With': 'XMLHttpRequest' };

function atualizarContador(quantidade) {
  $$('[data-carrinho-qtd]').forEach((selo) => {
    selo.textContent = quantidade;
    selo.hidden = !quantidade;
    selo.classList.remove('pulo');
    void selo.offsetWidth; // reinicia a animação
    selo.classList.add('pulo');
  });
}

function abrirCarrinho(link, evento) {
  if (evento.metaKey || evento.ctrlKey || evento.shiftKey) return;
  evento.preventDefault();
  definirConteudoGaveta('Carregando…');
  abrirGaveta();
  fetch(document.body.dataset.urlMinicarrinho, { headers: CABECALHOS })
    .then((resposta) => resposta.json())
    .then((dados) => definirConteudoGaveta(dados.html))
    .catch(() => { window.location = link.href; });
}

function enviarSemRecarregar(form) {
  const botao = form.querySelector('button[type="submit"]');
  if (botao) botao.disabled = true;
  const dentroDaGaveta = gavetaContem(form);

  fetch(form.action, { method: 'POST', body: new FormData(form), headers: CABECALHOS })
    .then((resposta) => resposta.json())
    .then((dados) => {
      atualizarContador(dados.qtd);
      definirConteudoGaveta(dados.html);
      toast(dados.mensagem, !dados.ok);
      if (dados.ok && !dentroDaGaveta) abrirGaveta();
    })
    .catch(() => form.submit())
    .then(() => { if (botao) botao.disabled = false; });
}

export function iniciarCarrinho() {
  if (!gavetaDisponivel()) return;
  $$('[data-abrir-carrinho]').forEach((link) => {
    link.addEventListener('click', (evento) => abrirCarrinho(link, evento));
  });
  document.addEventListener('submit', (evento) => {
    if (!evento.target.matches('[data-ajax-carrinho]')) return;
    evento.preventDefault();
    enviarSemRecarregar(evento.target);
  });
}
