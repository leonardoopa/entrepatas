import { $, $$, reduzMovimento } from './dom.js';

const INTERVALO_MS = 3500;
const DISTANCIA_MINIMA_ARRASTO = 50;

function iniciarHero(hero) {
  const trilho = $('.hero__trilho', hero);
  const slides = $$('.hero__slide', hero);
  const caixaPontos = $('.hero__pontos', hero);
  let atual = 0;
  let timer = null;

  hero.style.setProperty('--tempo', `${INTERVALO_MS}ms`);

  const pontos = slides.map((_, indice) => {
    const ponto = document.createElement('button');
    ponto.type = 'button';
    ponto.setAttribute('aria-label', `Ir para o slide ${indice + 1}`);
    ponto.addEventListener('click', () => { irPara(indice); reiniciar(); });
    caixaPontos.appendChild(ponto);
    return ponto;
  });

  function irPara(indice) {
    atual = (indice + slides.length) % slides.length;
    trilho.style.transform = `translateX(${-atual * 100}%)`;
    slides.forEach((slide, i) => {
      slide.classList.toggle('is-ativo', i === atual);
      slide.setAttribute('aria-hidden', String(i !== atual));
    });
    pontos.forEach((ponto, i) => {
      ponto.classList.remove('is-ativo');
      if (i === atual) {
        void ponto.offsetWidth; // força o reflow para reiniciar a animação de progresso
        ponto.classList.add('is-ativo');
      }
    });
  }

  const parar = () => { clearInterval(timer); timer = null; };
  const iniciar = () => {
    parar();
    if (!reduzMovimento && slides.length > 1) timer = setInterval(() => irPara(atual + 1), INTERVALO_MS);
  };
  const reiniciar = iniciar;

  $$('.hero__seta', hero).forEach((seta) => {
    seta.addEventListener('click', () => { irPara(atual + Number(seta.dataset.dir)); reiniciar(); });
  });
  hero.addEventListener('mouseenter', parar);
  hero.addEventListener('mouseleave', iniciar);
  hero.addEventListener('focusin', parar);
  hero.addEventListener('focusout', iniciar);

  let inicioX = null;
  hero.addEventListener('pointerdown', (e) => { inicioX = e.clientX; });
  hero.addEventListener('pointercancel', () => { inicioX = null; });
  hero.addEventListener('pointerup', (e) => {
    if (inicioX === null) return;
    const deslocamento = e.clientX - inicioX;
    inicioX = null;
    if (Math.abs(deslocamento) > DISTANCIA_MINIMA_ARRASTO) {
      irPara(atual + (deslocamento < 0 ? 1 : -1));
      reiniciar();
    }
  });

  irPara(0);
  iniciar();
}

export const iniciarHeros = () => $$('[data-hero]').forEach(iniciarHero);
