# 0001 — Viewer: usar Niivue

Data: 2026-10-31. Tarefa: T0.6 (fecha a Fase 0).

## Decisão

Usar **Niivue 0.69** como viewer, com **uma instância por coluna** (5) mais **uma instância para o viewer ampliado** (6 no total). Os cliques, arrastos e teclas do Niivue ficam desligados; o controle de corte, brilho, contraste e zoom é feito pelo nosso código. Não há motivo para trocar de biblioteca.

## O que foi testado e funcionou (com o `case_01`, 132×173×136)

- 5 volumes lado a lado, cada um com 3 vistas empilhadas (15 painéis), sem desalinhar colunas.
- Scroll por vista: rolar sobre uma axial move só as 5 axiais; coronal e sagital não mudam.
- Setas ▲▼ por vista, com repetição ao segurar, alinhadas à posição de cada vista.
- Brilho e contraste globais, aplicados às 5 colunas e ao ampliado, com Restaurar.
- Viewer ampliado: scroll acompanhado pela grade, zoom contínuo de 100% a 600% centrado, arrastar para mover, troca de coluna mantendo a vista, Esc para sair.
- Clique, arrasto, toque e teclas não movem nada fora do que programamos.

## Como cada ponto foi resolvido (para a Fase 3)

- **Posição compartilhada**: um vetor `pos` em frações do volume `[x, y, z]`, aplicado a `scene.crosshairPos` de todas as instâncias. Cada vista mexe só no componente dela (axial→z, coronal→y, sagital→x).
- **Roda do mouse**: listener próprio na fase de captura com `stopImmediatePropagation`, porque o do Niivue move todas as vistas juntas. A vista sob o mouse vem de `screenSlices`.
- **Brilho e contraste**: viram `cal_min` e `cal_max` (`centro = 0,5 − brilho/100`, `largura = 1 / (contraste/100)`). A janela padrão é 0–1, pois os dados já estão em [0,1]. Se o lote real não estiver normalizado assim, esta conta precisa mudar.
- **Zoom do ampliado**: o Niivue dá zoom em torno da origem do mundo. Para centrar, o pan é `(1 − zoom) × centro do volume em mm` (`frac2mm([0.5,0.5,0.5])`). Testado nas 3 vistas. O arrasto converte pixels em mm por `fovMM × zoom / largura do canvas`, igual para qualquer zoom.
- **Estado do viewer** exposto em `window.__view` (corte e janela) para o `viewer_state` futuro.

## Limitações e riscos

1. **Contagem de corte na roda**: a posição é uma fração, então cinco giros podem andar só quatro cortes por arredondamento. Na Fase 3, guardar o índice inteiro do corte por vista e derivar a fração dele. Isso também deixa o `viewer_state` exato.
2. **6 contextos WebGL** abertos ao mesmo tempo. Navegadores costumam aceitar uns 16, então há folga, mas a página seguinte (pré-carga, T3.6) não deve criar novas instâncias; deve reaproveitar as 5 e trocar o volume.
3. **Letras de orientação** (A, S, L, P) aparecem nas imagens. Decisão do Rafael: manter.
4. **Teste só em um navegador** (painel do app, com escala de tela 125%). Falta conferir em Chrome, Firefox e Safari antes de enviar o link aos médicos.
5. **Ampliado carrega o volume de novo** pela URL (vem do cache do navegador). Aceitável no local; reavaliar na hospedagem.
6. **Não testado**: touchpad com rolagem fina (um evento de roda = um corte, pode ficar rápido demais) e telas pequenas ou toque.
7. Os testes foram feitos com eventos simulados de arrasto e roda além de cliques reais; o ajuste fino do arrasto com mouse físico fica para a revisão da Fase 3.

## Alternativas consideradas

Não foram testadas outras bibliotecas: o Niivue já cumpriu todos os critérios da Fase 0, e trocar custaria tempo sem ganho. Se aparecer um bloqueio sério nos itens 2 ou 4, a alternativa a avaliar é o Cornerstone3D.
