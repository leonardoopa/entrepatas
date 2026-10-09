import { $ } from './dom.js';

const DURACAO_MS = 3500;
const SAIDA_MS = 300;

export function toast(mensagem, erro = false) {
  const caixa = $('[data-toasts]');
  if (!caixa || !mensagem) return;
  const aviso = document.createElement('div');
  aviso.className = 'toast' + (erro ? ' toast--erro' : '');
  aviso.textContent = mensagem;
  caixa.appendChild(aviso);
  setTimeout(() => {
    aviso.classList.add('saindo');
    setTimeout(() => aviso.remove(), SAIDA_MS);
  }, DURACAO_MS);
}
