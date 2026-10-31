# Hospedagem e acesso

Estado: a hospedagem no LIDS ainda não foi definida (`PLANO.md`, seção 4, item 6). Este documento descreve o que o app precisa e como colocá-lo no ar, para quando o servidor existir.

## O que o servidor precisa

- Python 3.11+ e Node 20+ (Node só para gerar o front uma vez).
- Disco: ~35 MB por caso (5 volumes de ~6–7 MB) mais o banco. 50 casos ≈ 2 GB.
- Banda: ~30 a 35 MB por página para cada médico (o front pré-carrega a página seguinte).
- **HTTPS** na frente (Caddy ou nginx) ou acesso só por VPN. Sem HTTPS o token do médico e a senha de admin trafegam em texto puro.
- **Não** usar compressão HTTP nos volumes (o tamanho uniforme precisa chegar ao navegador).

## Colocar no ar

1. Preparar os dados em uma máquina do laboratório (o gabarito fica lá):
   `python scripts/prepare_data.py <pasta_do_lote> data/prepared --force`
2. Copiar para o servidor **só** `data/prepared/` (volumes e `manifest.json`), `backend/` e o front gerado. Nunca copiar `answer_key.csv`, `radiologist_grading_testkit/` nem o `.tar.gz`.
3. No servidor, dentro de `backend/`:
   - `pip install -r requirements.txt`
   - `python -m app.cli load-manifest`
   - `python -m uvicorn app.main:app --factory --port 8000` (atrás do proxy reverso)
4. Front: `npm install` e `npm run build` em `frontend/`; servir `frontend/dist/` pelo proxy e encaminhar `/api` para a porta 8000.

Variáveis de ambiente: `MRI_DB_PATH`, `MRI_PREPARED_DIR`, `MRI_PAGES_PER_RATER`, `MRI_ADMIN_PASSWORD`.

## Acesso

- **Médico:** link `https://<servidor>/?t=<token>`. Um token por médico: `python -m app.cli create-rater --name "Nome"` (imprime o token). O link é a credencial; enviar por canal privado. Reabrir o link retoma da primeira página sem nota.
- **Administrador:** definir `MRI_ADMIN_PASSWORD` antes de subir o back e abrir `/api/admin/export.csv` (usuário qualquer, a senha é essa). Sem a variável a rota fica desligada.
- **Analista:** junta o CSV com o `answer_key.csv` por `case` e `slot`.

## Backup

- O banco é `data/app.db` (com `-wal` e `-shm` ao lado enquanto o back roda). Copiar com o back parado, ou exportar o CSV com frequência.
- Guardar o `answer_key.csv` em pelo menos duas cópias, fora do servidor e fora do repositório.

## Perguntas ao LIDS

Docker é permitido? Há acesso externo, HTTPS ou VPN? Quanto disco e banda? Quem faz o backup? (Se Docker for permitido, o plano prevê Docker Compose com Caddy; o gabarito nunca entra na imagem.)
