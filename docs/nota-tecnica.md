# Nota técnica

Plataforma para médicos avaliarem, em condição cega, a fidelidade de volumes de MRI cerebral (1 original e 4 reconstruções de autoencoder por caso, nota 1–5 por volume). Decisões e requisitos: `PLANO.md`. Estado das tarefas: `docs/ROADMAP.md`.

## Stack

| Camada | Escolha | Motivo |
|---|---|---|
| Viewer | Niivue 0.69 (WebGL), 5 instâncias + 1 para a lupa | Lê NIfTI, respeita o espaçamento do voxel. Ver `docs/decisions/0001-viewer.md` |
| Front | Vite + TypeScript, sem framework de UI | A tela é uma grade com estado simples |
| Back | Python + FastAPI + SQLModel | Mesmo ambiente dos scripts de preparação |
| Banco | SQLite em modo WAL, um arquivo (`data/app.db`) | ~20 médicos e poucos milhares de notas; backup é copiar o arquivo |
| Dados | `scripts/prepare_data.py` → `data/prepared/` | Volumes em inteiro de 16 bits sem compressão, mesmo tamanho em bytes, UUID como nome |

## Como o cegamento é garantido

1. O banco, a API e o CSV guardam só o **slot** (A–E). A ligação slot → modelo existe apenas no `answer_key.csv`, que o back nunca lê.
2. Volumes saem por UUID, sem compressão HTTP, todos do mesmo tamanho. Header NIfTI limpo.
3. A posição na tela é sorteada por médico e por página, com semente guardada. A análise refaz a ordem pelo CSV (`screen_position`).
4. Notas são append-only: gatilhos do SQLite barram `UPDATE` e `DELETE`; corrigir cria nova linha. A nota vigente é a última por médico, caso e slot.

Conferência: `docs/checklist-cegamento.md` e o teste ponta a ponta abaixo.

## API

| Rota | Função |
|---|---|
| `GET /api/session/{token}` | Progresso e próxima página |
| `GET /api/session/{token}/page/{n}` | Slots na ordem da tela, URLs opacas, notas vigentes |
| `POST /api/session/{token}/rating` | Nota 1–5, idempotente por `client_event_id`, com `viewer_state` |
| `GET /api/vol/{uuid}` | Volume |
| `GET /api/admin/export.csv` | CSV de todas as notas; senha em `MRI_ADMIN_PASSWORD`, rota desligada sem ela |

## Testes

```
python -m pytest backend scripts      # 62 testes (inclui o ponta a ponta)
python scripts/e2e_check.py           # médico simulado, 8 casos, CSV vs answer_key.csv
npx tsc --noEmit                      # dentro de frontend/
```

`scripts/e2e_check.py` responde as 5 colunas das 8 páginas pela API, exporta o CSV e confere: mesmos casos do gabarito, cada slot uma vez, 40 notas, dataset e sequência iguais, posições de tela 1 a 5 por caso. É o único código, além dos testes, que lê o gabarito.

## Para analisar

Juntar o CSV exportado com `answer_key.csv` por `case` e `slot` (pandas). Guardar cópias do gabarito fora do servidor e do repositório: sem ele não dá para analisar por modelo.

## Limitações conhecidas

- Desenho amostral indefinido: hoje cada médico vê as 8 páginas do testkit, uma por caso (`PLANO.md`, seção 4, item 2).
- Texto e âncoras da escala 1–5 ainda são proposta; licenças dos datasets ainda não constam nas instruções.
- Viewer testado em um navegador; falta Chrome, Firefox e Safari, e telas pequenas ou toque (`docs/decisions/0001-viewer.md`).
- Sem painel de admin: só o CSV. Sem backup automático.
