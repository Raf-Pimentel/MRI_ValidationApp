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

## Falta a olhada humana (o roteiro pede assinatura)

Abrir `http://localhost:5173/?t=<token>` no Chrome, com F12:

- [ ] Aba **Network**: filtrar por `vol`, conferir que a coluna *Size* é igual nos 5 volumes de cada página.
- [ ] Aba **Network**: abrir um volume em *Response* e ver que não há texto legível com nome de modelo.
- [ ] Aba **Elements**: buscar (Ctrl+F) por `resblock`, `mednext`, `segresnet`, `swin`, `real`, `truth`. Só pode haver "real" na pergunta das instruções ("aspecto de imagem real").
- [ ] Aba **Sources**: buscar o mesmo nos arquivos do site.
- [ ] Passar o mouse nas colunas e na lupa: nenhum tooltip com origem.

Conferido por: ______________________  Data: ____/____/______
