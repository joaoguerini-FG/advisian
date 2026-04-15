"""Dashboard FINAL - Multi-select filters + cards clickaveis + tema claro/escuro"""
import json, sys
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8")

with open("intimacoes_state.json", "r", encoding="utf-8") as f:
    state = json.load(f)

pubs = state["publicacoes"]
data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

DATAJURI_URL = "https://dj33.datajuri.com.br/app/#/lista/Processo/"
DATAJURI_TAB = "?relDir=asc&relSize=20&relPagina=1&tab=HistoricoAtividades"

rows = []
for pub in pubs:
    cls = pub.get("classificacao", {})
    ctx = pub.get("contexto", {})
    sinal = pub.get("sinal", {})
    processo = pub.get("processo", "")
    dj_id = pub.get("datajuri_id", ctx.get("id", ""))
    dj_url = ""
    if dj_id:
        try:
            dj_url = DATAJURI_URL + str(int(float(dj_id))) + DATAJURI_TAB
        except:
            pass

    def esc(s):
        if not s or not isinstance(s, str):
            return str(s) if s else ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "").replace("\t", " ").replace("`", "'").replace("${", "$ {")

    # Motor hibrido: GT V3 info
    gt_v3 = cls.get("gt_v3", {})
    gt_status = gt_v3.get("status", "")
    gt_regra = gt_v3.get("regra_gt_sugerida", "") or ""
    gt_sim = gt_v3.get("similaridade_max", 0)

    rows.append({
        "processo": esc(processo),
        "dj_url": esc(dj_url),
        "djen_link": esc(pub.get("link", "")),
        "data": esc(pub.get("data_disponibilizacao", "")),
        "tribunal": esc(pub.get("tribunal", "")),
        "tipo_doc": esc(pub.get("tipo_documento", "")),
        "natureza": esc(ctx.get("natureza", "") or pub.get("natureza", "")),
        "cliente": esc(ctx.get("cliente", "")),
        "adverso": esc(ctx.get("adverso", "")),
        "assunto_dj": esc(ctx.get("assunto", "")),
        "tipo_acao": esc(ctx.get("tipo_acao", "")),
        "fase_atual": esc(ctx.get("fase_atual", "")),
        "valor_causa": esc(ctx.get("valor_causa", "")),
        "tipo_processo": esc(ctx.get("tipo_processo", "")),
        "regra": esc(cls.get("regra", "")),
        "confianca": esc(cls.get("confianca", "")),
        "prazo": esc(str(cls.get("prazo_dias", "") or "")),
        "justificativa": esc(cls.get("justificativa", "")),
        "observacoes": esc(cls.get("observacoes", "")),
        "raciocinio": esc(cls.get("raciocinio", "")),
        "flags": esc(", ".join(cls.get("flags", []) if isinstance(cls.get("flags"), list) else [])),
        "texto": esc(pub.get("texto_completo", pub.get("texto_resumo", ""))),
        "gt_status": esc(gt_status),
        "gt_regra": esc(gt_regra),
        "gt_sim": esc(str(round(gt_sim, 2))) if gt_sim else "",
    })

rows_json = json.dumps(rows, ensure_ascii=False)
pend = ["PENDENTE","PENDENTE_CLASSIFICACAO","","ERRO_CLASSIFICACAO"]
total = len(rows)
alta = sum(1 for r in rows if r["confianca"] == "ALTA")
media = sum(1 for r in rows if r["confianca"] == "MEDIA")
baixa = sum(1 for r in rows if r["confianca"] == "BAIXA" and r["regra"] not in pend)
manual = sum(1 for r in rows if "MANUAL" in r["regra"] or "NENHUMA" in r["regra"])
pendentes = sum(1 for r in rows if r["regra"] in pend)
info = sum(1 for r in rows if r["regra"] == "INFORMATIVO_SEM_PRAZO")
# Workflows = classificacoes com regra real (encaixou num workflow do DataJuri)
excl = set(pend) | {"INFORMATIVO_SEM_PRAZO"}
workflows = sum(1 for r in rows if r["regra"] and r["regra"] not in excl and "MANUAL" not in r["regra"] and "NENHUMA" not in r["regra"])

# Motor hibrido stats
gt_concorda = sum(1 for r in rows if r.get("gt_status") == "CONCORDA")
gt_conflito = sum(1 for r in rows if r.get("gt_status") == "CONFLITO")

html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Controller de Prazos - Furtado Guerini</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
--bg:#0a0e1a;--bg2:#0f1424;--bg3:#131830;--bd:#1e293b;--bd2:rgba(99,102,241,0.15);
--txt:#e2e8f0;--txt2:#94a3b8;--txt3:#64748b;
--accent:#818cf8;--accent2:#c084fc;
}
body.light{
--bg:#f8fafc;--bg2:#ffffff;--bg3:#f1f5f9;--bd:#e2e8f0;--bd2:rgba(99,102,241,0.15);
--txt:#1e293b;--txt2:#475569;--txt3:#94a3b8;
--accent:#6366f1;--accent2:#a855f7;
}
body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text",Inter,sans-serif;background:var(--bg);color:var(--txt);-webkit-font-smoothing:antialiased;transition:background .2s}
.header{background:var(--bg2);padding:20px 32px;border-bottom:1px solid var(--bd);display:flex;justify-content:space-between;align-items:center}
.header-l h1{font-size:20px;font-weight:600;color:var(--txt);letter-spacing:-0.3px}
.header-l .sub{color:var(--txt3);font-size:12px;margin-top:3px}
.theme-toggle{background:var(--bg3);border:1px solid var(--bd);color:var(--txt2);padding:8px 14px;border-radius:999px;cursor:pointer;font-size:12px;font-weight:500;display:flex;align-items:center;gap:6px;transition:all .15s;font-family:inherit}
.theme-toggle:hover{border-color:var(--accent);color:var(--accent)}
.stats{display:flex;gap:10px;padding:16px 32px;background:var(--bg2);border-bottom:1px solid var(--bd);flex-wrap:wrap}
.sc{background:var(--bg);border:1px solid var(--bd);border-radius:10px;padding:14px 18px;min-width:110px;cursor:pointer;transition:all .2s;user-select:none}
.sc:hover{border-color:var(--accent);transform:translateY(-1px)}
.sc.active{border-color:var(--accent);background:var(--bg3);box-shadow:0 0 0 2px rgba(99,102,241,0.15)}
.sc .n{font-size:26px;font-weight:700;letter-spacing:-0.5px}
.sc .l{font-size:10px;color:var(--txt3);text-transform:uppercase;letter-spacing:1px;margin-top:3px;font-weight:600}
.filters{display:flex;gap:10px;padding:14px 32px;background:var(--bg2);flex-wrap:wrap;align-items:end;border-bottom:1px solid var(--bd)}
.fg{display:flex;flex-direction:column;gap:4px;position:relative}
.fg label{font-size:10px;color:var(--txt3);text-transform:uppercase;letter-spacing:1px;font-weight:600}
.multi-btn{background:var(--bg);border:1px solid var(--bd);color:var(--txt);padding:7px 12px;border-radius:6px;font-size:12px;font-family:inherit;cursor:pointer;min-width:140px;text-align:left;display:flex;justify-content:space-between;align-items:center;gap:8px;transition:border-color .15s}
.multi-btn:hover{border-color:var(--accent)}
.multi-btn.has-val{border-color:var(--accent);color:var(--accent)}
.multi-btn::after{content:"▾";font-size:9px;color:var(--txt3)}
.multi-dropdown{display:none;position:absolute;top:100%;left:0;background:var(--bg2);border:1px solid var(--bd);border-radius:8px;margin-top:4px;min-width:200px;max-height:320px;overflow-y:auto;z-index:1000;box-shadow:0 8px 24px rgba(0,0,0,0.2)}
.multi-dropdown.open{display:block}
.multi-actions{display:flex;gap:4px;padding:8px;border-bottom:1px solid var(--bd);background:var(--bg3)}
.multi-actions button{flex:1;background:var(--bg);border:1px solid var(--bd);color:var(--txt2);padding:5px 8px;border-radius:4px;font-size:10px;cursor:pointer;font-family:inherit;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;transition:all .1s}
.multi-actions button:hover{color:var(--accent);border-color:var(--accent)}
.multi-opt{padding:7px 12px;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:8px;transition:background .1s}
.multi-opt:hover{background:var(--bg3)}
.multi-opt input{cursor:pointer;accent-color:var(--accent)}
.multi-opt .lb-opt{color:var(--txt);flex:1}
.multi-opt.selected .lb-opt{color:var(--accent);font-weight:600}
.fg input[type=text]{background:var(--bg);border:1px solid var(--bd);color:var(--txt);padding:7px 12px;border-radius:6px;font-size:12px;font-family:inherit}
.tc{padding:0 32px 32px;overflow-x:auto;margin-top:12px}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px}
th{background:var(--bg2);color:var(--txt3);padding:10px 14px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.8px;font-weight:700;position:sticky;top:0;cursor:pointer;border-bottom:2px solid var(--bd);white-space:nowrap}
th:hover{color:var(--accent)}
tr{border-bottom:1px solid var(--bd);transition:background .15s;cursor:pointer}
tr:hover{background:var(--bg3)}
td{padding:10px 14px;vertical-align:top;color:var(--txt)}
.b{display:inline-block;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.b-a{background:rgba(34,197,94,0.12);color:#4ade80;border:1px solid rgba(34,197,94,0.2)}
.b-m{background:rgba(251,191,36,0.12);color:#fbbf24;border:1px solid rgba(251,191,36,0.2)}
.b-b{background:rgba(248,113,113,0.12);color:#f87171;border:1px solid rgba(248,113,113,0.2)}
.b-man{background:rgba(249,115,22,0.12);color:#fb923c;border:1px solid rgba(249,115,22,0.2)}
.b-info{background:rgba(99,102,241,0.12);color:#818cf8;border:1px solid rgba(99,102,241,0.2)}
.b-p{background:rgba(100,116,139,0.12);color:#94a3b8;border:1px solid rgba(100,116,139,0.2)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.dj{color:#c084fc;font-weight:600}.dj:hover{color:#d8b4fe}
body.light .dj{color:#9333ea}
.obs{color:var(--txt2);font-size:11px;max-width:420px;line-height:1.6;padding:8px 14px !important}
.flag{color:#fb923c;font-size:10px;font-weight:600}
.rm{border-left:3px solid #f97316}.rb{border-left:3px solid #f87171}
.empty{text-align:center;padding:60px;color:var(--txt3);font-size:14px}
</style>
</head>
<body>
<div class="header">
<div class="header-l">
<h1>Controller de Prazos — Intimações DJEN</h1>
<div class="sub">Furtado Guerini Advogados · """ + data_geracao + """ · GPT-4.1 + Opus 4.6</div>
</div>
<button class="theme-toggle" onclick="toggleTheme()" id="themeBtn">🌙 Escuro</button>
</div>
<div class="stats" id="statsContainer">
<div class="sc" data-filter="all"><div class="n" style="color:#818cf8" id="st">""" + str(total) + """</div><div class="l">Total</div></div>
<div class="sc" data-filter="workflow"><div class="n" style="color:#4ade80" id="sw">""" + str(workflows) + """</div><div class="l">Workflows</div></div>
<div class="sc" data-filter="regra:MANUAL"><div class="n" style="color:#fb923c" id="sr">""" + str(manual) + """</div><div class="l">Manual</div></div>
<div class="sc" data-filter="regra:INFORMATIVO_SEM_PRAZO"><div class="n" style="color:#818cf8" id="si">""" + str(info) + """</div><div class="l">Informativo</div></div>
<div class="sc" data-filter="regra:PENDENTE"><div class="n" style="color:#64748b" id="sp">""" + str(pendentes) + """</div><div class="l">Pendentes</div></div>
<div class="sc" data-filter="gt:CONCORDA"><div class="n" style="color:#22c55e" id="sgc">""" + str(gt_concorda) + """</div><div class="l">GT Confirma</div></div>
<div class="sc" data-filter="gt:CONFLITO"><div class="n" style="color:#ef4444" id="sgk">""" + str(gt_conflito) + """</div><div class="l">GT Conflito</div></div>
</div>
<div class="filters">
<div class="fg"><label>Natureza</label><button class="multi-btn" data-filter="fn">Todas</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('fn')">Selecionar tudo</button><button onclick="clearAll('fn')">Limpar</button></div><div class="multi-opts" id="opts-fn"></div></div></div>
<div class="fg"><label>Confianca</label><button class="multi-btn" data-filter="fc">Todas</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('fc')">Selecionar tudo</button><button onclick="clearAll('fc')">Limpar</button></div><div class="multi-opts" id="opts-fc"></div></div></div>
<div class="fg"><label>Tribunal</label><button class="multi-btn" data-filter="ft">Todos</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('ft')">Selecionar tudo</button><button onclick="clearAll('ft')">Limpar</button></div><div class="multi-opts" id="opts-ft"></div></div></div>
<div class="fg"><label>Tipo Doc</label><button class="multi-btn" data-filter="ftd">Todos</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('ftd')">Selecionar tudo</button><button onclick="clearAll('ftd')">Limpar</button></div><div class="multi-opts" id="opts-ftd"></div></div></div>
<div class="fg"><label>Data</label><button class="multi-btn" data-filter="fd">Todas</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('fd')">Selecionar tudo</button><button onclick="clearAll('fd')">Limpar</button></div><div class="multi-opts" id="opts-fd"></div></div></div>
<div class="fg"><label>Regra</label><button class="multi-btn" data-filter="fr">Todas</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('fr')">Selecionar tudo</button><button onclick="clearAll('fr')">Limpar</button></div><div class="multi-opts" id="opts-fr"></div></div></div>
<div class="fg"><label>Buscar</label><input type="text" id="fb" oninput="f()" placeholder="processo..." style="width:180px"></div>
<div class="fg"><label style="opacity:0">Clear</label><button class="multi-btn" onclick="clearAllFilters()" style="background:rgba(239,68,68,0.08);color:#f87171;border-color:rgba(239,68,68,0.2);min-width:80px;text-align:center">Limpar tudo</button></div>
</div>
<div class="tc">
<table><thead><tr>
<th onclick="s(0)">Processo</th><th onclick="s(1)">Data</th><th onclick="s(2)">Natureza</th>
<th onclick="s(3)">Tribunal</th><th onclick="s(4)">Tipo Doc</th><th onclick="s(5)">Regra</th>
<th onclick="s(6)">Confianca</th><th onclick="s(7)">Prazo</th><th>GT V3</th><th>Teor da Intimacao</th><th>Flags</th>
</tr></thead><tbody id="tb"></tbody></table>
</div>

<script>
var D=""" + rows_json + """;
var sc=-1,sa=true;

// Estado de filtros
var filters={fn:[],fc:[],ft:[],ftd:[],fd:[],fr:[]};
var cardFilter=null;

// Theme
function toggleTheme(){
  document.body.classList.toggle('light');
  var btn=document.getElementById('themeBtn');
  btn.innerHTML=document.body.classList.contains('light')?'☀️ Claro':'🌙 Escuro';
  localStorage.setItem('dashTheme',document.body.classList.contains('light')?'light':'dark');
}
if(localStorage.getItem('dashTheme')==='light'){document.body.classList.add('light');document.getElementById('themeBtn').innerHTML='☀️ Claro';}

function bg(c){if(!c)return'';var m={'ALTA':'b-a','MEDIA':'b-m','BAIXA':'b-b'};return'<span class="b '+(m[c]||'b-p')+'">'+c+'</span>';}
function rg(r){if(!r)return'';if(r.indexOf('MANUAL')>=0||r.indexOf('NENHUMA')>=0)return'<span class="b b-man">'+r+'</span>';if(r=='INFORMATIVO_SEM_PRAZO')return'<span class="b b-info">INFORMATIVO</span>';if(r=='PENDENTE'||r=='PENDENTE_CLASSIFICACAO'||r=='ERRO_CLASSIFICACAO')return'<span class="b b-p">'+r+'</span>';return r;}

function openVL(idx){
  var r=D[idx];
  var txt=(r.texto||'').replace(/\\\\n/g,'\\n').replace(/\\n/g,' ');
  // LIMPEZA PROFUNDA: remover CSS/HTML residual do DJEN
  var clean=txt;
  // Remover blocos de style/CSS (body{...}, #div{...}, etc)
  clean=clean.replace(/[#.]?[a-zA-Z][\\w-]*\\s*\\{[^}]*\\}/g,' ');
  // Remover propriedades CSS soltas (padding:10px, font-family:..., etc)
  clean=clean.replace(/[a-z-]+\\s*:\\s*[^;\\n]+;?/gi,function(m){
    // Manter se nao parecer CSS (ex: "prazo: 5 dias" nao tem semicolon)
    if(/font-family|padding|margin|color|background|border|display|width|height|line-height|text-align|font-size|font-weight|font-style/i.test(m))return' ';
    return m;
  });
  // Remover tags HTML residuais
  clean=clean.replace(/<[^>]+>/g,' ');
  // Remover entities HTML
  clean=clean.replace(/&[a-z]+;/gi,' ').replace(/&#\\d+;/g,' ');
  // Normalizar espacos
  clean=clean.replace(/\\s+/g,' ').trim();
  // Sentence case
  var upper=clean.replace(/[^A-Z]/g,'').length;
  var alpha=clean.replace(/[^a-zA-Z]/g,'').length;
  if(alpha>0&&upper/alpha>0.6){
    clean=clean.toLowerCase().replace(/(^|[.!?;:]\\s+)([a-z])/g,function(m,p,c){return p+c.toUpperCase()});
    ['INSS','RPV','CLT','CPC','CPF','CNPJ','OAB','TRT','TRF','TST','STJ','STF','DJEN','FGTS'].forEach(function(s){var re=new RegExp('\\\\b'+s.toLowerCase()+'\\\\b','gi');clean=clean.replace(re,s)});
  }
  // Destaques
  clean=clean.replace(/(\\d+)\\s*\\(?([^)]*?)\\)?\\s*(dias?|horas?)/gi,'<strong style="color:#fca5a5">$1 $2 $3</strong>');
  clean=clean.replace(/R\\$\\s*[\\d.,]+/gi,function(m){return'<strong style="color:#4ade80">'+m+'</strong>'});
  clean=clean.replace(/(\\d{2}\\/\\d{2}\\/\\d{4})/g,'<strong style="color:#a5b4fc">$1</strong>');
  ['JULGO PROCEDENTE','JULGO IMPROCEDENTE','ACORDAM','NEGO PROVIMENTO','DOU PROVIMENTO'].forEach(function(t){var re=new RegExp('('+t+')','gi');clean=clean.replace(re,'<strong style="color:#fde68a">$1</strong>')});
  ['SOB PENA DE','REVELIA','PRECLUSAO'].forEach(function(t){var re=new RegExp('('+t+')','gi');clean=clean.replace(re,'<strong style="color:#fb923c">$1</strong>')});
  ['INTIME-SE','CITE-SE','DEFIRO','INDEFIRO'].forEach(function(t){var re=new RegExp('('+t+')','gi');clean=clean.replace(re,'<strong style="color:#7dd3fc">$1</strong>')});
  clean=clean.replace(/(https?:\\/\\/[^\\s]+)/g,'<a href="$1" target="_blank" class="url">$1</a>');
  // Quebra em paragrafos
  var frases=[];
  clean.split(/(?<=[.;!?])\\s+/).forEach(function(f){if(f.trim().length>3)frases.push(f.trim())});
  if(frases.length<2&&clean.length>150){
    frases=[];var words=clean.split(/\\s+/),line='';
    words.forEach(function(w){if((line+' '+w).length>180){if(line.trim())frases.push(line.trim());line=w}else{line+=(line?' ':'')+w}});
    if(line.trim())frases.push(line.trim());
  }
  var confColor=r.confianca=='ALTA'?'#30d158':r.confianca=='MEDIA'?'#ffd60a':'#ff453a';

  var w=window.open('','_blank');
  var h='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+r.processo+'</title>';
  h+='<style>';
  h+='*{margin:0;padding:0;box-sizing:border-box}';
  h+='html,body{background:#000;color:#f5f5f7;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}';
  h+='body{background:radial-gradient(ellipse at top,#0a0a0a 0%,#000 50%)}';
  h+='.layout{display:grid;grid-template-columns:1fr 360px;min-height:100vh}';
  h+='.main{padding:0;overflow-y:auto}';
  h+='.hero{padding:48px 56px 32px}';
  h+='.crumb{font-size:11px;color:#636366;margin-bottom:20px;font-weight:500;letter-spacing:0.5px}';
  h+='.crumb span{color:#86868b;margin:0 6px}';
  h+='.titulo{font-size:36px;font-weight:600;color:#f5f5f7;letter-spacing:-1.5px;line-height:1.1}';
  h+='.subt{font-size:13px;color:#86868b;margin-top:10px}';
  h+='.subt strong{color:#d1d1d6;font-weight:500}';
  h+='.meta-grid{display:grid;grid-template-columns:repeat(3,1fr);margin-top:36px;border-top:1px solid rgba(255,255,255,0.06)}';
  h+='.meta-item{padding:16px 20px 16px 0;border-bottom:1px solid rgba(255,255,255,0.06);border-right:1px solid rgba(255,255,255,0.06)}';
  h+='.meta-item:nth-child(3n){border-right:none}';
  h+='.meta-item .ml{font-size:10px;color:#636366;text-transform:uppercase;letter-spacing:1.2px;font-weight:600;margin-bottom:5px}';
  h+='.meta-item .mv{font-size:14px;color:#f5f5f7;font-weight:500}';
  h+='.page-wrap{padding:20px 56px 64px}';
  h+='.page{background:linear-gradient(180deg,#1c1c1e 0%,#161618 100%);border:1px solid rgba(255,255,255,0.04);border-radius:14px;padding:48px 56px;box-shadow:0 12px 32px rgba(0,0,0,0.3)}';
  h+='.page-intro{font-size:10px;color:#636366;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid rgba(255,255,255,0.06)}';
  h+='.page p{font-size:15px;line-height:1.9;color:#d1d1d6;margin-bottom:20px;text-align:left}';
  h+='.url{display:inline-block;font-family:"SF Mono",Menlo,monospace;font-size:11px;color:#64d2ff;background:rgba(100,210,255,0.08);padding:2px 8px;border-radius:5px;word-break:break-all;max-width:100%;letter-spacing:-0.3px}';
  h+='.prazo-banner{background:linear-gradient(135deg,#1a0a0a 0%,#0a0505 100%);border:1px solid rgba(255,69,58,0.15);border-radius:12px;padding:20px 28px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between}';
  h+='.prazo-banner .pb-l{font-size:10px;color:#ff453a;text-transform:uppercase;letter-spacing:2px;font-weight:700}';
  h+='.prazo-banner .pb-v{font-size:32px;color:#ff6961;font-weight:700;letter-spacing:-1.5px;line-height:1;margin-top:3px}';
  h+='.side{padding:48px 28px;position:sticky;top:0;height:100vh;overflow-y:auto;border-left:1px solid rgba(255,255,255,0.06)}';
  h+='.btn-primary{display:block;text-align:center;padding:12px 18px;background:linear-gradient(180deg,#4a3f8a,#3d3372);color:#fff;border:none;border-radius:10px;text-decoration:none;font-size:13px;font-weight:600;box-shadow:0 4px 12px rgba(74,63,138,0.25)}';
  h+='.btn-primary:hover{transform:translateY(-1px)}';
  h+='.btn-ghost{display:block;text-align:center;padding:10px 14px;color:#ffd60a;text-decoration:none;font-size:11px;margin-top:8px;font-weight:500;border:1px solid rgba(255,245,150,0.3);border-radius:999px;background:rgba(255,214,10,0.03)}';
  h+='.btn-ghost:hover{border-color:rgba(255,245,150,0.6);background:rgba(255,214,10,0.08)}';
  h+='.side-section{margin-bottom:32px}';
  h+='.side-title{font-size:10px;color:#636366;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin-bottom:16px}';
  h+='.ia-regra{font-size:20px;color:#bf5af2;font-weight:600;line-height:1.25;letter-spacing:-0.5px;margin-bottom:16px}';
  h+='.ia-chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:24px}';
  h+='.ia-chip{padding:5px 12px;border-radius:16px;font-size:11px;font-weight:600;background:rgba(255,255,255,0.06);color:#d1d1d6;border:1px solid rgba(255,255,255,0.06)}';
  h+='.ia-chip.alta{background:rgba(48,209,88,0.1);color:#30d158;border-color:rgba(48,209,88,0.2)}';
  h+='.ia-chip.media{background:rgba(255,214,10,0.1);color:#ffd60a;border-color:rgba(255,214,10,0.2)}';
  h+='.ia-chip.baixa{background:rgba(255,69,58,0.1);color:#ff453a;border-color:rgba(255,69,58,0.2)}';
  h+='.ia-chip.prazo{background:rgba(255,69,58,0.1);color:#ff6961;border-color:rgba(255,69,58,0.2)}';
  h+='.info-block{margin-bottom:20px}';
  h+='.info-block .ib-l{font-size:10px;color:#636366;text-transform:uppercase;letter-spacing:1.2px;font-weight:600;margin-bottom:8px}';
  h+='.info-block .ib-v{font-size:13px;color:#d1d1d6;line-height:1.7}';
  h+='.info-block .ib-v.quote{font-size:13px;color:#a1a1a6;font-style:italic;padding-left:14px;border-left:2px solid rgba(255,255,255,0.08)}';
  h+='.dados-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04)}';
  h+='.dados-row:last-child{border:none}';
  h+='.dados-row .dr-k{font-size:11px;color:#636366}';
  h+='.dados-row .dr-v{font-size:12px;color:#d1d1d6;font-weight:500;text-align:right;max-width:65%}';
  h+='</style></head><body>';
  h+='<div class="layout"><div class="main"><div class="hero">';
  h+='<div class="crumb">'+r.data+'<span>/</span>'+r.natureza+'<span>/</span>'+r.tribunal+'</div>';
  h+='<h1 class="titulo">'+r.processo+'</h1>';
  h+='<div class="subt"><strong>'+r.tipo_doc+'</strong> &middot; '+r.natureza+'</div>';
  h+='<div class="meta-grid">';
  h+='<div class="meta-item"><div class="ml">Cliente</div><div class="mv">'+(r.cliente||'-')+'</div></div>';
  if(r.adverso)h+='<div class="meta-item"><div class="ml">Adverso</div><div class="mv">'+r.adverso+'</div></div>';
  h+='<div class="meta-item"><div class="ml">Natureza</div><div class="mv">'+r.natureza+'</div></div>';
  if(r.tipo_acao)h+='<div class="meta-item"><div class="ml">Acao</div><div class="mv">'+r.tipo_acao+'</div></div>';
  if(r.tipo_processo)h+='<div class="meta-item"><div class="ml">Tipo de Processo</div><div class="mv">'+r.tipo_processo+'</div></div>';
  if(r.valor_causa)h+='<div class="meta-item"><div class="ml">Valor da Causa</div><div class="mv" style="color:#4ade80;font-weight:700">R$ '+r.valor_causa+'</div></div>';
  if(r.fase_atual)h+='<div class="meta-item"><div class="ml">Fase atual</div><div class="mv">'+r.fase_atual+'</div></div>';
  h+='<div class="meta-item"><div class="ml">Tribunal</div><div class="mv">'+r.tribunal+'</div></div>';
  h+='</div></div>';
  h+='<div class="page-wrap"><div class="page">';
  h+='<div class="page-intro">Teor da Intimacao</div>';
  if(r.prazo)h+='<div class="prazo-banner"><div><div class="pb-l">Prazo identificado</div><div class="pb-v">'+r.prazo+' dias</div></div><div style="font-size:40px;opacity:0.3">⏱</div></div>';
  frases.forEach(function(f){h+='<p>'+f+'</p>'});
  h+='</div></div></div>';
  h+='<div class="side">';
  if(r.dj_url)h+='<a class="btn-primary" href="'+r.dj_url+'" target="_blank">Abrir no DataJuri →</a>';
  if(r.djen_link)h+='<a class="btn-ghost" href="'+r.djen_link+'" target="_blank">Ver documento DJEN</a>';
  h+='<div class="side-section" style="margin-top:32px">';
  h+='<div class="side-title">Classificacao</div>';
  h+='<div class="ia-regra">'+(r.regra||'Pendente')+'</div>';
  h+='<div class="ia-chips">';
  if(r.confianca)h+='<span class="ia-chip '+r.confianca.toLowerCase()+'">'+r.confianca+'</span>';
  if(r.prazo)h+='<span class="ia-chip prazo">'+r.prazo+' dias</span>';
  h+='</div>';
  if(r.justificativa)h+='<div class="info-block"><div class="ib-l">Justificativa</div><div class="ib-v">'+r.justificativa+'</div></div>';
  if(r.observacoes)h+='<div class="info-block"><div class="ib-l">Observacoes</div><div class="ib-v">'+r.observacoes+'</div></div>';
  if(r.flags)h+='<div class="info-block"><div class="ib-l">Alertas</div><div class="ib-v" style="color:#ff9f0a">'+r.flags+'</div></div>';
  h+='</div>';
  if(r.raciocinio)h+='<div class="side-section"><div class="side-title">Raciocinio</div><div class="info-block"><div class="ib-v quote">'+r.raciocinio+'</div></div></div>';
  h+='<div class="side-section"><div class="side-title">Processo</div>';
  h+='<div class="dados-row"><span class="dr-k">Numero</span><span class="dr-v">'+r.processo+'</span></div>';
  h+='<div class="dados-row"><span class="dr-k">Data</span><span class="dr-v">'+r.data+'</span></div>';
  h+='<div class="dados-row"><span class="dr-k">Tribunal</span><span class="dr-v">'+r.tribunal+'</span></div>';
  if(r.assunto_dj)h+='<div class="dados-row"><span class="dr-k">Assunto</span><span class="dr-v">'+r.assunto_dj+'</span></div>';
  h+='<div class="dados-row"><span class="dr-k">Cliente</span><span class="dr-v">'+(r.cliente||'-')+'</span></div>';
  if(r.adverso)h+='<div class="dados-row"><span class="dr-k">Adverso</span><span class="dr-v">'+r.adverso+'</span></div>';
  h+='</div></div></div></body></html>';
  w.document.write(h);
  w.document.close();
}

function render(rows){
  var tb=document.getElementById('tb');
  if(!rows.length){tb.innerHTML='<tr><td colspan="10" class="empty">Nenhuma publicacao encontrada</td></tr>';return;}
  var h='';
  for(var i=0;i<rows.length;i++){
    var r=rows[i];var oi=D.indexOf(r);
    var rc=r.regra.indexOf('MANUAL')>=0||r.regra.indexOf('NENHUMA')>=0?'rm':r.confianca=='BAIXA'?'rb':'';
    var dj=r.dj_url?'<a class="dj" href="'+r.dj_url+'" target="_blank" onclick="event.stopPropagation()">'+r.processo+'</a>':r.processo;
    var dl=r.djen_link?' <a href="'+r.djen_link+'" target="_blank" onclick="event.stopPropagation()" style="font-size:10px;color:#64748b">[DJEN]</a>':'';
    // Mostrar inteiro teor da publicacao (limitado)
    var teor=(r.texto||'').replace(/<[^>]+>/g,' ').replace(/\\s+/g,' ').trim();
    if(teor.length>280)teor=teor.substring(0,280)+'…';
    // GT V3 badge
    var gtHtml='';
    if(r.gt_status==='CONCORDA')gtHtml='<span class="b b-a" title="GT confirma: '+r.gt_regra+'">✓ '+r.gt_sim+'</span>';
    else if(r.gt_status==='CONFLITO')gtHtml='<span class="b b-b" title="GT sugere: '+r.gt_regra+' (sim: '+r.gt_sim+')">⚠ '+r.gt_sim+'</span>';
    else if(r.gt_status==='PRECEDENTE_FRACO')gtHtml='<span class="b b-p" title="Precedente fraco">~</span>';
    h+='<tr class="'+rc+'" onclick="openVL('+oi+')"><td>'+dj+dl+'</td><td style="white-space:nowrap">'+r.data+'</td><td>'+r.natureza+'</td><td>'+r.tribunal+'</td><td>'+r.tipo_doc+'</td><td>'+rg(r.regra)+'</td><td>'+bg(r.confianca)+'</td><td style="font-weight:700;color:#fca5a5">'+(r.prazo?r.prazo+'d':'')+'</td><td>'+gtHtml+'</td><td class="obs">'+teor+'</td><td class="flag">'+r.flags+'</td></tr>';
  }
  tb.innerHTML=h;
  updateStats(rows);
}

function updateStats(rows){
  var pend=['PENDENTE','PENDENTE_CLASSIFICACAO','','ERRO_CLASSIFICACAO'];
  var excl=pend.concat(['INFORMATIVO_SEM_PRAZO']);
  document.getElementById('st').textContent=rows.length;
  document.getElementById('sw').textContent=rows.filter(function(r){return r.regra&&excl.indexOf(r.regra)<0&&r.regra.indexOf('MANUAL')<0&&r.regra.indexOf('NENHUMA')<0}).length;
  document.getElementById('sr').textContent=rows.filter(function(r){return r.regra.indexOf('MANUAL')>=0||r.regra.indexOf('NENHUMA')>=0}).length;
  document.getElementById('si').textContent=rows.filter(function(r){return r.regra=='INFORMATIVO_SEM_PRAZO'}).length;
  document.getElementById('sp').textContent=rows.filter(function(r){return pend.indexOf(r.regra)>=0}).length;
  if(document.getElementById('sgc'))document.getElementById('sgc').textContent=rows.filter(function(r){return r.gt_status==='CONCORDA'}).length;
  if(document.getElementById('sgk'))document.getElementById('sgk').textContent=rows.filter(function(r){return r.gt_status==='CONFLITO'}).length;
}

function applyFilters(){
  var busca=document.getElementById('fb').value.toLowerCase();
  var r=D.filter(function(x){
    // Multi-select filters (vazio = todos)
    if(filters.fn.length>0&&filters.fn.indexOf(x.natureza)<0)return false;
    if(filters.fc.length>0&&filters.fc.indexOf(x.confianca)<0)return false;
    if(filters.ft.length>0&&filters.ft.indexOf(x.tribunal)<0)return false;
    if(filters.ftd.length>0&&filters.ftd.indexOf(x.tipo_doc)<0)return false;
    if(filters.fd.length>0&&filters.fd.indexOf(x.data)<0)return false;
    if(filters.fr.length>0&&filters.fr.indexOf(x.regra)<0)return false;
    if(busca&&x.processo.toLowerCase().indexOf(busca)<0)return false;
    // Card filter
    var pend=['PENDENTE','PENDENTE_CLASSIFICACAO','','ERRO_CLASSIFICACAO'];
    var excl=pend.concat(['INFORMATIVO_SEM_PRAZO']);
    if(cardFilter){
      if(cardFilter==='all')return true;
      if(cardFilter==='workflow'&&(!x.regra||excl.indexOf(x.regra)>=0||x.regra.indexOf('MANUAL')>=0||x.regra.indexOf('NENHUMA')>=0))return false;
      if(cardFilter==='regra:MANUAL'&&x.regra.indexOf('MANUAL')<0&&x.regra.indexOf('NENHUMA')<0)return false;
      if(cardFilter==='regra:INFORMATIVO_SEM_PRAZO'&&x.regra!='INFORMATIVO_SEM_PRAZO')return false;
      if(cardFilter==='regra:PENDENTE'&&pend.indexOf(x.regra)<0)return false;
      if(cardFilter==='gt:CONCORDA'&&x.gt_status!=='CONCORDA')return false;
      if(cardFilter==='gt:CONFLITO'&&x.gt_status!=='CONFLITO')return false;
    }
    return true;
  });
  render(r);
}
function f(){applyFilters();}

// Cards clicaveis
document.querySelectorAll('.sc').forEach(function(c){
  c.addEventListener('click',function(){
    var filter=c.dataset.filter;
    if(cardFilter===filter){
      cardFilter=null;
      document.querySelectorAll('.sc').forEach(function(x){x.classList.remove('active')});
    }else{
      cardFilter=filter;
      document.querySelectorAll('.sc').forEach(function(x){x.classList.remove('active')});
      c.classList.add('active');
    }
    applyFilters();
  });
});

// Multi-select dropdowns
function buildMultiSelect(id,values){
  var container=document.getElementById('opts-'+id);
  container.innerHTML='';
  values.forEach(function(v){
    var opt=document.createElement('div');
    opt.className='multi-opt';
    opt.innerHTML='<input type="checkbox" data-val="'+v+'"><span class="lb-opt">'+v+'</span>';
    opt.addEventListener('click',function(e){
      if(e.target.tagName!=='INPUT'){
        var cb=opt.querySelector('input');
        cb.checked=!cb.checked;
      }
      updateMultiFilter(id);
    });
    container.appendChild(opt);
  });
}

function updateMultiFilter(id){
  var checked=Array.from(document.querySelectorAll('#opts-'+id+' input:checked')).map(function(cb){return cb.dataset.val});
  filters[id]=checked;
  var btn=document.querySelector('.multi-btn[data-filter="'+id+'"]');
  if(checked.length===0){btn.textContent='Todas';btn.classList.remove('has-val');}
  else if(checked.length===1){btn.textContent=checked[0];btn.classList.add('has-val');}
  else{btn.textContent=checked.length+' selecionados';btn.classList.add('has-val');}
  // Reapply opt classes
  document.querySelectorAll('#opts-'+id+' .multi-opt').forEach(function(o){
    var cb=o.querySelector('input');
    if(cb.checked)o.classList.add('selected');else o.classList.remove('selected');
  });
  applyFilters();
}

function selectAll(id){
  document.querySelectorAll('#opts-'+id+' input').forEach(function(cb){cb.checked=true});
  updateMultiFilter(id);
}
function clearAll(id){
  document.querySelectorAll('#opts-'+id+' input').forEach(function(cb){cb.checked=false});
  updateMultiFilter(id);
}

function clearAllFilters(){
  ['fn','fc','ft','ftd','fd','fr'].forEach(function(id){clearAll(id)});
  document.getElementById('fb').value='';
  cardFilter=null;
  document.querySelectorAll('.sc').forEach(function(x){x.classList.remove('active')});
  applyFilters();
}

// Toggle dropdown
document.querySelectorAll('.multi-btn[data-filter]').forEach(function(btn){
  btn.addEventListener('click',function(e){
    e.stopPropagation();
    var dd=btn.nextElementSibling;
    // Fechar outros
    document.querySelectorAll('.multi-dropdown.open').forEach(function(x){if(x!==dd)x.classList.remove('open')});
    dd.classList.toggle('open');
  });
});
document.addEventListener('click',function(){
  document.querySelectorAll('.multi-dropdown.open').forEach(function(x){x.classList.remove('open')});
});

function s(col){
  if(sc==col)sa=!sa;else{sc=col;sa=true;}
  var k=['processo','data','natureza','tribunal','tipo_doc','regra','confianca','prazo'];
  D.sort(function(a,b){var va=a[k[col]]||'',vb=b[k[col]]||'';return sa?va.localeCompare(vb):vb.localeCompare(va);});
  applyFilters();
}

// Populate
var tribs=[...new Set(D.map(function(r){return r.tribunal}).filter(Boolean))].sort();
var datas=[...new Set(D.map(function(r){return r.data}).filter(Boolean))].sort().reverse();
var regras=[...new Set(D.map(function(r){return r.regra}).filter(Boolean))].sort();
var tipos=[...new Set(D.map(function(r){return r.tipo_doc}).filter(Boolean))].sort();
var natur=[...new Set(D.map(function(r){return r.natureza}).filter(Boolean))].sort();
buildMultiSelect('fn',natur);
buildMultiSelect('fc',['ALTA','MEDIA','BAIXA']);
buildMultiSelect('ft',tribs);
buildMultiSelect('ftd',tipos);
buildMultiSelect('fd',datas);
buildMultiSelect('fr',regras);

render(D);
</script>
</body>
</html>"""

with open("dashboard_prazos.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"Dashboard: {total} | ALTA:{alta} MEDIA:{media} BAIXA:{baixa} MANUAL:{manual} INFO:{info} PEND:{pendentes}")
