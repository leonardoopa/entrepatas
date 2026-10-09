import { $$, reduzMovimento } from './dom.js';

const ALVOS = '.secao, .vantagens, .animal, .abas';

function aparecer(elemento) {
  elemento.classList.add('visivel');
  elemento.addEventListener('transitionend', () => elemento.classList.remove('revelar', 'visivel'), { once: true });
}

export function iniciarRevelar() {
  if (reduzMovimento || !('IntersectionObserver' in window)) return;
  const observador = new IntersectionObserver((entradas) => {
    entradas.forEach((entrada) => {
      if (!entrada.isIntersecting) return;
      aparecer(entrada.target);
      observador.unobserve(entrada.target);
    });
  }, { threshold: 0.12 });

  $$(ALVOS).forEach((elemento, indice) => {
    elemento.style.setProperty('--ordem', indice % 5);
    elemento.classList.add('revelar');
    observador.observe(elemento);
  });
}
