# ROADMAP — MVP

Legenda: `[ ]` a fazer, `[~]` em andamento, `[x]` feito. Cada tarefa tem critério de pronto (CP). Só marque `[x]` quando o CP for verificado.

## Estado atual

- Última atualização: 2026-10-31
- Fase em curso: Fase 0 (T0.1 a T0.5 feitas; próxima: T0.6)
- Pendências de decisão que bloqueiam: ver `PLANO.md`, seção 4 (escala 1–5, desenho amostral). Nenhuma bloqueia as Fases 0 a 2.
- Anotações da última sessão: T0.5 ok. Lupa 🔍 no canto de cada vista de cada coluna (15 botões, posicionados via `screenSlices`) abre o viewer ampliado: uma 6ª instância Niivue com uma só vista, abaixo da barra (brilho e contraste continuam valendo e afetam também o ampliado). Roda do mouse muda o corte da vista e acompanha a grade; slider de zoom contínuo 100%–600%; arrastar move a imagem; botões A–E ou teclas a–e trocam de coluna mantendo a vista; Esc ou Fechar sai. Detalhe técnico: o Niivue dá zoom em torno da origem do mundo, então o pan é `(1 − zoom) × centro do volume` (testado nas 3 vistas) e o arrasto converte pixels em mm por `fovMM × zoom / largura`. Letras de orientação ficam visíveis (decisão do Rafael). Observação: com a roda, a contagem do corte pode saltar 1 por arredondamento (posição guardada como fração); ver na T0.6. Posição e zoom do ampliado ainda não são gravados.

## Fase 0 — Spike do viewer (usa o `case_01` do testkit)

Objetivo: provar que o viewer funciona como imaginamos, antes de construir o resto.

- [x] **T0.1** Criar `frontend/` (Vite + TS + Niivue) e exibir um volume do `case_01`. CP: abre em localhost e mostra as 3 vistas.
- [x] **T0.2** 5 instâncias Niivue lado a lado, cada uma com 3 vistas em coluna. CP: os 5 volumes do caso aparecem em 15 painéis.
- [x] **T0.3** Scroll independente por vista, aplicado às 5 colunas, com o clique de crosshair desativado. CP: rolar sobre uma axial move só as 5 axiais; coronal e sagital não mudam.
- [x] **T0.4** Setas por linha e brilho/contraste globais com "Restaurar". CP: ambos afetam as 5 colunas.
- [x] **T0.5** Viewer ampliado (lupa): scroll, zoom contínuo e troca de coluna mantendo a vista. CP: scroll no ampliado acompanha a vista na grade.
- [ ] **T0.6** Registrar em `docs/decisions/0001-viewer.md` o que funcionou, limitações e a decisão final (Niivue sim ou não). CP: documento escrito.

## Fase 1 — Preparação dos dados (`scripts/`)

Objetivo: transformar um lote no formato do testkit em arquivos servíveis, sem revelar a origem.

- [ ] **T1.1** Script que lê o caso (volumes + `info.txt`) sem tocar no gabarito e confere shape e orientação iguais nos 5 volumes. CP: teste passa nos 8 casos; falha com mensagem clara em um caso adulterado.
- [ ] **T1.2** Reempacotar em inteiro de 16 bits, sem compressão, com header limpo. CP: teste confirma que os 5 volumes de cada caso têm exatamente o mesmo tamanho em bytes.
- [ ] **T1.3** Gerar IDs opacos (UUID) e o manifesto (`case`, `slot`, `opaque_id`, shape, espaçamento, dataset, sequência). CP: nenhum nome de arquivo, caminho ou campo contém modelo ou "real".
- [ ] **T1.4** Teste de vazamento: varrer a saída e provar que não existe a palavra de nenhum modelo nem o gabarito. CP: teste passa.
- [ ] **T1.5** Rodar nos 8 casos e documentar o comando em `CLAUDE.md`. CP: saída em `data/` (fora do git).

## Fase 2 — Backend (`backend/`)

- [ ] **T2.1** Esqueleto FastAPI + SQLite (WAL) + modelos (`case`, `volume`, `rater`, `assignment`, `rating_event`). CP: sobe e cria o banco.
- [ ] **T2.2** Carregar o manifesto no banco. CP: casos e volumes consultáveis, sem campo de origem.
- [ ] **T2.3** Token por médico e criação de `rater` com semente. CP: link com token abre a sessão; token inválido dá erro claro.
- [ ] **T2.4** Sorteio reprodutível da ordem das páginas e das colunas por semente. CP: mesma semente dá a mesma ordem; testes de distribuição sem erro.
- [ ] **T2.5** Endpoint de página (dados do caso e ordem dos slots, sem origem) e endpoint de volume por ID opaco. CP: o JSON da página não contém nada além de slot, sequência e URLs opacas.
- [ ] **T2.6** Endpoint de nota append-only e idempotente (`client_event_id`). CP: reenvio não duplica; corrigir cria nova linha; nota fora de 1–5 é rejeitada.
- [ ] **T2.7** Retomar progresso. CP: reabrir o link leva à primeira página sem nota completa.

## Fase 3 — Front completo

- [ ] **T3.1** Integrar o front do spike com a API (carregar página e volumes). CP: página real exibida com a ordem sorteada.
- [ ] **T3.2** Nota 1–5 por coluna com autosave e comentário opcional. CP: recarregar a página mantém as notas.
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
