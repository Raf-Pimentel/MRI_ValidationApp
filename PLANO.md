# Plataforma de Avaliação Cega de MRI Sintéticas — Plano v0.3

Status: rascunho para iteração. Última atualização: 2026-10-31.

Documentos relacionados na mesma pasta: `radiologist_grading_testkit/.../radiologist-site-spec.md` (especificação do laboratório) e `testkit/` (8 casos reais de teste). Este plano é o que vale quando houver divergência com a especificação, e a seção 3 lista as diferenças.

## 1. Objetivo

Plataforma para que médicos especialistas avaliem a fidelidade de volumes de MRI 3D de cérebro, em condição cega. Cada página compara a imagem original (controle) com as reconstruções feitas por 4 arquiteturas de autoencoder, no pipeline do MAISI.

Origem das imagens de cada página:

1. Pega-se uma imagem do grupo controle (original).
2. Ela passa pelo autoencoder (encoder) e vai ao espaço latente.
3. O decoder gera a imagem sintética. Cada modelo repete o pipeline com a sua arquitetura.

Logo, as 5 colunas de uma página mostram **o mesmo paciente e a mesma sequência**. O médico **não** é informado de que uma das colunas é a imagem original.

## 2. Requisitos fechados

| Tema | Decisão |
|---|---|
| Dado | Volumes 3D em `.nii.gz`. Três vistas: axial, coronal, sagital. Os dados do testkit são float32 em [0,1], voxel de 1 mm, headers limpos. Dimensões **variam** entre casos (128 a 145 por eixo) e são iguais entre os 5 volumes do mesmo caso. A plataforma não pode assumir um tamanho fixo |
| Datasets e sequências | Datasets BraTS-GLI, BraTS-MET e IXI. Sequências T1, T1-Gd (`T1ce`), T2 e FLAIR |
| Caso (página) | Um caso é um par (paciente, sequência), com 5 volumes. A origem de cada volume é conhecida só pelo gabarito offline |
| Layout da página | **5 colunas** (volumes) × **3 linhas** (vistas) = 15 painéis |
| Colunas | O servidor só conhece o **slot** de cada volume (arquivo `vol_A` a `vol_E`). A que modelo cada slot corresponde fica fora do sistema, no gabarito. Para o médico, só "Imagem A–E" |
| Modelos (no gabarito) | ResNet (âncora/controle MAISI), MedNeXt, Swin, SegResNet e a imagem original |
| Cegamento | Ordem das colunas sorteada **por médico + página**. Ordem das páginas também sorteada por médico, na primeira entrada |
| Sequência por página | **Uma única sequência por página**, nunca mistura |
| Aleatorização das páginas | Médicos diferentes veem ordens diferentes (por exemplo, João: P13/T1, depois P2/FLAIR; Flávia: P30/T1-Gd, depois P4/T1-Gd), para eliminar viés de ordem |
| Scroll | O scroll move **uma vista por vez**: rolar sobre qualquer imagem axial move todas as axiais; coronal e sagital não se mexem. O mesmo para cada vista |
| Viewer ampliado | A lupa de cada imagem abre um viewer grande, quase tela cheia. Nele o scroll troca de corte normalmente. Ver seção 5 |
| Navegação sem mouse | Setas para cima/baixo em cada linha (vista) trocam o corte daquela vista nas 5 colunas |
| Brilho e contraste | **Global**: vale sempre para todas as imagens, com botão "Restaurar" |
| Registro do viewer | Cada nota grava o corte de cada vista e o brilho/contraste globais no momento da nota (`viewer_state_json`). O zoom **não** é gravado |
| Nota | **1 a 5 por coluna, medindo fidelidade**: o quão real parece a imagem, saudável ou não. O objetivo é medir a qualidade da síntese, não avaliar a doença. Comentário opcional por coluna |
| Ranking dos 5 volumes | Pedido pela especificação. **Fica para depois do MVP** (seção 8). O esquema do banco já comporta a extensão |
| Escala | ≥ 20 médicos, 50 páginas avaliadas por médico |
| Fluxo | Salvar progresso e retomar, voltar e alterar notas |
| Acesso | Link pessoal com token, sem senha. A primeira entrada gera e fixa a ordem sorteada daquele médico |
| Ética das imagens | Datasets públicos e abertos, sem restrição ética para exibir. Citar e respeitar a licença de cada um |
| Hospedagem | Primeiro rodar **100% local**. Depois, servidor do LIDS e compartilhamento com os médicos. Se for difícil, servidor externo |

### 2.1 Escopo do MVP

Para não complicar cedo, o MVP é o menor conjunto que já coleta dados válidos. Esta divisão é uma proposta, e você pode mover itens.

**No MVP:**
- Token por médico, ordem sorteada de páginas e colunas, salvar e retomar.
- Grade 3×5 com scroll por vista, setas por linha e viewer ampliado.
- Brilho e contraste globais.
- Nota 1–5 por coluna e comentário opcional.
- Tela simples de instruções (em português).
- Exportação CSV pelo admin, com `viewer_state`.
- Teste ponta a ponta com o testkit e o gabarito.

**Depois do MVP:**
- Ranking dos 5 volumes.
- Interface em inglês.
- Páginas de treino.
- Atalhos de teclado.
- Perfil do médico.
- Painel admin completo.
- Backup automático diário.
- Cronometragem por página.

## 3. Alinhamento com a especificação do laboratório

| Tema | Especificação | Este plano |
|---|---|---|
| Ranking dos 5 | Exige (RF3) | Depois do MVP |
| Nota | 1–5 de "qualidade diagnóstica" | 1–5 de **fidelidade** (o quão real parece). O texto da escala é decisão nossa, como a especificação permite |
| Origem do volume | O site nunca lê o gabarito e a origem não chega ao navegador (RNF1, RNF2) | Atendido: o banco guarda só o slot. A ligação slot → modelo é feita offline |
| Visualizador | NIfTI com fatias e janela. Axial no mínimo | Atendido e ampliado: 3 vistas, viewer ampliado |
| Mesma fatia e janela por caso | RF2 | Atendido pelo scroll por vista e pelo brilho/contraste globais |
| Identificação | Nome ou código, sem autenticação robusta | Link com token |
| Correções | Nova linha, sem sobrescrever (RNF3) | Atendido (append-only) |
| Retomar, vários médicos, exportação | RF6, RF7, RF8 | Atendido |
| Ordem dos casos | Sugere randomizar por radiologista | Atendido |
| Entregáveis | Teste ponta a ponta com o gabarito, nota técnica e documentação de hospedagem e acesso (RNF4) | Na seção 8 |

**Consequência de guardar só o slot.** O banco e a exportação não trazem o nome do modelo. Para analisar, junta-se a exportação com o `answer_key.csv` (por caso e slot), por exemplo no pandas. Isso protege o cegamento mesmo se o banco vazar. Em contrapartida, o gabarito vira um arquivo crítico: sem ele não dá para analisar por modelo. Guardar cópias dele fora do servidor e fora do repositório. Para o lote real, o script que monta os casos (a montagem do testkit) tem de gerar esse gabarito junto.

## 4. Pendências

Já resolvidas: dimensões e formato dos volumes (conferidos nos 40 arquivos do testkit), lista de sequências e modelos, mesmo caso nas colunas, o médico não sabe qual é o original, significado da nota, ranking adiado, gabarito fora do servidor.

Abertas:

1. **Texto e âncoras da escala 1–5.** Proposta para aprovar:
   - Pergunta: "Quão real parece esta imagem de ressonância? Considere anatomia, textura e contraste. Avalie o aspecto de imagem real, independentemente de haver ou não doença."
   - 1 = claramente artificial; 2 = provavelmente artificial; 3 = incerta; 4 = provavelmente real; 5 = indistinguível de uma ressonância real.
2. **Desenho amostral.** Quantos casos no total além dos 8 do testkit? Cada médico vê 50 deles? O mesmo paciente pode aparecer ao mesmo médico em sequências diferentes (risco de aprendizado entre páginas)? Quantos médicos por caso, no mínimo? Define o algoritmo de sorteio.
3. **Quem gera o lote real e em que formato.** Os casos reais devem seguir o formato do testkit (5 volumes por caso, `info.txt` com dataset e sequência, gabarito à parte). Quem roda a montagem e quando?
4. **Licenças e citações** de BraTS-GLI, BraTS-MET e IXI. Público não significa sem termos de uso. Registrar na tela de instruções ou no rodapé o que cada licença pedir.
5. **TCLE dos avaliadores** (baixa prioridade). Confirmar com o orientador se precisa de termo, já que registramos o estado do viewer.
6. **Hospedagem no LIDS.** Perguntar quando chegar a hora: Docker é permitido? Acesso externo, HTTPS ou VPN? Quanto disco?

## 5. Arquitetura proposta

```
Navegador (médico)                      Servidor
┌──────────────────────┐   HTTPS   ┌─────────────────────────────┐
│ Front (TypeScript)   │ ────────► │ FastAPI (Python)            │
│  - 5 instâncias      │           │  - /api/session (token)     │
│    Niivue (WebGL),   │ ◄──────── │  - /api/page/{n}            │
│    cada uma com 3    │  volumes  │  - /api/rating  (autosave)  │
│    vistas em coluna  │ (opacos)  │  - /api/vol/{opaque_id}     │
│  - scroll por vista  │           │  - /admin (CSV, progresso)  │
│  - viewer ampliado   │           │ SQLite → Postgres (se crescer)│
│  - Nota 1-5          │           │ Volumes preparados (disco)  │
└──────────────────────┘           └─────────────────────────────┘
                                   Fora do servidor: answer_key.csv
```

### 5.1 Escolhas e motivos

- **Viewer: [Niivue](https://github.com/niivue/niivue).** Biblioteca WebGL para NIfTI, com vista multiplanar (axial/coronal/sagital) e sincronização entre instâncias. Aceita volumes de qualquer tamanho e respeita o espaçamento de voxel do header. Alternativa: Cornerstone3D, mais pesada e voltada a DICOM. A especificação também sugere o Niivue.
- **Front: Vite + TypeScript, sem framework pesado.** A tela é uma grade com estado simples.
- **Backend: FastAPI + SQLModel.** O mesmo ambiente Python roda os scripts de preparação dos dados.
- **Banco: SQLite** (20 médicos, ~5000 notas). Um arquivo só, backup trivial. Postgres só se escalar.
- **Deploy:** Docker Compose (app + Caddy para HTTPS automático), mas só na hospedagem. O Docker não está instalado nesta máquina, e o desenvolvimento local roda direto com Node e Python.

### 5.2 Pontos técnicos críticos

1. **Cegamento real, não só visual.**
   - Volumes servidos por IDs opacos (UUID por asset). A URL e o nome do arquivo nunca contêm o slot nem o modelo.
   - O servidor nunca lê o gabarito. O sorteio `posição na tela → slot` é feito por médico e por página.
   - **O tamanho do arquivo denuncia o original.** No testkit, o volume real pesa 2,6 a 5,3 MB e as reconstruções 5,4 a 8,7 MB, e isso aparece na aba de rede do navegador. O script de preparação reempacota os 5 volumes de um caso com o mesmo formato (inteiro de 16 bits, sem compressão), de modo que todos têm exatamente o mesmo tamanho em bytes. O servidor entrega esses arquivos sem compressão HTTP.
   - Limpar headers NIfTI e usar o mesmo formato de armazenamento. Os dados do testkit já vêm em [0,1], então a janela padrão é fixa em 0–1.
2. **Scroll independente por vista, com 5 instâncias Niivue.**
   - Cada coluna é uma instância Niivue em layout multiplanar (3 vistas empilhadas). Isso usa 5 contextos WebGL, não 15.
   - Um handler de scroll próprio muda só o eixo da vista sob o mouse e aplica a posição, em fração do volume, às 5 instâncias. As outras duas vistas não se movem.
   - O clique para mover o crosshair fica desativado, para o médico não bagunçar as outras vistas.
3. **Dimensões variáveis.** O viewer lê o shape e o espaçamento de cada volume. O script de preparação gera um manifesto por caso e verifica que os 5 volumes têm o mesmo shape e orientação.
4. **Desempenho.** Cada caso tem 5 volumes de ~3 milhões de voxels. Em 16 bits sem compressão, cerca de 6 a 7 MB cada, e ~30 a 35 MB por página. Mitigação: pré-carregar a próxima página em segundo plano e reaproveitar na memória os volumes no viewer ampliado. Se a banda do LIDS for um problema, revisar a compressão mantendo o tamanho uniforme.
5. **Salvar e retomar.** Cada nota vai ao servidor no ato (autosave). Reabrir o link leva à primeira página sem nota. As notas são **registros append-only**, e a nota vigente é a mais recente.
6. **Aleatorização reprodutível.** A semente é guardada por médico, e a análise pode reconstruir a ordem das páginas e das colunas.

### 5.3 Armazenamento das notas: banco de dados, não .json

**Decisão: SQLite (modo WAL) como fonte de verdade. JSON e CSV só como formatos de exportação.**

Por que não um .json como armazenamento principal:

- 20 médicos salvando ao mesmo tempo. Um arquivo JSON precisa ser reescrito inteiro a cada nota, então duas gravações simultâneas podem se sobrescrever ou corromper o arquivo.
- Sem transações, uma queda no meio da gravação deixa o arquivo quebrado.
- Sem restrições (nota entre 1 e 5) nem consultas de progresso sem carregar tudo.

Robustez:

- Gravação **append-only**: cada alteração de nota vira uma nova linha.
- Gravação **idempotente**: o front envia um `client_event_id`, então reenvio por queda de rede não duplica.
- `CHECK (score BETWEEN 1 AND 5)` e chaves estrangeiras ligadas.
- Coluna `schema_version` para migrações.

Tabelas (resumo). Nenhuma delas guarda a origem do volume:

- `case(id, dataset, modality)`: espelha o `info.txt`
- `volume(id, case_id, slot, opaque_id, path, shape, spacing)`
- `rater(id, token, name?, email?, seed, created_at, finished_at)`
- `assignment(rater_id, position, case_id, column_order[])`: ordem das páginas e a ordem dos slots na tela
- `rating_event(id, client_event_id, rater_id, case_id, slot, score 1-5, comment, viewer_state_json, created_at)`: append-only

`viewer_state_json` guarda, no momento da nota, o corte de cada vista e o brilho/contraste globais (o zoom não é gravado).

Depois do MVP, o ranking entra como uma tabela nova `ranking_event(rater_id, case_id, slot, position, created_at)`, também append-only, sem mexer no que já existe.

Exemplo de exportação (uma linha por nota, formato longo):

```json
{"rater":"r07","case":"case_12","dataset":"BraTS-MET","modality":"T1ce","slot":"C","screen_column":3,"score":4,
 "comment":"leve borramento no cerebelo",
 "viewer":{"slice":{"axial":58,"coronal":71,"sagittal":66},"brightness":100,"contrast":120},
 "created_at":"2026-10-14T13:02:11Z"}
```

Na análise, junta-se por `(case, slot)` com o gabarito para obter o modelo.

## 6. Telas

1. **Entrada via link:** valida token e, na primeira entrada, gera a ordem sorteada.
2. **Instruções:** a pergunta e a escala 1–5 (pendência 1), o scroll por vista, o viewer ampliado e a atribuição dos datasets.
3. **Página de avaliação** (mockup v3 validado visualmente):
   - Cabeçalho com a sequência da página, progresso (n/50) e contador de notas (n de 5).
   - Barra com brilho e contraste (globais) e "Restaurar".
   - Grade 3×5: cabeçalho "Imagem A–E", três linhas de imagens (axial, coronal, sagital) e, abaixo, nota 1–5 por coluna. O comentário é um botão que abre um campo.
   - Coluna lateral por linha com as setas para cima/baixo e o nome da vista. Elas movem só aquela vista.
   - Scroll do mouse sobre uma imagem move só a vista dela.
   - Lupa no canto superior direito de cada imagem: abre o viewer ampliado.
   - Botões Anterior/Próxima.
4. **Viewer ampliado** (aberto pela lupa):
   - Mostra a imagem selecionada (coluna e vista) em tamanho quase tela cheia.
   - O scroll troca o corte, e a vista correspondente da grade acompanha.
   - Zoom contínuo (slider) e arrastar para mover. O zoom não é gravado.
   - Setas para trocar de corte e alternar entre as colunas mantendo a mesma vista, para comparar no tamanho grande.
   - Brilho, contraste e a nota da coluna, sem precisar fechar.
   - `Esc` ou "Voltar à grade" fecha.
   - Implementação: uma instância Niivue de vista única reaproveitando o volume já carregado.
5. **Final:** agradecimento. Antes de finalizar, avisa se alguma coluna ficou sem nota.
6. **Admin** (protegido): MVP com exportação CSV. Depois, progresso por médico e geração de links.

## 7. Estrutura do repositório

```
MRI_ValidationApp/
  PLANO.md
  backend/      FastAPI, banco, sorteio
  frontend/     Vite + TypeScript + Niivue
  scripts/      preparação dos volumes (reempacotamento, manifesto)
  data/         volumes preparados (fora do git)
  docs/         nota técnica, hospedagem e acesso
  radiologist_grading_testkit/   material de teste do laboratório
```

Regras:
- `git init` com `.gitignore` para `data/`, para os volumes brutos, para o `.tar.gz` e para o gabarito.
- O `answer_key.csv` nunca fica em uma pasta que o servidor serve ou monta, nem entra em imagem Docker.
- O `.tar.gz` do testkit (255 MB) é uma duplicata da pasta extraída, que por sua vez tem uma pasta aninhada repetida. Pode manter um só e remover o outro quando você preferir.

## 8. Fases

| Fase | Entrega |
|---|---|
| 0. Spike (1–2 dias) | Com o `case_01` do testkit: 5 instâncias Niivue, 3 vistas em coluna, scroll independente por vista e viewer ampliado |
| 1. Preparação dos dados | Script Python que verifica compatibilidade dos 5 volumes, limpa headers, reempacota com tamanho uniforme, gera IDs opacos e manifesto. Nunca lê o gabarito |
| 2. Backend | Tokens, sorteio, endpoints de página/nota/volume, banco |
| 3. Front | Grade 3×5, viewer ampliado, avaliação e instruções |
| 4. Exportação | CSV do admin |
| 5. Teste ponta a ponta | Responder os 8 casos do testkit, exportar e conferir com o `answer_key.csv` |
| **MVP pronto** | Fases 0 a 5 concluídas, mais a nota técnica e a documentação de hospedagem e acesso |
| 6. Piloto | 2–3 pessoas, ajustes de usabilidade e desempenho |
| 7. Pós-MVP | Ranking dos 5 volumes, inglês, treino, atalhos, perfil, painel admin completo e backup automático |
| 8. Coleta | Convite aos ≥ 20 médicos |

## 9. Riscos

- O scroll por vista independente com 5 instâncias Niivue exige um handler próprio e desativar o clique do crosshair. É a primeira coisa a validar na Fase 0.
- Vazamento da origem por artefatos de preparação (tamanho de arquivo, header, formato). O tamanho já foi observado no testkit e tem mitigação (seção 5.2). Vale uma checagem automática no script de preparação.
- O original pode ser identificável por ser mais nítido ou mais "blocado" que as reconstruções. É parte do que o estudo mede, mas afeta a leitura das notas.
- Médicos com internet lenta: ~30 a 35 MB por página sem compressão. Mitigar com prefetch.
- Fadiga com 50 páginas × 5 notas. Considerar o tempo médio no piloto.
- Brilho/contraste mudam o que cada médico vê. Por isso o estado do viewer é gravado com cada nota, e o ajuste é igual em todas as imagens.
- Em tela de notebook, 15 painéis ficam pequenos. Mitigação: viewer ampliado, comentário recolhido, layout em tela cheia. Validar no piloto.
- Perda do `answer_key.csv` impede a análise por modelo. Guardar cópias fora do servidor e do repositório.
