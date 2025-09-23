# Guia R�pido: VS Code

## Abrir o projeto
1. Abra o VS Code.
2. `File > Open Folder` e selecione `tech_challenge2`.

## Terminal integrado
- `Ctrl + `` abre o terminal dentro do VS Code.
- Use `python -m venv .venv` para criar ambiente virtual e `.\.venv\Scripts\activate` para ativar (Windows).

## Extens�es �teis
- **Python** (Microsoft): lint, debug e Jupyter.
- **GitLens**: visualiza��o de hist�rico.
- **AWS Toolkit** (opcional): interagir com S3/Lambda/Glue.

## Rodando scripts
- No terminal integrado: `python src/ingestion/fetch_b3_data.py --tickers PETR4.SA VALE3.SA --local-output data/raw`.
- Para refino: `python src/glue/refine_data.py --input data/raw --output data/refined`.
- Resultado aparecer� em `data/refined/dt=.../ticker=.../`.

## Debug r�pido
1. Abra o arquivo Python.
2. Coloque breakpoints (clique no gutter esquerdo).
3. Pressione `F5`, escolha `Python` e selecione o script a depurar.

## Atalhos importantes
- `Ctrl+P`: localizar arquivo.
- `Ctrl+Shift+F`: busca global.
- `Ctrl+/`: comentar linhas selecionadas.
- `Alt+Shift+F`: formatar arquivo (requer formatter configurado, ex. `black`).

Mais recursos: [VS Code Python docs](https://code.visualstudio.com/docs/python/python-tutorial).
