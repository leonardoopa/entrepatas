import { $ } from './dom.js';

export function iniciarMenu() {
  const botao = $('[data-menu-toggle]');
  const menu = $('[data-menu]');
  if (!botao || !menu) return;
  botao.addEventListener('click', () => {
    const aberto = menu.classList.toggle('is-aberto');
    botao.setAttribute('aria-expanded', String(aberto));
  });
}
