# Setup do Deploy Online (GitHub Pages + Actions)

## Passo 1 — Criar repo no GitHub

1. Vá em https://github.com/new
2. Nome: `controller-prazos` (ou o que preferir)
3. Público (já que escolheu público)
4. **NÃO** inicialize com README (vamos subir o que já temos)
5. Clique "Create repository"

## Passo 2 — Subir código local

Abra PowerShell/CMD na pasta `C:\Users\joaof\Documents\intimacoes`:

```bash
cd C:\Users\joaof\Documents\intimacoes

# Inicializar git
git init
git branch -M main

# Adicionar arquivos (só os que devem ir - .gitignore filtra o resto)
git add .

# Primeiro commit
git commit -m "Initial: Controller de Prazos"

# Conectar com GitHub (substitua SEU_USUARIO)
git remote add origin https://github.com/SEU_USUARIO/controller-prazos.git

# Push
git push -u origin main
```

## Passo 3 — Configurar Secrets

No GitHub, vá no seu repo > **Settings** > **Secrets and variables** > **Actions** > **New repository secret**

Adicione os 5 secrets:

| Nome | Valor |
|---|---|
| `DATAJURI_CLIENT_ID` | `yhju3iaqoi8t6w2ml8i7` |
| `DATAJURI_SECRET` | `8523a356-de6d-4c7f-9241-bcb2f402a1f2` |
| `DATAJURI_USER` | `joaoguerini@furtadoguerini.com.br` |
| `DATAJURI_PASS` | `joaovascaino007` |
| `OPENAI_API_KEY` | `sk-proj-TR0XQbCW...` (sua key completa) |

## Passo 4 — Ativar GitHub Pages

No repo > **Settings** > **Pages**

- Source: **Deploy from a branch**
- Branch: **main** > **/ (root)**
- Save

Em ~1 minuto estará disponível em:
```
https://SEU_USUARIO.github.io/controller-prazos/dashboard_prazos.html
```

## Passo 5 — Rodar Action manualmente (teste)

No repo > **Actions** > **Atualizar Dashboard de Prazos** > **Run workflow** > Run workflow

Em ~5 minutos o pipeline roda, classifica novas publicações e commita. Dashboard atualiza automático.

## Passo 6 — Confirmar schedule

O workflow está configurado para rodar diariamente às **11h UTC (8h Brasília)**.

Para ajustar, edite `.github/workflows/atualizar_dashboard.yml`, linha:

```yaml
- cron: '0 11 * * *'
```

Formato cron: `min hora dia mês dia-semana`.

## Troubleshooting

- **Action falha com "permission denied"**: Settings > Actions > General > Workflow permissions > "Read and write permissions" > Save
- **Pages não carrega**: aguarde até 5 min na primeira vez
- **Dashboard vazio**: verifique se state.json foi commitado (tem que estar fora do .gitignore)
