# Lista de conferência do cegamento (T5.2)

Objetivo: provar que nada que o navegador recebe revela a origem de um volume (modelo ou "real").

Data da checagem automática: 2026-10-31. Ambiente: back e front locais, navegador do app, token de teste, `case_01` na página 1.

## Conferido (feito por script no navegador e por varredura do build)

| # | Item | Resultado |
|---|---|---|
| 1 | Aba de rede: URLs dos volumes são `/api/vol/<uuid>`, sem slot nem modelo | OK |
| 2 | Aba de rede: os 5 volumes de cada página têm exatamente o mesmo tamanho (6.211.744 bytes na página 1; 6.212.782 na página 2), tanto no tamanho transferido quanto no `Content-Length` | OK |
| 3 | JSON da página: só `position`, `total_pages`, `sequence`, `columns[{slot, url}]` e `ratings` | OK |
| 4 | Cabeçalhos HTTP dos volumes e do JSON: sem campo que cite modelo ou origem (`Last-Modified` e `ETag` não distinguem o original: a ordem de gravação dos arquivos segue a ordem dos slots A a E, que não tem relação com a origem) | OK |
| 5 | Header NIfTI dos volumes: `descrip`, `aux_file`, `intent_name` e extensões vazios | OK |
| 6 | HTML e DOM da página: nenhuma ocorrência de nome de modelo, "ground truth", "answer", "source" | OK |
| 7 | JS: build de produção do front sem `resblock`, `mednext`, `segresnet`, `swin`, `ground truth`, `answer_key` (a palavra "control" aparece 6 vezes, todas dentro do código do Niivue) | OK |
| 8 | `localStorage` e `sessionStorage` vazios (token só na URL) | OK |
| 9 | Rotas de documentação (`/docs`, `/openapi.json`) desligadas | OK (por construção, `create_app`) |
| 10 | Gabarito fora do servidor: `answer_key.csv` só é lido por `scripts/e2e_check.py` e pelos testes | OK |

## Conferência humana (assinada)

Abrir `http://localhost:5173/?t=<token>` no Chrome, com F12:

- [x] Aba **Network**: filtrar por `vol`, conferir que a coluna *Size* é igual nos 5 volumes de cada página.
- [x] Aba **Network**: abrir um volume em *Response* e ver que não há texto legível com nome de modelo.
- [x] Aba **Elements**: buscar (Ctrl+F) por `resblock`, `mednext`, `segresnet`, `swin`, `real`, `truth`. Só pode haver "real" na pergunta das instruções ("aspecto de imagem real").
- [x] Aba **Sources**: buscar o mesmo nos arquivos do site.
- [x] Passar o mouse nas colunas e na lupa: nenhum tooltip com origem.

Conferido por: Rafael (nomes opacos na aba Network e busca por nomes de modelo em Elements com 0 resultados)  Data: 2026-10-31

Confirmado depois, com *Disable cache* ligado: tamanhos iguais (`content-length` 6211744 no volume inspecionado), cabeçalhos sem origem, buscas em Sources com zero resultados e nenhuma dica ao passar o mouse (colunas, botões, lupa).

Nota: na primeira conferência do Rafael a coluna *Size* mostrou `(disk cache)`; os tamanhos iguais foram medidos pelo script (item 2) e o total carregado (62.205.695 B para 10 volumes) é coerente.

## Repetição após a repaginada visual (P12.5, 2026-10-31)

Feita por script no navegador (servidor de desenvolvimento, médico de teste, página 1) e por varredura do build de produção. A conferência humana (F12, Elements/Sources/tooltips) **não** foi repetida: fica para quando houver o endereço final (P10).

- Rede: URLs dos volumes são `/api/vol/<uuid>`; as outras chamadas são `/api/session/<token>` e `/api/session/<token>/page/<n>`.
- Os 5 volumes da página 1 têm exatamente o mesmo tamanho (6.551.776 bytes, lidos com `cache: no-store`).
- Cabeçalhos dos volumes: `accept-ranges`, `cache-control`, `connection`, `content-length`, `content-type`, `date`, `etag`, `last-modified`, `server`, `vary`; nenhum cita origem.
- DOM: nenhuma ocorrência de `resblock`, `mednext`, `segresnet`, `swin`, `ground truth`, `answer`, `source`, `truth`. A palavra "real" aparece 4 vezes, todas no texto das instruções. Nenhum atributo `title` (sem tooltips).
- Build (`frontend/dist`): 0 ocorrências de `resblock`, `mednext`, `segresnet`, `swin`, `ground truth`, `answer_key`.
- `localStorage` vazio; `sessionStorage` sem chaves do app.
