import { $, $$ } from './dom.js';

const gaveta = $('[data-gaveta]');
const fundo = $('.gaveta-fundo');
const corpo = $('[data-gaveta-corpo]');
let focoAnterior = null;

export const gavetaDisponivel = () => Boolean(gaveta);
export const gavetaContem = (elemento) => gaveta.contains(elemento);
export const definirConteudoGaveta = (html) => { corpo.innerHTML = html; };
export const gavetaAberta = () => gaveta.classList.contains('is-aberta');

export function abrirGaveta() {
  focoAnterior = document.activeElement;
  fundo.hidden = false;
  gaveta.classList.add('is-aberta');
  gaveta.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  $('.gaveta__fechar', gaveta)?.focus();
}

export function fecharGaveta() {
  gaveta.classList.remove('is-aberta');
  gaveta.setAttribute('aria-hidden', 'true');
  fundo.hidden = true;
  document.body.style.overflow = '';
  focoAnterior?.focus();
}

export function iniciarGaveta() {
  if (!gaveta) return;
  $$('[data-gaveta-fechar]').forEach((el) => el.addEventListener('click', fecharGaveta));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && gavetaAberta()) fecharGaveta();
  });
}
