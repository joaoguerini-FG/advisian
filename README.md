# Controller de Prazos - Furtado Guerini

Sistema de classificação automática de intimações DJEN com IA.

## Dashboard online

Acesse o dashboard em: **https://SEU_USUARIO.github.io/controller-prazos/dashboard_prazos.html**

Atualizado automaticamente todo dia às 8h (horário de Brasília).

## Arquitetura

1. **Captura DJEN** → API pública CNJ, 3 filtros (OAB, nome pessoal, nome escritório)
2. **Enriquecimento DataJuri** → contexto processual via API OAuth
3. **Classificação IA** → GPT-4.1 com base de conhecimento + ground truth
4. **Validação** → filtros hard por natureza + retry automático
5. **Dashboard HTML** → interativo com filtros multi-select + Visual Law

## Arquivos principais

- `pipeline_diario.py` — executado pelo GitHub Action
- `motor_definitivo.py` — classificador com todas as validações
- `dash_simples.py` — gera o HTML do dashboard
- `base_conhecimento.json` — regras do DataJuri + exemplos GOLD
- `intimacoes_state.json` — histórico de publicações classificadas

## Setup local

```bash
pip install requests openai openpyxl
```

## Setup GitHub Actions (secrets necessários)

No repo > Settings > Secrets and variables > Actions > New repository secret:

- `DATAJURI_CLIENT_ID`
- `DATAJURI_SECRET`
- `DATAJURI_USER`
- `DATAJURI_PASS`
- `OPENAI_API_KEY`

## Execução manual

```bash
# Pipeline diário (captura + classifica)
python pipeline_diario.py

# Regenerar dashboard HTML
python dash_simples.py
```
