# Handoff — Port advisian-djen → intimacoes

**Data**: 2026-04-17
**Status**: Sprint 1 de 4 concluída (~25%)
**Commit de estado**: `567240e` (push OK em `joaoguerini-FG/advisian` main)

---

## 🎯 Objetivo da série de sessões

Portar **TODAS** as melhorias do projeto `C:\Users\joaof\Documents\advisian-djen\`
(template público, desenvolvido em outra sessão) para o sistema proprietário
`C:\Users\joaof\Documents\intimacoes\` (produção FG, dashboard em
`https://joaoguerini-fg.github.io/advisian/`).

**Regra de ouro**: SOMAR, nunca substituir. O intimacoes tem IA (Opus 4.6 +
170 regras), DataJuri proprietário, auditoria INT-IDs — tudo isso FICA.

**Hierarquia de natureza** (definida pelo user):
1. DataJuri (prioritário) — quando enriquecimento OAuth der certo
2. DataJud (fallback) — classe processual do CNJ público
3. CNJ parsing (último fallback) — dígito J do número

---

## ✅ O que já foi feito (commit 567240e)

### S1.1 — `telemetria.py` estendida
Adicionadas sem quebrar o que existe:
- `registrar_execucao(nome_monitorado, total_capturado, novas, repetidas, duracao_segundos, janela_dias=None, enriquecido_datajuri=0, enriquecido_datajud=0, erros=0, log_path="telemetria_execucoes.jsonl")` — 1 registro por run
- `resumo_execucoes(log_path="telemetria_execucoes.jsonl")` — CLI --execucoes
- Preservadas: `registrar_classificacao`, `resumo`, `custo_por_mes`, `accuracy_vs_gt`

### S1.2 — `schemas.py` já tinha tudo
Verificado: `validar_publicacao_djen`, `validar_state_publicacao`,
`validar_classificacao_result`, etc. **Pulado** (nenhum port necessário).

### S1.3 — `captura_djen.py` NOVO (módulo)
- `capturar_publicacoes(filtros, janela_dias=2, hoje=None, verbose=True)` — multi-filtro
- `capturar_por_nome(nome, janela_dias=3, ...)` — wrapper compat advisian-djen
- Retry 3x automático + timeout 90s + backoff exponencial
- CLI: `python captura_djen.py --nome "..."` / `--oab XX --uf SP` / `--termo "..."`

### S1.4 — `enriquecimento_datajud.py` NOVO
- `enriquecer_publicacoes_datajud(pubs, cache_path="cache_datajud.json", max_workers=8, verbose=True, sobrepor_natureza_datajuri=False)` — modifica in-place, retorna stats
- Paralelo (ThreadPoolExecutor 8 workers), cache 7d TTL
- Campos adicionados às pubs: `datajud` (classe, assuntos, órgão, movimentos),
  `natureza_datajud`, `natureza_fonte` (`"datajuri"` ou `"datajud"`)
- API key pública CNJ embutida (`DJ_KEY_PUBLICA`)
- STF filtrado (sem endpoint DataJud público)

---

## ⏳ O que falta fazer

### S1.5 — Integrar DataJud no `pipeline_diario.py`
Etapa 3 (ou nova 2.5) do pipeline deve chamar `enriquecer_publicacoes_datajud`
**depois** de `enriquecer` (DataJuri). Exemplo de ponto de injeção:

```python
# pipeline_diario.py, logo depois de enriquecer() DataJuri:
from enriquecimento_datajud import enriquecer_publicacoes_datajud
items_enriquecidos = enriquecer(items_novos)  # DataJuri existente
stats_dj = enriquecer_publicacoes_datajud(items_enriquecidos)  # adiciona DataJud
# Continua fluxo normal pra motor_opus.classificar_publicacao
```

Custo zero (API pública), latência +10-30s para 100 pubs.

### S2.1 — `dashboard.html.j2` (Jinja2 template)
Ler `C:\Users\joaof\Documents\advisian-djen\dashboard.html.j2` (91KB) e adaptar
pra cobrir os campos do intimacoes:
- **Manter do advisian-djen**: dark/light theme, filtros client-side, Excel export,
  busca live, responsividade
- **Adicionar do intimacoes**: coluna `regra` (IA), `confianca` (ALTA/MEDIA/BAIXA),
  `prazo_dias`, `INT-ID`, grupo duplicadas, link DataJuri, coluna DataJud nova
  (classe processual)
- **Branding ADVISIAN** mantido (logo, navy + red, fonte FG)

### S2.2 — `dashboard.py` renderer Jinja2
Atualmente `dash_simples.py` gera HTML via string concat. Reescrever usando
Jinja2 (`pip install jinja2`), separando lógica de apresentação.

### S2.3 — `servidor_local.py` + proxy DataJud inline
Portar `C:\Users\joaof\Documents\advisian-djen\servidor_local.py` (18KB):
- Serve `index.html` estático na porta 8765
- Expõe `/api/datajud` (POST) que proxia API DataJud (contorna CORS do browser)
- `/api/datajud/bulk` fanout paralelo (até 30 tribunais)
- Cache 7d, ThreadPoolExecutor

### S3.1 — Deploy Cloudflare Worker (`proxy_datajud/`)
Diretório `C:\Users\joaof\Documents\advisian-djen\proxy_datajud/` tem:
- `worker.js` (Cloudflare Worker script)
- `wrangler.toml` (config)
- `README.md`

Deploy via `wrangler deploy` → URL tipo `https://advisian-djen-proxy.USUARIO.workers.dev`.
Grava URL em `intimacoes_config.json` como `datajud_proxy_url` para uso do dashboard público.

### S3.2 — `deploy_git.py` (substituir deploy_netlify.py)
Atualmente o deploy é manual (`git add` + `git commit` + `git push`).
Portar `deploy_git.py` do advisian-djen que automatiza isso + deletar
`deploy_netlify.py` (já não usamos Netlify).

### S4 — Validação em produção + docs + commit final
- Rodar `pipeline_diario.py` end-to-end e verificar DataJuri + DataJud juntos
- Dashboard Jinja2 renderiza corretamente com novos campos
- Servidor local funciona (`python servidor_local.py` + abrir localhost:8765)
- Atualizar README.md do intimacoes
- Commit final com changelog

---

## 📁 Arquivos-chave (referência rápida)

### Em `C:\Users\joaof\Documents\advisian-djen\` (fonte para port)
| Arquivo | Tamanho | Destino no intimacoes |
|---------|---------|-----------------------|
| `telemetria.py` | 4KB | ✅ portado (estendido) |
| `schemas.py` | 5KB | ✅ não precisou |
| `captura_djen.py` | 6KB | ✅ portado (multi-filtro) |
| `enriquecimento_datajud.py` | 12KB | ✅ portado (hierarquia natureza) |
| `dashboard.html.j2` | 91KB | ⏳ S2.1 |
| `dashboard.py` | 7KB | ⏳ S2.2 |
| `servidor_local.py` | 19KB | ⏳ S2.3 |
| `proxy_datajud/` | — | ⏳ S3.1 |
| `deploy_git.py` | 5KB | ⏳ S3.2 |
| `pipeline.py` | 11KB | Referência p/ refactor pipeline_diario |
| `setup.py` | 4KB | Opcional (template público) |
| `atualizar.bat` | 0.6KB | Opcional |

### Em `C:\Users\joaof\Documents\intimacoes\` (produção FG)
- `pipeline_diario.py` — pipeline atual (DJEN + DataJuri + Opus)
- `motor_opus.py` — IA Opus 4.6 com 170 regras + retry escalonado (NÃO MEXER)
- `dash_simples.py` — dashboard atual (string concat — será substituído)
- `intimacoes_config.json` — credenciais (datajuri, anthropic, netlify, djen)
- `intimacoes_state.json` — estado (467 pubs dias 13-17/04/2026)
- `base_conhecimento.json` — 170 regras FG (NÃO MEXER)
- `ground_truth_v5.json` — 505 pares (NÃO MEXER)
- `auditoria_ids.py` — INT-IDs + hash chain (mesmo que advisian-djen)

---

## 🚨 Incompatibilidades + decisões a manter

1. **DataJuri vs DataJud são complementares, não substitutos**
   - DataJuri traz partes/valor/dados recentes
   - DataJud traz classe/assuntos/movimentos públicos
   - Rodam em paralelo no pipeline

2. **Motor IA do intimacoes (Opus 4.6 + 170 regras + GT V5) NÃO é tocado**
   - É a maior vantagem competitiva do FG
   - Dashboard Jinja2 precisa mostrar os campos dele

3. **Schema do state.json** — intimacoes tem campos que advisian-djen não tem:
   - `classificacao` (regra, confianca, prazo_dias, justificativa)
   - `contexto` (natureza, cliente, adverso, valor_causa) vindo do DataJuri
   - Novo: `datajud`, `natureza_datajud`, `natureza_fonte` (a partir deste commit)

4. **Deploy**: já migrado Netlify → GitHub Pages. `deploy_netlify.py` pode ser deletado.

5. **Task Scheduler** não rodou no dia 17/04 06:00. Pipeline foi rodado manual.
   Reconfigurar com LogonType S4U (requer admin).

---

## 🚀 Prompt inicial sugerido para a próxima sessão

```
Continuar port advisian-djen → intimacoes. Leia
C:\Users\joaof\Documents\intimacoes\HANDOFF_PORT_ADVISIAN_DJEN.md para
contexto.

Estado atual: Sprint 1 completa (commit 567240e pushed).
Próximo: S1.5 integrar DataJud no pipeline_diario.py.

Comece lendo o pipeline_diario.py atual e o enriquecimento_datajud.py
recém-criado, depois proponha o ponto de integração mínimo antes de editar.
```

---

## 📊 Telemetria do sistema (snapshot)

- **state atual**: 467 publicações (dias 13-17/04/2026)
- **dashboard online**: https://joaoguerini-fg.github.io/advisian/
- **motor**: Opus 4.6 (claude-opus-4-6)
- **custo acumulado Opus**: ~$15 em abril 2026
- **taxa alta confiança**: ~64%
- **auditoria**: 467/467 cadeias íntegras (SHA256 hash chain)
