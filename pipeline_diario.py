"""
Pipeline diario - executado pelo GitHub Action todo dia de manha.
1. Captura publicacoes DJEN do dia anterior + hoje
2. Enriquece via DataJuri
3. Classifica com GPT-4.1 (motor definitivo)
4. Atualiza intimacoes_state.json (append, nao sobrescreve)
"""
import os, json, sys, re, time, base64
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

# Configuracoes via environment (GitHub Secrets)
DJ_CLIENT_ID = os.environ.get("DATAJURI_CLIENT_ID", "")
DJ_SECRET = os.environ.get("DATAJURI_SECRET", "")
DJ_USER = os.environ.get("DATAJURI_USER", "")
DJ_PASS = os.environ.get("DATAJURI_PASS", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not all([DJ_CLIENT_ID, DJ_SECRET, DJ_USER, DJ_PASS, OPENAI_API_KEY]):
    print("ERRO: Variaveis de ambiente nao configuradas")
    sys.exit(1)

import requests
from openai import OpenAI

client_openai = OpenAI(api_key=OPENAI_API_KEY)

DJ_BASE = "https://api.datajuri.com.br"
DJEN_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"

# ============================================================
# HELPERS
# ============================================================
def strip_html(t):
    if not t: return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()

def datajuri_token():
    creds = base64.b64encode(f"{DJ_CLIENT_ID}:{DJ_SECRET}".encode()).decode()
    r = requests.post(f"{DJ_BASE}/oauth/token",
        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
        data=f"grant_type=password&username={DJ_USER}&password={DJ_PASS}", timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

# ============================================================
# ETAPA 1: Capturar DJEN
# ============================================================
def capturar_djen(data_alvo):
    print(f"Capturando DJEN para {data_alvo}...")
    filtros = [
        {"numeroOab": "30079", "ufOab": "ES"},
        {"nomeAdvogado": "JOAO FURTADO GUERINI"},
        {"nomeAdvogado": "FURTADO GUERINI SOCIEDADE INDIVIDUAL DE ADVOCACIA"},
    ]
    seen = set()
    all_items = []
    for filtro in filtros:
        params = {**filtro, "meio": "D",
                  "dataDisponibilizacaoInicio": data_alvo,
                  "dataDisponibilizacaoFim": data_alvo}
        pagina = 1
        while True:
            params["pagina"] = pagina
            r = requests.get(DJEN_URL, params=params, timeout=30)
            r.raise_for_status()
            items = r.json().get("items", [])
            for i in items:
                if i["id"] not in seen:
                    seen.add(i["id"])
                    all_items.append(i)
            if len(items) < 100: break
            pagina += 1
            time.sleep(0.5)
    print(f"  {len(all_items)} publicacoes capturadas")
    return all_items

# ============================================================
# DEDUP
# ============================================================
def deduplicar(items):
    grupos = defaultdict(list)
    for i in items:
        proc = i.get("numeroprocessocommascara", i.get("numero_processo", ""))
        grupos[proc].append(i)
    resultado = []
    for proc, group in grupos.items():
        if len(group) == 1:
            group[0]["_dedup"] = "UNICA"
            resultado.append(group[0])
        else:
            textos = {}
            for it in group:
                if it["texto"] in textos:
                    continue
                textos[it["texto"]] = it
            mantidas = list(textos.values())
            if len(mantidas) > 1:
                for m in mantidas: m["_dedup"] = "ATENCAO_MULTIPLA"
            else:
                mantidas[0]["_dedup"] = "MANTIDA"
            resultado.extend(mantidas)
    return resultado

# ============================================================
# ETAPA 2: Enriquecer via DataJuri
# ============================================================
def enriquecer(items):
    print("Enriquecendo via DataJuri...")
    token = datajuri_token()
    headers = {"Authorization": f"Bearer {token}"}
    campos = "id,pasta,natureza,assunto,tipoAcao,status,faseAtual.tipoFase,faseAtual.instancia,historicoAtividadesStr,listaPrazoAbertoStr,cliente.nome,adverso.nome,valorCausa,tipoProcesso"

    processos_alvo = set(i.get("numeroprocessocommascara", "") for i in items if i.get("numeroprocessocommascara"))
    cache = {}
    page = 0
    while len(cache) < len(processos_alvo) and page < 200:
        try:
            r = requests.get(f"{DJ_BASE}/v1/entidades/Processo", headers=headers,
                params={"page": page, "pageSize": 50, "campos": campos}, timeout=30)
            data = r.json()
            records = data.get("rows", data.get("content", []))
            if not records: break
            for rec in records:
                pasta = rec.get("pasta", "")
                if pasta in processos_alvo:
                    cache[pasta] = rec
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  Erro pg {page}: {e}")
            token = datajuri_token()
            headers = {"Authorization": f"Bearer {token}"}

    for item in items:
        proc = item.get("numeroprocessocommascara", "")
        ctx = cache.get(proc, {})
        item["_contexto"] = {
            "id": ctx.get("id", ""),
            "natureza": ctx.get("natureza", ""),
            "status": ctx.get("status", ""),
            "tipo_acao": ctx.get("tipoAcao", ""),
            "fase_atual": ctx.get("faseAtual.tipoFase", ""),
            "cliente": ctx.get("cliente.nome", ""),
            "adverso": ctx.get("adverso.nome", ""),
            "historico": strip_html(ctx.get("historicoAtividadesStr", ""))[:2000],
            "valor_causa": ctx.get("valorCausa", "") or "",
            "tipo_processo": ctx.get("tipoProcesso", "") or "",
        }

    print(f"  {len(cache)}/{len(processos_alvo)} processos encontrados")
    return items

# ============================================================
# ETAPA 3: Classificar via motor definitivo
# ============================================================
def classificar(items):
    print("Classificando com motor definitivo...")
    from motor_definitivo import classificar_publicacao

    with open("base_conhecimento.json", "r", encoding="utf-8") as f:
        base = json.load(f)

    gt_index = []
    try:
        with open("ground_truth_v4.json", "r", encoding="utf-8") as f:
            gt = json.load(f)
        from motor_definitivo import extrair_teor_juridico
        for m in gt["matches_perfeitos"]:
            teor = m.get("pub_teor_puro", "") or extrair_teor_juridico(m.get("pub_texto_original", ""))
            tokens = set(w for w in re.findall(r"\b[a-záéíóúâêôçãõü]{4,}\b", teor.lower()))
            gt_index.append({"regra": m["tarefa_regra"], "tokens": tokens})
    except:
        pass

    for i, item in enumerate(items):
        # Adaptar item para formato esperado pelo motor
        pub = {
            "processo": item.get("numeroprocessocommascara", ""),
            "tribunal": item.get("siglaTribunal", ""),
            "tipo_documento": item.get("tipoDocumento", ""),
            "texto_completo": item.get("texto", ""),
            "texto_resumo": item.get("texto", "")[:300],
            "contexto": item.get("_contexto", {}),
            "natureza": item.get("_contexto", {}).get("natureza", ""),
        }
        resultado = classificar_publicacao(pub, base, gt_index)
        item["_classificacao"] = resultado
        print(f"  [{i+1}/{len(items)}] {pub['processo']} -> {resultado.get('regra','?')} ({resultado.get('confianca','?')})")
        time.sleep(0.3)

    return items

# ============================================================
# MAIN
# ============================================================
def main():
    # Carregar state existente (se houver)
    if os.path.exists("intimacoes_state.json"):
        with open("intimacoes_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"publicacoes": [], "processed_ids": [], "metadata": {}}

    ids_existentes = set(p["id"] for p in state["publicacoes"] if p.get("id"))

    # Capturar ultimo dia util
    hoje = datetime.now()
    ontem = hoje - timedelta(days=1)
    # Se sabado/domingo, pega sexta
    while ontem.weekday() >= 5:
        ontem -= timedelta(days=1)
    data_alvo = ontem.strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"PIPELINE DIARIO - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Data alvo: {data_alvo}")
    print(f"{'='*60}\n")

    # Etapa 1
    items = capturar_djen(data_alvo)

    # Filtrar ja processadas
    items_novos = [i for i in items if i["id"] not in ids_existentes]
    print(f"Novas publicacoes: {len(items_novos)}")

    if not items_novos:
        print("Sem publicacoes novas hoje")
        return

    # Etapa 1.5: Dedup
    items_novos = deduplicar(items_novos)

    # Etapa 2
    items_novos = enriquecer(items_novos)

    # Etapa 3
    items_novos = classificar(items_novos)

    # Append ao state
    for item in items_novos:
        pub_state = {
            "id": item["id"],
            "data_disponibilizacao": item.get("data_disponibilizacao", ""),
            "processo": item.get("numeroprocessocommascara", ""),
            "tribunal": item.get("siglaTribunal", ""),
            "tipo_documento": item.get("tipoDocumento", ""),
            "texto_resumo": strip_html(item.get("texto", ""))[:300],
            "texto_completo": strip_html(item.get("texto", "")),
            "link": item.get("link", ""),
            "natureza": item.get("_contexto", {}).get("natureza", ""),
            "contexto": item.get("_contexto", {}),
            "datajuri_id": item.get("_contexto", {}).get("id", ""),
            "cliente": item.get("_contexto", {}).get("cliente", ""),
            "adverso": item.get("_contexto", {}).get("adverso", ""),
            "dedup_status": item.get("_dedup", ""),
            "classificacao": item.get("_classificacao", {}),
        }
        state["publicacoes"].append(pub_state)

    state["metadata"]["last_run"] = datetime.now().isoformat()
    state["metadata"]["total"] = len(state["publicacoes"])

    with open("intimacoes_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"CONCLUIDO: {len(items_novos)} novas publicacoes processadas")
    print(f"Total no state: {len(state['publicacoes'])}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
