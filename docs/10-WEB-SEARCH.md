# 10 - Integracao de Busca Web (Tavily + DuckDuckGo)

## Objetivo

Adicionar uma camada de busca web que executa **antes** de chamar o DeepSeek,
resolvendo o problema de o modelo nao ter acesso nativo a internet.
Os resultados da busca sao enviados como contexto no prompt do usuario,
permitindo que o DeepSeek trabalhe com dados atualizados.

## Decisoes de Design

| Decisao | Escolha |
|---|---|
| API primaria | Tavily Search API (tavily-python) |
| API secundaria (fallback) | DuckDuckGo (duckduckgo-search, gratuita, sem API key) |
| Ativacao | Por prompt — campo `enable_search` (boolean) |
| Resultados por busca | Configuravel por prompt — campo `search_max_results` (default: 5) |
| Formato do contexto | Prefixado no `user_prompt` antes de enviar ao DeepSeek |
| Instrucao `enable_search` existente | Mantida no system prompt (DeepSeek pode complementar com busca propria) |
| Fallback se ambas APIs falharem | Chama DeepSeek sem contexto de busca (nao interrompe execucao) |

## Arquitetura — Fluxo Modificado

```
Cron / Manual → executor.run_schedule(schedule_id)
  → Busca schedule no SQLite → Busca prompt vinculado
  → Se prompt.enable_search == True:
      → search_client.web_search(prompt.title, max_results)
        → Tenta Tavily → falha? → Tenta DuckDuckGo
        → Formata resultados como [DADOS DE PESQUISA RECENTE]
      → Enriquecer user_prompt com resultados prefixados
  → Se prompt.enable_search == False OU busca retornou vazio:
      → user_prompt original (sem contexto extra)
  → call_deepseek(user_prompt_enriquecido, tone, enable_search=True)
  → Email com resultado
```

## Novos Arquivos

### `app/search_client.py`

Modulo responsavel pela busca web com fallback em cadeia.

```python
# Funcao principal
def web_search(query, max_results=5):
    """
    Realiza busca web usando Tavily como primaria e DuckDuckGo como fallback.
    Retorna string formatada com os resultados ou string vazia se ambas falharem.
    """
```

**Estrategia de fallback:**
1. Tentar Tavily (requer `TAVILY_API_KEY` no .env)
2. Se falhar (timeout, erro de rede, API key ausente), tentar DuckDuckGo
3. Se DuckDuckGo tambem falhar, logar warning e retornar string vazia
4. O executor trata string vazia como "sem resultados" e prossegue normalmente

**Formato dos resultados** (prefixado ao user_prompt):

```
[DADOS DE PESQUISA RECENTE]
As informacoes a seguir foram obtidas da web e devem ser usadas como base
para sua resposta. Priorize dados factuais destas fontes:

1. Titulo: {title}
   Fonte: {url}
   Conteudo: {content}

2. Titulo: {title}
   Fonte: {url}
   Conteudo: {content}

[FIM DOS DADOS DE PESQUISA]
```

**Tavily:**
- Biblioteca: `tavily-python`
- Metodo: `TavilyClient.search(query, max_results=N, search_depth="advanced")`
- Resultado: dicionario com lista `results` contendo `{title, url, content, score}`

**DuckDuckGo (fallback):**
- Biblioteca: `duckduckgo-search`
- Metodo: `DDGS().text(query, max_results=N)`
- Resultado: lista de `{title, href, body}`
- Sem necessidade de API key, sem limites de cota

## Arquivos Modificados

### `requirements.txt` — Novas dependencias

```
tavily-python>=0.5.0
duckduckgo-search>=7.0.0
```

### `.env` / `.env.example` — Novas variaveis

```
# Web Search (Tavily - primaria)
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SEARCH_MAX_RESULTS_DEFAULT=5
```

- `TAVILY_API_KEY`: obrigatoria apenas se `enable_search=True` em algum prompt (log warning se ausente)
- `SEARCH_MAX_RESULTS_DEFAULT`: valor default global, sobrescrito pelo campo `search_max_results` do prompt

### `app/models.py` — Migracao de schema

**Novas colunas na tabela `prompts`:**

| Coluna | Tipo | Default | Descricao |
|---|---|---|---|
| `enable_search` | BOOLEAN | 1 | Ativa busca web antes do DeepSeek |
| `search_max_results` | INTEGER | 5 | Quantidade de resultados por busca |

**Migracao (ALTER TABLE try/except, mesmo padrao existente):**
```python
try:
    conn.execute("ALTER TABLE prompts ADD COLUMN enable_search BOOLEAN DEFAULT 1")
except sqlite3.OperationalError:
    pass
try:
    conn.execute("ALTER TABLE prompts ADD COLUMN search_max_results INTEGER DEFAULT 5")
except sqlite3.OperationalError:
    pass
```

**Metodos `Prompt` modificados:**
- `Prompt.create()` — adicionar parametros `enable_search=1, search_max_results=5`
- `Prompt.update()` — adicionar parametros `enable_search, search_max_results`

**Metodo `Schedule.get_by_id()` — Query JOIN ampliada:**
- Adicionar `p.enable_search, p.search_max_results` na query para expor ao executor

### `app/executor.py` — Logica de busca pre-DeepSeek

**Fluxo no `run_schedule()` (branch AI, ~linha 136):**

```python
# Antes de chamar call_deepseek:
if schedule_id:
    enable_search = schedule.get("enable_search", 1)
    search_max = schedule.get("search_max_results", 5) or 5
else:
    # Execucao manual sem schedule — busca o prompt
    prompt_row = Prompt.get_by_id(prompt_id_override)
    enable_search = prompt_row["enable_search"] if prompt_row else 1
    search_max = prompt_row.get("search_max_results", 5) or 5

user_prompt = f"Topico: {prompt_content}\n\nGere o infografico/relatorio..."

if enable_search:
    from app.search_client import web_search
    search_query = prompt_title if schedule_id and prompt_title else prompt_content
    search_results = web_search(search_query, max_results=search_max)
    if search_results:
        user_prompt = search_results + "\n\n" + user_prompt
        logger.info("Busca web adicionou %d chars de contexto", len(search_results))
    else:
        logger.warning("Busca web nao retornou resultados, seguindo sem contexto extra")

result_html, error = call_deepseek(user_prompt, tone=prompt_tone, enable_search=True)
```

### `app/deepseek_client.py` — Assinatura mantida

A funcao `call_deepseek()` mantem a mesma assinatura: `(prompt_content, tone, enable_search)`.
A diferenca e que o `prompt_content` agora chega **ja enriquecido** com os resultados de busca
prefixados (quando disponiveis). O `enable_search=True` continua adicionando a instrucao
`SEARCH_INSTRUCTION` ao system prompt — isso permite que o DeepSeek complemente com busca
propria se necessario.

**Ajuste no log** (linha 79): `prompt_len` agora reflete o tamanho do prompt ja enriquecido.

### `app/routes.py` — Rotas de prompt com novos campos

**`prompts_create()` (POST):**
```python
enable_search = 1 if request.form.get("enable_search") == "1" else 0
search_max_results = int(request.form.get("search_max_results", "5"))
Prompt.create(title, content, tone, fmt, active=1,
              enable_search=enable_search, search_max_results=search_max_results)
```

**`prompts_edit()` (POST):**
```python
enable_search = 1 if request.form.get("enable_search") == "1" else 0
search_max_results = int(request.form.get("search_max_results", "5"))
Prompt.update(prompt_id, title, content, tone, fmt, active,
              enable_search=enable_search, search_max_results=search_max_results)
```

**`prompts_run()` (execucao manual):**
- Passar `prompt_id_override` e `schedule_id=None` para o executor
- O executor agora busca os campos `enable_search` e `search_max_results` do prompt

### Templates

**`prompts/create.html` — Novos campos no formulario:**

Adicionar apos o campo "Formato de Saida":

```html
<div class="form-group">
    <label>
        <input type="checkbox" name="enable_search" value="1" checked>
        Ativar busca web antes do DeepSeek
    </label>
    <small style="color:var(--muted);">Busca noticias atualizadas e envia como contexto</small>
</div>
<div class="form-group">
    <label>Resultados da busca</label>
    <input type="number" name="search_max_results" value="5" min="1" max="20"
           style="width:80px;">
    <small style="color:var(--muted);">Quantidade de resultados (1-20)</small>
</div>
```

**`prompts/edit.html` — Novos campos no formulario:**

Adicionar apos o campo "Ativo":

```html
<div class="form-group">
    <label>
        <input type="checkbox" name="enable_search" value="1"
               {% if prompt.enable_search %}checked{% endif %}>
        Ativar busca web antes do DeepSeek
    </label>
    <small style="color:var(--muted);">Busca noticias atualizadas e envia como contexto</small>
</div>
<div class="form-group">
    <label>Resultados da busca</label>
    <input type="number" name="search_max_results"
           value="{{ prompt.search_max_results or 5 }}" min="1" max="20"
           style="width:80px;">
    <small style="color:var(--muted);">Quantidade de resultados (1-20)</small>
</div>
```

**`prompts/list.html` — Indicador visual de busca:**

Adicionar coluna "Busca" na tabela:

```html
<th>Busca</th>
...
<td data-label="Busca">
    <span class="badge badge-{{ 'success' if prompt.enable_search else 'muted' }}">
        {{ 'On' if prompt.enable_search else 'Off' }}
    </span>
</td>
```

### `Dockerfile` — Sem alteracoes

As bibliotecas `tavily-python` e `duckduckgo-search` serao instaladas via `requirements.txt`
durante o build da imagem, sem necessidade de pacotes de sistema adicionais.

### Scripts — Sem alteracoes

`run_executor.sh`, `run_cron.sh` e `entrypoint-cron.sh` nao precisam de ajustes —
a busca web e executada dentro do mesmo processo Python do executor.

## Testes

### Novo arquivo: `tests/test_search.py`

| Teste | Descricao |
|---|---|
| `test_tavily_success` | Tavily retorna resultados → string formatada valida |
| `test_tavily_fail_fallback_ddg` | Tavily falha → DuckDuckGo assume → resultados do DDG retornados |
| `test_both_fail_return_empty` | Ambas APIs falham → retorna string vazia |
| `test_tavily_no_api_key` | TAVILY_API_KEY ausente → pula direto para DuckDuckGo |
| `test_empty_query` | Query vazia → retorna string vazia, sem chamar APIs |
| `test_format_output` | Verifica formato `[DADOS DE PESQUISA RECENTE]` no output |
| `test_max_results_respected` | Verifica que `max_results` e respeitado no output |
| `test_integration_executor_with_search` | Fluxo completo: busca → DeepSeek com contexto enriquecido |
| `test_integration_executor_search_disabled` | Fluxo sem busca: prompt original sem contexto extra |

Todos os testes de API externa usam `unittest.mock.patch` (mesmo padrao de `test_deepseek.py`).

### Atualizar: `tests/test_deepseek.py`

Adicionar teste que verifica que o `call_deepseek` recebe prompt ja enriquecido corretamente.

### Atualizar: `tests/test_routes.py`

Adicionar testes para os novos campos nos formularios de create/edit de prompt.

## Ordem de Implementacao

1. **`requirements.txt`** — Adicionar `tavily-python` e `duckduckgo-search`
2. **`.env.example`** — Adicionar `TAVILY_API_KEY` e `SEARCH_MAX_RESULTS_DEFAULT`
3. **`app/models.py`** — Migracao ALTER TABLE + novos campos no `Prompt.create/update` + JOIN no `Schedule.get_by_id`
4. **`app/search_client.py`** — Novo arquivo com funcao `web_search()` e fallback
5. **`app/deepseek_client.py`** — Ajustar log e documentar que prompt_content pode vir enriquecido
6. **`app/executor.py`** — Adicionar logica de busca antes de `call_deepseek()` no branch AI
7. **`app/routes.py`** — Adicionar novos campos nas rotas `prompts_create` e `prompts_edit`
8. **Templates** — `create.html`, `edit.html`, `list.html`
9. **`tests/test_search.py`** — Novo arquivo de testes
10. **`tests/test_deepseek.py`, `tests/test_routes.py`** — Atualizar testes existentes
11. **Rodar testes** — `./run_tests.sh` para validar tudo
12. **`docker-compose build && docker-compose up -d`** — Testar em Docker

## Observacoes

- **Custo Tavily**: Tier gratuito = 1000 buscas/mes. Suficiente para uso pessoal com poucos prompts.
- **DuckDuckGo**: Sem limite de cota, mas pode ser instavel (bloqueios por User-Agent).
  Usar apenas como fallback.
- **Tokens extras**: Cada resultado de busca adiciona ~200-500 tokens ao prompt.
  Com 5 resultados, sao ~1000-2500 tokens extras por chamada (custo adicional ~$0.0007 no DeepSeek).
- **Timeout de busca**: 15s para Tavily, 10s para DuckDuckGo. Se ambas excederem,
  o executor prossegue sem contexto de busca (nao bloqueia a execucao).
- **Logs**: Cada etapa da busca (Tavily OK, Tavily fail, DDG OK, DDG fail) gera log com nivel apropriado
  para facilitar diagnostico.
