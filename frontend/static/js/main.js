import { iniciarTodasAbas } from './componentes/abas.js';
import { iniciarBusca } from './componentes/busca.js';
import { iniciarCarrinho } from './componentes/carrinho.js';
import { iniciarCarrosseis } from './componentes/carrossel.js';
import { iniciarGaveta } from './componentes/gaveta.js';
import { iniciarMenu } from './componentes/menu.js';
import { iniciarQuantidade } from './componentes/quantidade.js';
import { iniciarRevelar } from './componentes/revelar.js';
import { iniciarCenas } from './paginas/cena.js';
import { iniciarFiltros } from './paginas/filtros.js';
import { iniciarHeros } from './paginas/hero.js';

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
