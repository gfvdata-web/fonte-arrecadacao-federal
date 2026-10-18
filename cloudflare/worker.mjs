// Worker do site: os estáticos vêm de docs/ (binding ASSETS). Só roda antes dos assets nas rotas de
// run_worker_first (wrangler.jsonc): /contagem.json, /skill/* e /dados/*.csv — o resto nem chega aqui.
import { atender } from "./contagem.mjs";

export default {
  async fetch(pedido, env, ctx) {
    return atender(pedido, {
      db: env.DOWNLOADS,
      site: env.SITE,
      servirArquivo: () => env.ASSETS.fetch(pedido),
      adiar: (promessa) => ctx.waitUntil(promessa),
    });
  },
};
