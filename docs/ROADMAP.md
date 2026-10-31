# ROADMAP — MVP

Legenda: `[ ]` a fazer, `[~]` em andamento, `[x]` feito. Cada tarefa tem critério de pronto (CP). Só marque `[x]` quando o CP for verificado.

## Estado atual

- Última atualização: 2026-10-31
- Fase em curso: Fases 0 a 5 concluídas (T0.1 a T5.3). **MVP pronto**; próximo: piloto (ver "Depois do MVP")
- Pendências de decisão que bloqueiam: ver `PLANO.md`, seção 4 (escala 1–5, desenho amostral). Nenhuma bloqueia as Fases 0 a 2.
- Anotações da última sessão: Fase 5. T5.1: `scripts/e2e_check.py` (e `scripts/tests/test_e2e.py`) simula um médico pela API nos 8 casos, exporta o CSV e confere com o gabarito: 8 casos, 40 notas, slots, dataset, sequência e posições de tela batem. T5.2: verificação automática no navegador e no build do front deu tudo OK (volumes de mesmo tamanho, URLs opacas, header NIfTI vazio, sem nome de modelo no HTML/JS); o Rafael conferiu no Chrome (F12): nomes dos volumes opacos e buscas por nomes de modelo em Elements com 0 resultados; assinatura em `docs/checklist-cegamento.md`. Foi criado um médico de teste ("Checagem T5.2") em `data/app.db`, sem notas. T5.3: `docs/nota-tecnica.md` e `docs/hospedagem-e-acesso.md`. Fase 4 (sessão anterior): feita em `backend/app/export.py` e rota `GET /api/admin/export.csv` (HTTP Basic: usuário qualquer, senha em `MRI_ADMIN_PASSWORD`; sem a variável a rota responde 404, senha errada 401). Uma linha por nota (`rating_event`), com `event_id`, `created_at`, `rater_id`, `rater_name`, `case`, `dataset`, `sequence`, `page_position`, `screen_position` (1–5), `slot`, `score`, `comment`, `viewer_state` (JSON em texto). Só slots, nunca origem; correções aparecem como linhas extras (a nota vigente é a última por rater, case e slot). Aberto no pandas em teste. Não há tela de admin: baixar abrindo a URL no navegador (ele pede a senha). Fase 3 (sessão anterior): feita em `frontend/` (`api.ts`, `viewer.ts`, `main.ts`, `index.html`). Link do médico: `/?t=<token>` (a tela de entrada também aceita o link colado). Vite faz proxy de `/api` para `localhost:8000`; o plugin `/dev-data` do spike saiu. Nota 1–5 salva na hora (cada clique ou comentário é um POST com `client_event_id`, em fila, com nova tentativa se cair a conexão); `viewer_state` = cortes (índice 1-based por vista) + brilho/contraste, conferido no banco. Brilho/contraste persistem entre páginas; cortes voltam ao meio. Próxima/Finalizar avisa colunas sem nota; a tela final diz quantas páginas ainda têm imagens sem nota e leva à primeira incompleta. Pré-carga: busca os 5 volumes da página seguinte (cache HTTP do navegador; conferido que a troca lê do cache). Texto das instruções usa a pergunta e as âncoras *propostas* do PLANO seção 4, item 1 (ainda não aprovadas). Pendente: licenças/atribuição dos datasets nas instruções (PLANO seção 4, item 4); desenho amostral (hoje 8 páginas, uma por caso); a lupa não mostra a nota da coluna (PLANO seção 6, item 4); testado no navegador só por JavaScript (o painel não gerou capturas de tela), então falta uma olhada visual de layout, principalmente a faixa de notas em telas pequenas. Ver `.claude/launch.json` para subir back e front.

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

- [x] **T3.1** Integrar o front do spike com a API (carregar página e volumes). CP: página real exibida com a ordem sorteada.
- [x] **T3.2** Nota 1–5 por coluna com autosave e comentário opcional. Reservar uma faixa fixa abaixo das imagens, com as notas alinhadas às colunas (as imagens ficam menores; a lupa dá o detalhe). CP: recarregar a página mantém as notas e a grade ainda cabe na tela.
- [x] **T3.3** Anterior/Próxima, progresso (n/50) e aviso de colunas sem nota. CP: não finaliza com nota faltando sem aviso.
- [x] **T3.4** Tela de entrada, instruções (em português) e tela final. CP: fluxo completo de ponta a ponta no navegador.
- [x] **T3.5** Registrar o `viewer_state` (cortes e brilho/contraste) em cada nota. CP: aparece na linha gravada.
- [x] **T3.6** Pré-carregar a próxima página. CP: troca de página sem espera visível no testkit local.

## Fase 4 — Exportação

- [x] **T4.1** Exportação CSV de todas as notas (uma linha por nota, com slot, posição na tela e `viewer_state`). CP: abre no pandas sem tratamento.
- [x] **T4.2** Proteger a rota de admin com senha por variável de ambiente. CP: sem a senha, não exporta.

## Fase 5 — Teste ponta a ponta e documentação

- [x] **T5.1** Script que simula um médico respondendo os 8 casos, exporta o CSV e compara com o `answer_key.csv`. CP: tudo confere (casos, slots, quantidade de notas).
- [x] **T5.2** Checagem manual no navegador: nada na aba de rede, no HTML ou no JS revela a origem. CP: lista de conferência assinada.
- [x] **T5.3** Nota técnica (stack, hospedagem, biblioteca) e documento de hospedagem e acesso em `docs/`. CP: escritos.

**MVP pronto** quando T5.1 a T5.3 estiverem marcadas.

## Depois do MVP (não começar antes)

Piloto com 2–3 pessoas, ranking dos 5 volumes, inglês, treino, atalhos, perfil, admin completo, backup automático, hospedagem no LIDS.
