import { $, $$, reduzMovimento } from './dom.js';

const PASSO = 0.9;
const FOLGA_PX = 4;

function iniciarCarrossel(carrossel) {
  const pista = $('.carrossel__pista', carrossel);
  const anterior = $('.carrossel__seta--ant', carrossel);
  const proxima = $('.carrossel__seta--prox', carrossel);

  const atualizar = () => {
    anterior.disabled = pista.scrollLeft <= FOLGA_PX;
    proxima.disabled = pista.scrollLeft + pista.clientWidth >= pista.scrollWidth - FOLGA_PX;
  };

  [anterior, proxima].forEach((seta) => {
    seta.addEventListener('click', () => {
      pista.scrollBy({
        left: Number(seta.dataset.dir) * pista.clientWidth * PASSO,
        behavior: reduzMovimento ? 'auto' : 'smooth',
      });
    });
  });
  pista.addEventListener('scroll', atualizar, { passive: true });
  window.addEventListener('resize', atualizar);
  atualizar();
}

export const iniciarCarrosseis = () => $$('[data-carrossel]').forEach(iniciarCarrossel);
