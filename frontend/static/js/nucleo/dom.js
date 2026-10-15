export const $ = (seletor, contexto = document) => contexto.querySelector(seletor);
export const $$ = (seletor, contexto = document) => Array.from(contexto.querySelectorAll(seletor));
export const reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
