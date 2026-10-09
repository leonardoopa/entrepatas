import { $$ } from './dom.js';

function iniciarAbas(abas) {
  const botoes = $$('[data-aba]', abas);
  const paineis = $$('[data-painel]', abas);
  botoes.forEach((botao) => {
    botao.addEventListener('click', () => {
      botoes.forEach((outro) => {
        const ativo = outro === botao;
        outro.classList.toggle('is-ativo', ativo);
        outro.setAttribute('aria-selected', String(ativo));
      });
      paineis.forEach((painel) => {
        const ativo = painel.dataset.painel === botao.dataset.aba;
        painel.hidden = !ativo;
        painel.classList.toggle('is-ativo', ativo);
      });
    });
  });
}

export const iniciarTodasAbas = () => $$('[data-abas]').forEach(iniciarAbas);
