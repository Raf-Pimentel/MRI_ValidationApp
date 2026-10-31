# 0002 — Backend: forma da API e do sorteio

Data: 2026-10-31. Tarefas: T2.1 a T2.7 (fecham a Fase 2).

## Decisões

- **Rotas.** O token vai no caminho: `GET /api/session/{token}`, `GET /api/session/{token}/page/{n}`, `POST /api/session/{token}/rating`. Volumes: `GET /api/vol/{opaque_id}`, sem token, porque o Niivue carrega por URL e o UUID não é adivinhável. Isso troca os caminhos `/api/page/{n}` e `/api/rating` do desenho inicial (PLANO, seção 5).
- **Página sem id de caso.** O JSON traz só `position`, `total_pages`, `sequence`, `columns[{slot, url}]` (já na ordem da tela) e `ratings` (nota vigente por slot). A nota é enviada com `position` e `slot`; o servidor resolve o caso.
- **Sorteio.** `random.Random` com semente em texto: páginas por `pages:{seed}` e colunas por `columns:{seed}:{case}`. A ordem é gravada em `assignment` na primeira chamada da sessão e nunca mais recalculada. Sem repetir caso para o mesmo médico; cada médico recebe `min(MRI_PAGES_PER_RATER, nº de casos)` páginas, até o desenho amostral ser definido.
- **Append-only no banco.** Gatilhos SQLite barram `UPDATE` e `DELETE` em `ratingevent`, além do `CHECK (score BETWEEN 1 AND 5)`. A nota vigente é a linha mais recente por (médico, caso, slot).
- **Idempotência.** `client_event_id` único. Reenvio devolve o mesmo evento; id já usado por outro médico dá 409.
- **Retomar.** Uma página está completa quando os 5 slots têm ao menos uma nota. `next_position` é a primeira página, na ordem do médico, que não está completa.
- **Carregador.** Recusa caso sem os 5 slots, com arquivo faltando ou com tamanhos diferentes em bytes (regra do tamanho uniforme), e recusa trocar os volumes de um caso já carregado.
- **Sem CORS e sem compressão HTTP.** Em desenvolvimento o front usa proxy do Vite; os volumes saem byte a byte.
