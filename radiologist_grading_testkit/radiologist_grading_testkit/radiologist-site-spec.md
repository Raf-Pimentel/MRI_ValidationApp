# Especificação de Projeto — Site de Avaliação de Reconstruções por Radiologistas

## Contexto

O benchmark treina autoencoders (`resblock`, MedNeXt, SegResNet, Swin) que
comprimem e reconstroem volumes de MRI cerebral. As métricas automáticas
(PSNR, SSIM, LPIPS) medem fidelidade pixel a pixel, mas não dizem se um
radiologista de fato acha a reconstrução convincente ou útil para
diagnóstico. Para isso, falta uma avaliação humana: radiologistas comparando
volumes reconstruídos com o volume real, sem saber qual é qual.

Já existe um lote de teste com 8 casos reais (BraTS/IXI), cada um com 5
volumes NIfTI — 1 real + 4 reconstruções, em posições embaralhadas — pronto
para servir de material de desenvolvimento e teste do site. Está na mesma
pasta desta especificação, em `testkit/`.

## Objetivo

Construir uma aplicação web que apresente esses casos a radiologistas
recrutados e colete, por caso:

1. um ranking dos 5 volumes, do mais realista ao menos realista;
2. uma nota de qualidade diagnóstica (escala tipo Likert) para cada volume
   individualmente.

As respostas são gravadas com identificação do radiologista, do caso e um
timestamp.

## Fluxo de uso

1. O radiologista se identifica (nome ou código — não precisa de
   autenticação robusta).
2. O site apresenta um caso por vez, com os 5 volumes daquele caso.
3. Para cada volume, o radiologista navega pelas fatias (no mínimo axial;
   coronal/sagital é um ganho) e ajusta a janela de contraste.
4. O radiologista ordena os 5 volumes por realismo e dá uma nota de 1 a 5
   para cada um.
5. Ao confirmar, o site grava as respostas e avança para o próximo caso.
6. O radiologista pode interromper e retomar depois, sem repetir casos já
   respondidos.

## Material de entrada (`testkit/`)

- `case_01/` .. `case_08/`, cada um com 5 arquivos `.nii.gz`
  (`vol_A` .. `vol_E`) e um `info.txt` com dataset + modalidade — iguais
  entre os 5 volumes do mesmo caso, então podem ser exibidos sem problema.
- `_answer_key_do_not_share_with_radiologists/answer_key.csv`: o gabarito
  com a fonte real de cada slot de cada caso. Serve só para conferir se o
  site está exibindo e gravando tudo corretamente durante o
  desenvolvimento — nunca deve ser lido pelo site em produção nem exibido
  em tela alguma.
- `README.md`, dentro do próprio `testkit/`, com os comandos para regenerar
  ou ampliar o lote de casos, se for preciso mais volume de teste.

## Requisitos funcionais

- **RF1.** Exibir os volumes de um caso em um visualizador de imagens
  médicas (NIfTI), com navegação por fatia e ajuste de janela/contraste —
  não uma imagem estática por volume.
- **RF2.** Usar a mesma fatia e a mesma janela de contraste, por padrão,
  para todos os volumes de um mesmo caso, para a comparação ser justa.
- **RF3.** Coletar um ranking completo e sem empates dos 5 volumes de cada
  caso.
- **RF4.** Coletar uma nota de 1 a 5 (ou escala equivalente) para cada
  volume do caso, incluindo o volume real, de forma independente do
  ranking.
- **RF5.** Gravar cada resposta com radiologista, caso, slot e timestamp.
- **RF6.** Permitir retomar uma sessão sem repetir casos já respondidos.
- **RF7.** Suportar múltiplos radiologistas avaliando o mesmo conjunto de
  casos, cada um com seu próprio histórico de respostas.
- **RF8.** Exportar os dados coletados em um formato legível depois em
  pandas/Excel (CSV ou dump de banco).

## Requisitos não funcionais

- **RNF1.** Nenhuma informação que revele a origem de um volume (nome de
  arquivo, arquitetura, ordem de upload) pode chegar ao radiologista — nem
  na interface, nem no código enviado ao navegador.
- **RNF2.** O gabarito (`answer_key.csv`) nunca é lido, exposto ou incluído
  no site em produção.
- **RNF3.** Corrigir uma resposta gera um novo registro; não sobrescreve o
  registro anterior.
- **RNF4.** O ambiente de hospedagem e quem tem acesso ao site devem estar
  documentados.

## Modelo de dados (sugestão)

| tabela | campos principais | para que serve |
|---|---|---|
| `radiologistas` | id, nome/código, criado_em | quem está avaliando |
| `casos` | id, dataset, modalidade, n_slots | espelha o `info.txt` de cada caso |
| `rankings` | id, radiologista_id, caso_id, slot, posicao, criado_em | um ranking respondido |
| `notas` | id, radiologista_id, caso_id, slot, nota, criado_em | uma nota respondida |
| `progresso` | radiologista_id, caso_id, concluido_em | controla o que já foi respondido |

## Entregáveis

- Site funcionando, com acesso disponível para os radiologistas recrutados.
- Esquema de dados documentado e exportação testada.
- Um teste ponta a ponta usando o `testkit/`: comparar o que o site
  registrou com o `answer_key.csv`, antes de usar com radiologistas reais.
- Uma nota curta descrevendo as escolhas técnicas feitas (stack,
  hospedagem, biblioteca de visualização de NIfTI).

## Fora de escopo

- Alterar o processo de geração dos casos (`reconstruct.py` e a montagem do
  `testkit/`).
- Qualquer nova métrica automática de qualidade de imagem — isso aqui é
  avaliação humana, complementar, não substitui as métricas já existentes.

## Decisões a cargo do desenvolvedor

- Stack de frontend/backend e hospedagem.
- Biblioteca de visualização de NIfTI (existem várias prontas para uso em
  navegador, ex. Niivue — não vale a pena construir um visualizador do
  zero).
- Texto exato e âncoras da escala de qualidade diagnóstica.
- Número de radiologistas por caso.
- Ordem de apresentação dos casos por radiologista (sugestão: randomizar,
  para não haver um efeito de cansaço/ordem sempre nos mesmos casos).
