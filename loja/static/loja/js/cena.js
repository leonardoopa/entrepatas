import { $, $$, reduzMovimento } from './dom.js';

const MARGEM_PX = 12;

const limitar = (valor, minimo, maximo) => Math.min(maximo, Math.max(minimo, valor));

function iniciarCena(cena) {
  const palco = $('.cena__palco', cena);
  const topo = $('.topo');
  let agendado = false;

  const atualizar = () => {
    agendado = false;
    const alturaTopo = (topo ? topo.getBoundingClientRect().height : 0) + MARGEM_PX;
    cena.style.setProperty('--topo', `${alturaTopo}px`);
    const distancia = cena.offsetHeight - palco.offsetHeight;
    const progresso = distancia > 0 ? limitar((alturaTopo - cena.getBoundingClientRect().top) / distancia, 0, 1) : 1;
    cena.style.setProperty('--p', progresso.toFixed(4));
  };

  const agendar = () => {
    if (agendado) return;
    agendado = true;
    requestAnimationFrame(atualizar);
  };

  if (reduzMovimento) return;
  window.addEventListener('scroll', agendar, { passive: true });
  window.addEventListener('resize', agendar);
  atualizar();
}

export const iniciarCenas = () => $$('[data-cena]').forEach(iniciarCena);
