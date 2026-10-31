# ROADMAP — MVP

Legenda: `[ ]` a fazer, `[~]` em andamento, `[x]` feito. Cada tarefa tem critério de pronto (CP). Só marque `[x]` quando o CP for verificado.

## Estado atual

- Última atualização: 2026-10-31
- Fase em curso: Fases 0, 1 e 2 concluídas (T0.1 a T2.7); próxima: T3.1
- Pendências de decisão que bloqueiam: ver `PLANO.md`, seção 4 (escala 1–5, desenho amostral). Nenhuma bloqueia as Fases 0 a 2.
- Anotações da última sessão: Fase 2 feita em `backend/` (39 testes, `python -m pytest backend`). Rotas sob `/api/session/{token}` (sessão, `page/{n}`, `rating`) e `/api/vol/{opaque_id}`; o token vai no caminho, não em header, para o front poder montar o link simples. A página não traz id do caso, só `position`; a nota é enviada com `position` + `slot` e o servidor descobre o caso. O JSON da página tem `sequence`, `columns[{slot,url}]` e `ratings` (nota vigente por slot, para retomar). Ordem de páginas e colunas sai de `random.Random` com semente em texto; é gravada em `assignment` na primeira entrada. `rating_event` tem gatilhos SQLite que barram UPDATE e DELETE. O carregador recusa caso cujos 5 arquivos tenham tamanhos diferentes. Ver `docs/decisions/0002-backend.md`. Pendente: o desenho amostral (PLANO seção 4, item 2) ainda não existe; por ora cada médico recebe `min(50, nº de casos)` páginas em ordem sorteada, sem repetir caso. Não rodei o servidor com uvicorn (só o cliente de teste, com os 8 casos reais: os 5 volumes saem com 6.212.782 bytes). Sem CORS: o front deve usar proxy do Vite (T3.1). Obs.: as 7 tarefas foram feitas numa sessão só, a pedido do Rafael.

## Fase 0 — Spike do viewer (usa o `case_01` do testkit)

Objetivo: provar que o viewer funciona como imaginamos, antes de construir o resto.

- [x] **T0.1** Criar `frontend/` (Vite + TS + Niivue) e exibir um volume do `case_01`. CP: abre em localhost e mostra as 3 vistas.
- [x] **T0.2** 5 instâncias Niivue lado a lado, cada uma com 3 vistas em coluna. CP: os 5 volumes do caso aparecem em 15 painéis.
- [x] **T0.3** Scroll independente por vista, aplicado às 5 colunas, com o clique de crosshair desativado. CP: rolar sobre uma axial move só as 5 axiais; coronal e sagital não mudam.
- [x] **T0.4** Setas por linha e brilho/contraste globais com "Restaurar". CP: ambos afetam as 5 colunas.
- [x] **T0.5** Viewer ampliado (lupa): scroll, zoom contínuo e troca de coluna mantendo a vista. CP: scroll no ampliado acompanha a vista na grade.
- [x] **T0.6** Registrar em `docs/decisions/0001-viewer.md` o que funcionou, limitações e a decisão final (Niivue sim ou não). CP: documento escrito.
- [x] **T0.7** Fazer o viewer acompanhar o zoom do navegador (Ctrl + e Ctrl −) e o redimensionamento da janela. Feedback do Rafael ao validar a Fase 0. CP: com zoom de 50% a 200% as 15 imagens continuam nítidas, sem corte e sem desalinhar as colunas.

## Fase 1 — Preparação dos dados (`scripts/`)

Objetivo: transformar um lote no formato do testkit em arquivos servíveis, sem revelar a origem.

- [x] **T1.1** Script que lê o caso (volumes + `info.txt`) sem tocar no gabarito e confere shape e orientação iguais nos 5 volumes. CP: teste passa nos 8 casos; falha com mensagem clara em um caso adulterado.
- [x] **T1.2** Reempacotar em inteiro de 16 bits, sem compressão, com header limpo. CP: teste confirma que os 5 volumes de cada caso têm exatamente o mesmo tamanho em bytes.
- [x] **T1.3** Gerar IDs opacos (UUID) e o manifesto (`case`, `slot`, `opaque_id`, shape, espaçamento, dataset, sequência). CP: nenhum nome de arquivo, caminho ou campo contém modelo ou "real".
- [x] **T1.4** Teste de vazamento: varrer a saída e provar que não existe a palavra de nenhum modelo nem o gabarito. CP: teste passa.
- [x] **T1.5** Rodar nos 8 casos e documentar o comando em `CLAUDE.md`. CP: saída em `data/` (fora do git).

## Fase 2 — Backend (`backend/`)

- [x] **T2.1** Esqueleto FastAPI + SQLite (WAL) + modelos (`case`, `volume`, `rater`, `assignment`, `rating_event`). CP: sobe e cria o banco.
- [x] **T2.2** Carregar o manifesto no banco. CP: casos e volumes consultáveis, sem campo de origem.
- [x] **T2.3** Token por médico e criação de `rater` com semente. CP: link com token abre a sessão; token inválido dá erro claro.
- [x] **T2.4** Sorteio reprodutível da ordem das páginas e das colunas por semente. CP: mesma semente dá a mesma ordem; testes de distribuição sem erro.
- [x] **T2.5** Endpoint de página (dados do caso e ordem dos slots, sem origem) e endpoint de volume por ID opaco. CP: o JSON da página não contém nada além de slot, sequência e URLs opacas.
- [x] **T2.6** Endpoint de nota append-only e idempotente (`client_event_id`). CP: reenvio não duplica; corrigir cria nova linha; nota fora de 1–5 é rejeitada.
- [x] **T2.7** Retomar progresso. CP: reabrir o link leva à primeira página sem nota completa.

## Fase 3 — Front completo

- [ ] **T3.1** Integrar o front do spike com a API (carregar página e volumes). CP: página real exibida com a ordem sorteada.
- [ ] **T3.2** Nota 1–5 por coluna com autosave e comentário opcional. Reservar uma faixa fixa abaixo das imagens, com as notas alinhadas às colunas (as imagens ficam menores; a lupa dá o detalhe). CP: recarregar a página mantém as notas e a grade ainda cabe na tela.
- [ ] **T3.3** Anterior/Próxima, progresso (n/50) e aviso de colunas sem nota. CP: não finaliza com nota faltando sem aviso.
- [ ] **T3.4** Tela de entrada, instruções (em português) e tela final. CP: fluxo completo de ponta a ponta no navegador.
- [ ] **T3.5** Registrar o `viewer_state` (cortes e brilho/contraste) em cada nota. CP: aparece na linha gravada.
- [ ] **T3.6** Pré-carregar a próxima página. CP: troca de página sem espera visível no testkit local.

## Fase 4 — Exportação

- [ ] **T4.1** Exportação CSV de todas as notas (uma linha por nota, com slot, posição na tela e `viewer_state`). CP: abre no pandas sem tratamento.
- [ ] **T4.2** Proteger a rota de admin com senha por variável de ambiente. CP: sem a senha, não exporta.

## Fase 5 — Teste ponta a ponta e documentação

- [ ] **T5.1** Script que simula um médico respondendo os 8 casos, exporta o CSV e compara com o `answer_key.csv`. CP: tudo confere (casos, slots, quantidade de notas).
- [ ] **T5.2** Checagem manual no navegador: nada na aba de rede, no HTML ou no JS revela a origem. CP: lista de conferência assinada.
- [ ] **T5.3** Nota técnica (stack, hospedagem, biblioteca) e documento de hospedagem e acesso em `docs/`. CP: escritos.

**MVP pronto** quando T5.1 a T5.3 estiverem marcadas.

## Depois do MVP (não começar antes)

Piloto com 2–3 pessoas, ranking dos 5 volumes, inglês, treino, atalhos, perfil, admin completo, backup automático, hospedagem no LIDS.
