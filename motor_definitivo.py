"""
MOTOR DEFINITIVO DE CLASSIFICACAO - Furtado Guerini
Consolida TODAS as licoes aprendidas:

1. FILTROS HARD:
   - Natureza DataJuri restringe regras disponíveis (Previdenciário != Cível)
   - Processo encerrado: não analisar fase
   - Distribuição Trabalhista = CADASTRAR PROCESSO (nunca RECLAMAÇÃO)
   - Distribuição em geral = CADASTRAR PROCESSO da natureza correspondente

2. DISTINCOES CRITICAS:
   - BENEFÍCIO INDEFERIDO = ato ADMINISTRATIVO do INSS (antes da ação)
   - SENTENÇA IMPROCEDENTE - PREVIDENCIÁRIO - [sufixo tribunal] = decisão JUDICIAL
   - RECLAMAÇÃO TRABALHISTA = cadastro manual comercial = INFORMATIVO_SEM_PRAZO

3. SUFIXOS POR TRIBUNAL (Previdenciário):
   - TRF1 → SENTENÇA IMPROCEDENTE - PREVIDENCIÁRIO - TRF1
   - TRF2+ES → JFES
   - TRF2+RJ → JFRJ
   - TRF3 → TRF3
   - TRF4 → TRF4
   - TRF5 → TRF5
   - TRF6 → TRF6
   - TJ* → TJs

4. MOTOR HIBRIDO:
   - IA pura decide primeiro (raciocinio juridico)
   - Ground truth V4 valida (teor juridico puro, 60 dias, sim >= 15%)
   - Concordancia: confianca muito alta
   - Conflito: flag revisao humana

5. VALIDACAO POS-CLASSIFICACAO:
   - Regra escolhida DEVE bater com natureza do processo
   - Se mismatch, reclassificar com filtro hard

6. LIMPEZA DE TEXTO:
   - Remover CSS/HTML
   - Remover elementos comuns ao processo (num, cliente, adverso, tribunal, vara)
   - Manter apenas teor juridico especifico
"""
import json, sys, re, time
from pathlib import Path
from collections import Counter, defaultdict
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# CONFIGURACAO
# ============================================================
# API key via variavel de ambiente (GitHub Secret em producao)
# Para rodar local, setar: $env:OPENAI_API_KEY="sua-key"
import os
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_KEY:
    # Tentar ler de arquivo local (nao commitado)
    try:
        with open("intimacoes_config.json", "r", encoding="utf-8") as f:
            cfg_local = json.load(f)
            OPENAI_KEY = cfg_local.get("anthropic", {}).get("openai_key") or cfg_local.get("openai_key", "")
    except:
        pass

MODEL_PRIMARY = "gpt-4.1"
if OPENAI_KEY:
    client = OpenAI(api_key=OPENAI_KEY)
else:
    client = None

# ============================================================
# LIMPEZA DE TEXTO (remove elementos comuns ao processo)
# ============================================================
def strip_html(texto):
    if not texto: return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto)).strip()

def extrair_teor_juridico(texto, processo="", cliente="", adverso=""):
    """Remove elementos comuns que identificam o processo, mantem SO o teor"""
    if not texto: return ""
    t = texto
    # CSS / HTML
    t = re.sub(r"[#.]?[a-zA-Z][\w-]*\s*\{[^}]*\}", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z]+;|&#\d+;", " ", t)
    # URLs
    t = re.sub(r"https?://[^\s]+", " ", t)
    # Numeros CNJ
    t = re.sub(r"\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}", " ", t)
    # CPF/CNPJ
    t = re.sub(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", " ", t)
    t = re.sub(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", " ", t)
    # Nomes (cliente, adverso) e palavras do nome
    for nome in [cliente, adverso]:
        if nome and len(nome) > 3:
            t = re.sub(re.escape(nome), " ", t, flags=re.I)
            for w in nome.split():
                if len(w) >= 4:
                    t = re.sub(r"\b" + re.escape(w) + r"\b", " ", t, flags=re.I)
    # Cabecalhos comuns
    for p in [
        r"PODER JUDICI[AÁ]RIO", r"JUSTI[CÇ]A DO TRABALHO",
        r"TRIBUNAL (REGIONAL|SUPERIOR) (DO TRABALHO|FEDERAL)",
        r"TRIBUNAL DE JUSTI[CÇ]A",
        r"VARA (DO TRABALHO|CIVEL|FEDERAL|C[IÍ]VEL)",
        r"\d+[ªºa°]?\s*(VARA|TURMA|C[AÂ]MARA|SEC[CÇ][AÃ]O)",
        r"JUIZADO ESPECIAL (FEDERAL|C[IÍ]VEL)",
        r"Avenida [A-Z][^,]*,\s*\d+", r"Rua [A-Z][^,]*,\s*\d+",
        r"CEP[:\s]*\d{5}-?\d{3}",
    ]:
        t = re.sub(p, " ", t, flags=re.I)
    # OAB, datas
    t = re.sub(r"OAB[:/\s]*[A-Z]{2}\s*\d+", " ", t, flags=re.I)
    t = re.sub(r"\d{2}/\d{2}/\d{4}", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# ============================================================
# INFERENCIAS DETERMINISTICAS
# ============================================================
def inferir_regiao_jfes_jfrj(texto, tribunal):
    """TRF2 atende RJ e ES. Infere pela UF mencionada."""
    if tribunal != "TRF2": return None
    if re.search(r"/ES\b|VIT[OÓ]RIA|ESP[IÍ]RITO SANTO", texto, re.I): return "JFES"
    if re.search(r"/RJ\b|RIO DE JANEIRO", texto, re.I): return "JFRJ"
    return "JFRJ"  # default

def determinar_sufixo_previdenciario(tribunal, texto):
    """Retorna sufixo do tribunal para regras previdenciarias"""
    if tribunal == "TRF1": return "TRF1"
    if tribunal == "TRF2":
        r = inferir_regiao_jfes_jfrj(texto, "TRF2")
        return r if r else "JFRJ"
    if tribunal == "TRF3": return "TRF3"
    if tribunal == "TRF4": return "TRF4"
    if tribunal == "TRF5": return "TRF5"
    if tribunal == "TRF6": return "TRF6"
    if tribunal.startswith("TJ"): return "TJs"
    return None

# ============================================================
# VALIDACOES POS-CLASSIFICACAO
# ============================================================
def area_da_regra(regra):
    if not regra: return ""
    up = regra.upper()
    if "TRABALHISTA" in up: return "Trabalhista"
    if "PREVIDENCI" in up: return "Previdenciário"
    if "CÍVEL" in up or "CIVEL" in up: return "Cível"
    return ""

def validar_classificacao(regra, natureza_processo, tribunal="", texto=""):
    """Valida se a regra classificada e valida para o processo"""
    if not regra or regra in {"INFORMATIVO_SEM_PRAZO","CLASSIFICACAO_MANUAL_OBRIGATORIA","NENHUMA_REGRA","DESPACHAR"}:
        return True, ""

    # 1. Area precisa bater com natureza
    area = area_da_regra(regra)
    if natureza_processo and area and natureza_processo.lower() != area.lower():
        return False, f"Area da regra ({area}) diverge da natureza do processo ({natureza_processo})"

    # 2. BENEFICIO INDEFERIDO so pra ato administrativo INSS, nao sentenca
    if regra == "BENEFÍCIO INDEFERIDO - PREVIDENCIÁRIO":
        if re.search(r"senten[cç]a|julg[oa]|dispositivo|ante o exposto", texto, re.I):
            return False, "Sentença judicial não deve usar BENEFÍCIO INDEFERIDO (é ato administrativo INSS)"

    # 3. Sentenca improcedente previdenciario precisa do sufixo correto do tribunal
    if natureza_processo == "Previdenciário" and "SENTENÇA IMPROCEDENTE" in regra:
        sufixo_esperado = determinar_sufixo_previdenciario(tribunal, texto)
        if sufixo_esperado and sufixo_esperado not in regra:
            return False, f"SENTENÇA IMPROCEDENTE - PREVIDENCIÁRIO precisa sufixo {sufixo_esperado} para tribunal {tribunal}"

    return True, ""

# ============================================================
# SELECAO DE REGRAS CANDIDATAS (FILTRO HARD POR NATUREZA)
# ============================================================
def selecionar_regras_candidatas(base, natureza, keywords, limite=20):
    """Filtra regras SOMENTE da natureza do processo"""
    if not natureza:
        # Sem natureza, retorna top regras trigadas
        todas = [(n, i) for n, i in base["regras"].items() if i.get("trigada_por_publicacao")]
        return sorted(todas, key=lambda x: -x[1].get("frequencia_historica", 0))[:limite]

    candidatas = []
    for nome, info in base["regras"].items():
        if not info.get("trigada_por_publicacao"): continue
        area = info.get("area", "")
        if not area: continue
        # FILTRO HARD: area da regra = natureza do processo
        if natureza.lower() not in area.lower() and area.lower() not in natureza.lower():
            continue

        score = info.get("frequencia_historica", 0) / 100
        # Boost por keywords
        regra_kw = set(info.get("keywords", []))
        score += len(set(keywords) & regra_kw) * 0.5
        # Boost por exemplos GOLD
        gold = sum(1 for e in info.get("exemplos", []) if e.get("qualidade") in ("GOLD","GOLD_MIXED"))
        score += gold * 0.2
        candidatas.append((nome, info, score))

    candidatas.sort(key=lambda x: -x[2])
    return [(n, i) for n, i, _ in candidatas[:limite]]

# ============================================================
# PROMPT DEFINITIVO (com todas as lições)
# ============================================================
def build_system_prompt():
    return """Voce e classificador juridico de nivel militar do escritorio Furtado Guerini.
Um prazo perdido pode quebrar o escritorio. Sua analise deve ser impecavel.

REGRAS CRITICAS (nao negociaveis):

1. NATUREZA DO PROCESSO RESTRINGE DURAMENTE AS REGRAS:
   - Processo PREVIDENCIARIO: escolher APENAS regras de natureza Previdenciário
   - Processo TRABALHISTA: escolher APENAS regras Trabalhistas
   - Processo CIVEL: escolher APENAS regras Cíveis
   - NUNCA classifique processo Previdenciario com regra Civel e vice-versa

2. DISTRIBUICAO DE PROCESSO:
   - "Distribuicao/Distribuidos" no tipoDocumento = processo foi recem-distribuido
   - O escritorio SEMPRE e polo ativo
   - Classificar como "CADASTRAR PROCESSO - TRABALHISTA" (ou CIVEL/PREVIDENCIARIO)
   - NUNCA use "RECLAMACAO TRABALHISTA" - esse e cadastro manual do dept comercial

3. BENEFICIO INDEFERIDO vs SENTENCA IMPROCEDENTE:
   - BENEFICIO INDEFERIDO = ato ADMINISTRATIVO do INSS (antes do processo judicial)
   - SENTENCA IMPROCEDENTE - PREVIDENCIARIO = decisao JUDICIAL em processo
   - Se o texto tem "sentenca", "julgo", "dispositivo", "ante o exposto" = SENTENCA
   - Sentenca previdenciaria improcedente TEM sufixo do tribunal:
     * TRF1 = SENTENCA IMPROCEDENTE - PREVIDENCIARIO - TRF1
     * TRF2/ES = SENTENCA IMPROCEDENTE - PREVIDENCIARIO - JFES
     * TRF2/RJ = SENTENCA IMPROCEDENTE - PREVIDENCIARIO - JFRJ
     * TRF3 = SENTENCA IMPROCEDENTE - PREVIDENCIARIO - TRF3
     * TRF4 = SENTENCA IMPROCEDENTE - PREVIDENCIARIO - TRF4
     * TJs = SENTENCA IMPROCEDENTE - PREVIDENCIARIO - TJs

4. PROCESSO ENCERRADO:
   - Se status = "Encerrado", fase nao e relevante
   - Publicacao pode ser residual/informativa
   - Nao forcar workflow em processo ja arquivado

5. RACIOCINIO (chain-of-thought):
   Passo 0: Processo ATIVO ou ENCERRADO? Se encerrado, considerar INFORMATIVO.
   Passo 1: Qual NATUREZA do processo? (restringe regras disponíveis)
   Passo 2: Qual EVENTO JURIDICO? (sentenca, acordao, despacho, emenda, etc.)
   Passo 3: tipoDocumento DJEN confirma? Se diverge, qual prevalece?
   Passo 4: Qual TRIBUNAL? (afeta sufixo de regras previdenciarias)
   Passo 5: Qual FASE PROCESSUAL? (historico de atividades)
   Passo 6: Qual a REGRA especifica dentre as disponiveis da natureza?
   Passo 7: Ha informacoes adicionais (datas, valores, riscos)?

6. CENARIOS SEM WORKFLOW:
   A) INFORMATIVO_SEM_PRAZO: publicacao meramente informativa
      - Distribuicao (exceto se requer cadastro: usa CADASTRAR PROCESSO)
      - Conclusos para despacho
      - Certidoes informativas
      - Processos encerrados com publicacao residual
   B) CLASSIFICACAO_MANUAL_OBRIGATORIA: exige acao sem regra cadastrada
   C) NENHUMA_REGRA: incapaz de determinar

CONFIANCA:
- ALTA: todos os sinais concordam (natureza + tipo DJEN + keywords + exemplos)
- MEDIA: match provavel mas 1 sinal diverge
- BAIXA: multiplos sinais divergentes

OBSERVACOES (campo "observacoes"): extraia datas, valores monetarios, riscos processuais,
determinacoes adicionais, prazos secundarios, nomes de peritos.

RESPONDA EXCLUSIVAMENTE em JSON puro (sem markdown)."""

# ============================================================
# MOTOR PRINCIPAL
# ============================================================
def classificar_publicacao(pub, base, gt_index):
    """
    Classifica uma publicacao aplicando TODAS as validacoes.
    Retorna dict com regra, confianca, gt_status, etc.
    """
    ctx = pub.get("contexto", {})
    natureza = (ctx.get("natureza") or pub.get("natureza") or "").strip()
    status_proc = ctx.get("status", "")
    processo = pub.get("processo", "")
    cliente = ctx.get("cliente", "")
    adverso = ctx.get("adverso", "")
    tribunal = pub.get("tribunal", "")
    tipo_doc_djen = pub.get("tipo_documento", "")
    texto_raw = pub.get("texto_completo", "") or pub.get("texto_resumo", "")

    # 1. TEOR PURO (sem elementos comuns do processo)
    teor_puro = extrair_teor_juridico(texto_raw, processo, cliente, adverso)

    # 2. DETECCAO DETERMINISTICA DE DISTRIBUICAO
    if tipo_doc_djen in ("Distribuição", "Distribuidos"):
        if natureza == "Trabalhista":
            return {"regra": "CADASTRAR PROCESSO - TRABALHISTA", "confianca": "ALTA",
                    "justificativa": "Publicacao de distribuicao - escritorio e polo ativo, precisa cadastrar processo",
                    "prazo_dias": None, "observacoes": "", "_via": "deterministico_distribuicao"}
        elif natureza == "Cível":
            return {"regra": "CADASTRAR PROCESSO - CÍVEL", "confianca": "ALTA",
                    "justificativa": "Distribuicao - cadastrar processo civel",
                    "prazo_dias": None, "observacoes": "", "_via": "deterministico_distribuicao"}
        elif natureza == "Previdenciário":
            return {"regra": "CADASTRAR PROCESSO - PREVIDENCIARIO", "confianca": "ALTA",
                    "justificativa": "Distribuicao - cadastrar processo previdenciario",
                    "prazo_dias": None, "observacoes": "", "_via": "deterministico_distribuicao"}

    # 3. SELECAO DE REGRAS (FILTRO HARD por natureza)
    keywords = re.findall(r"\b[a-z]{5,}\b", teor_puro.lower())[:30]
    candidatas = selecionar_regras_candidatas(base, natureza, keywords, limite=20)

    if not candidatas:
        return {"regra": "CLASSIFICACAO_MANUAL_OBRIGATORIA", "confianca": "BAIXA",
                "justificativa": f"Sem regras candidatas para natureza {natureza}",
                "prazo_dias": None, "observacoes": "", "_via": "sem_candidatas"}

    # 4. MONTAR PROMPT
    regras_txt = ""
    for nome, info in candidatas:
        regras_txt += f"\n### {nome}\n"
        regras_txt += f"Area: {info.get('area','')} | Freq: {info.get('frequencia_historica',0)}\n"
        for ex in info.get("exemplos", [])[:2]:
            if ex.get("qualidade") in ("GOLD","GOLD_MIXED"):
                regras_txt += f"Ex: \"{ex.get('texto','')[:250]}\"\n"

    # Sugerir sufixo se Previdenciario + TRF
    dica_sufixo = ""
    if natureza == "Previdenciário" and tribunal.startswith(("TRF","TJ")):
        sufixo = determinar_sufixo_previdenciario(tribunal, texto_raw)
        if sufixo:
            dica_sufixo = f"\nATENCAO: Tribunal {tribunal} - regras previdenciarias desse tribunal usam sufixo {sufixo}"

    user_prompt = f"""PROCESSO: {processo}
NATUREZA: {natureza}  (FILTRO HARD - so use regras dessa natureza)
STATUS: {status_proc}
TIPO DE ACAO: {ctx.get('tipo_acao','N/A')}
TRIBUNAL: {tribunal}{dica_sufixo}
FASE: {ctx.get('fase_atual','N/A')}
CLIENTE: {cliente}

HISTORICO:
{(ctx.get('historico','') or '')[:1500]}

PRAZOS EM ABERTO:
{(ctx.get('prazos_abertos','') or 'Nenhum')[:300]}

TIPO DJEN: {tipo_doc_djen}
TEXTO (teor puro):
{teor_puro[:2500]}

REGRAS CANDIDATAS (somente da natureza {natureza}):
{regras_txt}

JSON puro:
{{"regra":"NOME EXATO","confianca":"ALTA|MEDIA|BAIXA","justificativa":"1-2 frases","prazo_dias":null,"tipo_contagem":"uteis|corridos","observacoes":""}}"""

    # 5. CHAMAR IA
    try:
        response = client.chat.completions.create(
            model=MODEL_PRIMARY, max_tokens=1500, temperature=0.1,
            messages=[{"role":"system","content":build_system_prompt()},{"role":"user","content":user_prompt}]
        )
        text = response.choices[0].message.content.strip()
        cleaned = re.sub(r"```(?:json)?", "", text).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            return {"regra": "ERRO_CLASSIFICACAO", "confianca": "BAIXA",
                    "justificativa": "Sem JSON valido", "prazo_dias": None, "observacoes": "",
                    "_via": "erro_parse"}
        resultado = json.loads(m.group())
    except Exception as e:
        return {"regra": "ERRO_CLASSIFICACAO", "confianca": "BAIXA",
                "justificativa": f"Erro API: {str(e)[:100]}", "prazo_dias": None, "observacoes": "",
                "_via": "erro_api"}

    # 6. VALIDAR POS-CLASSIFICACAO
    regra = resultado.get("regra", "")
    ok, motivo = validar_classificacao(regra, natureza, tribunal, texto_raw)

    if not ok:
        # Retry com mensagem de correcao
        print(f"    [VALIDACAO FALHOU] {motivo} - retry...", flush=True)
        retry_prompt = user_prompt + f"\n\nATENCAO: sua classificacao {regra} FALHOU na validacao: {motivo}. Reclassifique corretamente."
        try:
            response = client.chat.completions.create(
                model=MODEL_PRIMARY, max_tokens=1500, temperature=0.05,
                messages=[{"role":"system","content":build_system_prompt()},{"role":"user","content":retry_prompt}]
            )
            text = response.choices[0].message.content.strip()
            cleaned = re.sub(r"```(?:json)?", "", text).strip()
            m = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if m:
                retry_result = json.loads(m.group())
                ok2, motivo2 = validar_classificacao(retry_result.get("regra",""), natureza, tribunal, texto_raw)
                if ok2:
                    resultado = retry_result
                    resultado["_validation_retry"] = True
                else:
                    resultado["_validation_error"] = motivo2
        except:
            pass

    # 7. MOTOR HIBRIDO - Ground Truth como segunda opiniao
    if gt_index:
        pub_tokens = set(w for w in re.findall(r"\b[a-záéíóúâêôçãõü]{4,}\b", teor_puro.lower()))
        melhores = []
        for gt in gt_index:
            inter = pub_tokens & gt["tokens"]
            uniao = pub_tokens | gt["tokens"]
            sim = len(inter)/len(uniao) if uniao else 0
            if sim >= 0.15:
                melhores.append({"regra": gt["regra"], "sim": sim})

        if melhores:
            melhores.sort(key=lambda x: -x["sim"])
            top_gt = melhores[:3]
            votos = defaultdict(float)
            for t in top_gt: votos[t["regra"]] += t["sim"]
            regra_gt = max(votos.items(), key=lambda x: x[1])[0]
            sim_max = top_gt[0]["sim"]

            if regra_gt == resultado["regra"]:
                resultado["_gt_status"] = "CONCORDA"
                if resultado.get("confianca") == "MEDIA":
                    resultado["confianca"] = "ALTA"
                    resultado["_gt_boost"] = True
            else:
                resultado["_gt_status"] = "CONFLITO"
                resultado["_gt_sugerida"] = regra_gt
                resultado["_gt_similaridade"] = round(sim_max, 3)

    return resultado

# ============================================================
# MAIN - se rodar diretamente, reclassifica tudo do state
# ============================================================
if __name__ == "__main__":
    with open("intimacoes_state.json","r",encoding="utf-8") as f:
        state = json.load(f)
    with open("base_conhecimento.json","r",encoding="utf-8") as f:
        base = json.load(f)

    # Indexar ground truth V4
    gt_index = []
    try:
        with open("ground_truth_v4.json","r",encoding="utf-8") as f:
            gt = json.load(f)
        for m in gt["matches_perfeitos"]:
            teor = m.get("pub_teor_puro","") or extrair_teor_juridico(m.get("pub_texto_original",""))
            tokens = set(w for w in re.findall(r"\b[a-záéíóúâêôçãõü]{4,}\b", teor.lower()))
            gt_index.append({"regra": m["tarefa_regra"], "tokens": tokens})
        print(f"GT V4 indexado: {len(gt_index)} precedentes")
    except Exception as e:
        print(f"GT nao disponivel: {e}")

    # Modo default: validar todas as classificacoes existentes
    # Se quiser reclassificar, mudar flag
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="Reclassificar so publicacoes dessa data (YYYY-MM-DD)")
    parser.add_argument("--validar", action="store_true", help="Apenas validar (sem reclassificar)")
    parser.add_argument("--somente-mismatch", action="store_true", help="Reclassificar so publicacoes com validacao falhando")
    args = parser.parse_args()

    pubs_target = state["publicacoes"]
    if args.data:
        pubs_target = [p for p in pubs_target if p.get("data_disponibilizacao") == args.data]

    if args.somente_mismatch:
        filtrado = []
        for p in pubs_target:
            regra = p.get("classificacao",{}).get("regra","")
            natureza = (p.get("contexto",{}).get("natureza") or "").strip()
            ok, _ = validar_classificacao(regra, natureza, p.get("tribunal",""), p.get("texto_completo",""))
            if not ok:
                filtrado.append(p)
        pubs_target = filtrado
        print(f"Publicacoes com mismatch a reclassificar: {len(pubs_target)}")

    if args.validar:
        # So validar
        mismatches = []
        for p in pubs_target:
            regra = p.get("classificacao",{}).get("regra","")
            natureza = (p.get("contexto",{}).get("natureza") or "").strip()
            ok, motivo = validar_classificacao(regra, natureza, p.get("tribunal",""), p.get("texto_completo",""))
            if not ok:
                mismatches.append({"processo": p["processo"], "regra": regra, "motivo": motivo})
        print(f"\n{len(mismatches)} classificacoes com problema:")
        for m in mismatches:
            print(f"  {m['processo']} | {m['regra']} | {m['motivo']}")
    else:
        print(f"\nReclassificando {len(pubs_target)} publicacoes...")
        for i, pub in enumerate(pubs_target):
            print(f"[{i+1}/{len(pubs_target)}] {pub.get('processo','')}", flush=True)
            resultado = classificar_publicacao(pub, base, gt_index)
            # Preservar V1 se nao foi
            cls_antiga = pub.get("classificacao", {})
            if "regra_v1" not in cls_antiga:
                cls_antiga["regra_v1"] = cls_antiga.get("regra","")
                cls_antiga["confianca_v1"] = cls_antiga.get("confianca","")
            # Merge preservando historico
            for k, v in resultado.items():
                cls_antiga[k] = v
            pub["classificacao"] = cls_antiga
            print(f"    -> {resultado.get('regra','?')} ({resultado.get('confianca','?')})", flush=True)
            time.sleep(0.3)

        with open("intimacoes_state.json","w",encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print("\nState atualizado")
