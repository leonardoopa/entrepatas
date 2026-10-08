import { iniciarTodasAbas } from './abas.js';
import { iniciarBusca } from './busca.js';
import { iniciarCarrinho } from './carrinho.js';
import { iniciarCarrosseis } from './carrossel.js';
import { iniciarCenas } from './cena.js';
import { iniciarFiltros } from './filtros.js';
import { iniciarGaveta } from './gaveta.js';
import { iniciarHeros } from './hero.js';
import { iniciarMenu } from './menu.js';
import { iniciarQuantidade } from './quantidade.js';
import { iniciarRevelar } from './revelar.js';

[
  iniciarMenu,
  iniciarHeros,
  iniciarCarrosseis,
  iniciarCenas,
  iniciarBusca,
  iniciarGaveta,
  iniciarCarrinho,
  iniciarQuantidade,
  iniciarFiltros,
  iniciarTodasAbas,
  iniciarRevelar,
].forEach((iniciar) => iniciar());
