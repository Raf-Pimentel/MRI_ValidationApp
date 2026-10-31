# MRI_ValidationApp

Plataforma web para médicos avaliarem, em condição cega, a fidelidade (o quão real parece) de volumes de MRI cerebral. Cada caso tem 5 volumes NIfTI: 1 original e 4 reconstruções de autoencoder. O médico dá nota 1–5 por volume.

Fonte da verdade do projeto: `PLANO.md` (decisões e requisitos) e `docs/ROADMAP.md` (tarefas e estado). Leia o ROADMAP antes de começar qualquer trabalho.

## Regras que nunca podem ser quebradas

1. **Cegamento.** O servidor e o navegador nunca recebem a origem de um volume (modelo ou "real"). Só o `slot` (A–E) do arquivo. Nada de nome de modelo em URL, nome de arquivo, header NIfTI, JSON ou log.
2. **Gabarito.** `answer_key.csv` nunca é lido pelo backend, nunca entra no frontend, em imagem Docker ou em pasta servida. Só scripts de teste e de análise offline o leem.
3. **Append-only.** Corrigir uma nota cria uma nova linha em `rating_event`. Nunca `UPDATE` nem `DELETE` em notas.
4. **Tamanho uniforme.** Os 5 volumes de um caso são servidos com o mesmo formato e o mesmo tamanho em bytes (o tamanho do arquivo denuncia o original).

## Stack

- Front: Vite + TypeScript + Niivue (sem framework de UI pesado)
- Back: Python + FastAPI + SQLModel + SQLite (WAL)
- Dados de teste: `radiologist_grading_testkit/` (8 casos reais, 5 volumes cada)
- Ambiente local: Node e Python direto, sem Docker por enquanto

## Comandos

- Instalar o front: `npm install` dentro de `frontend/`
- Rodar o front: `npm run dev` dentro de `frontend/` (http://localhost:5173)
- Checar tipos: `npx tsc --noEmit` dentro de `frontend/`
- O front precisa do back no ar (Vite faz proxy de `/api` para `localhost:8000`). Abrir `http://localhost:5173/?t=<token>`.
- Preparar os dados (Fase 1): `pip install -r scripts/requirements.txt`, depois `python scripts/prepare_data.py radiologist_grading_testkit/radiologist_grading_testkit/testkit data/prepared --force`. Gera `data/prepared/volumes/<uuid>.nii` e `data/prepared/manifest.json`. Nunca lê o gabarito.
- Testes dos scripts: `python -m pytest scripts` (na raiz do repositório).
- Back (dentro de `backend/`): `pip install -r requirements.txt`; `python -m app.cli load-manifest` (carrega `data/prepared/manifest.json` em `data/app.db`); `python -m app.cli create-rater --name "Fulano"` (imprime o token); `python -m uvicorn app.main:app --factory --port 8000`. Variáveis opcionais: `MRI_DB_PATH`, `MRI_PREPARED_DIR`, `MRI_PAGES_PER_RATER`.
- Testes do back: `python -m pytest backend` (na raiz). `python -m pytest backend scripts` roda os dois.

## Como trabalhar aqui

- Uma tarefa do ROADMAP por sessão. Anuncie o ID da tarefa (por exemplo T1.3) no começo.
- Mudanças pequenas e testáveis. Para lógica de backend e scripts de dados, escreva o teste junto.
- Não adicione dependência, camada ou abstração que a tarefa atual não exija. Escopo do MVP está em `PLANO.md`, seção 2.1.
- Ao terminar: rode os testes, marque a tarefa no ROADMAP, anote em "Estado atual" o que ficou pendente, e faça um commit com mensagem clara, sem jargões, em linguagem natural.
- Se uma decisão mudar o que está no `PLANO.md`, registre em `docs/decisions/` (uma página curta) e atualize o PLANO.
- Responda e documente em português. Código, nomes e commits em inglês.
