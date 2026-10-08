import { $, $$ } from './dom.js';

export function iniciarFiltros() {
  $$('[data-auto-enviar]').forEach((campo) => {
    campo.addEventListener('change', () => (campo.form || $('#filtros')).submit());
  });
  const botao = $('[data-filtros-toggle]');
  const painel = $('[data-filtros]');
  if (botao && painel) botao.addEventListener('click', () => painel.classList.toggle('is-aberto'));
}
