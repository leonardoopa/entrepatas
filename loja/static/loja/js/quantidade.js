import { $, $$ } from './dom.js';

const ESPERA_ENVIO_MS = 450;

function iniciarSeletor(seletor) {
  const campo = $('input', seletor);
  $$('[data-step]', seletor).forEach((botao) => {
    botao.addEventListener('click', () => {
      const minimo = campo.min === '' ? 0 : Number(campo.min);
      const maximo = campo.max === '' ? Infinity : Number(campo.max);
      const valor = Math.min(maximo, Math.max(minimo, (Number(campo.value) || 0) + Number(botao.dataset.step)));
      if (valor === Number(campo.value)) return;
      campo.value = valor;
      campo.dispatchEvent(new Event('change', { bubbles: true }));
    });
  });
}

function enviarAoAlterar(form) {
  let espera = null;
  form.addEventListener('change', () => {
    clearTimeout(espera);
    espera = setTimeout(() => form.submit(), ESPERA_ENVIO_MS);
  });
}

export function iniciarQuantidade() {
  $$('[data-stepper]').forEach(iniciarSeletor);
  $$('[data-auto-form]').forEach(enviarAoAlterar);
}
