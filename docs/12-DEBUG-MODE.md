# 12 - Modo Debug por Prompt

## Objetivo

Permitir ativar o modo debug individualmente por prompt. Quando ativado, alem do conteudo
solicitado, o email inclui a trilha completa da execucao: system prompt, user prompt
(incluindo resultados de busca se houver), modelo, tom, duracao e timestamp.

## Decisoes de Design

| Decisao | Escolha |
|---|---|
| Ativacao | Por prompt — campo `debug_mode` (boolean, default 0) |
| Conteudo do debug | System prompt + user prompt + metadata (modelo, tom, busca, duracao, timestamp) |
| Formato no email | Secao HTML apos o conteudo gerado, com separador visual e estilo monospace |
| Onde monta o debug | No `executor.py`, antes de enviar o email |
| Impacto no `call_deepseek` | Nenhum — o executor reconstroi o system prompt importando constantes |
| Cores da secao debug | Tons verdes/ciano sobre fundo escuro (estilo terminal) |

## Formato da Secao Debug no Email

```html
<hr style="border:1px solid #ff00ff; margin:30px 0 20px 0;">

<div style="background:#0a0a0a; border:1px solid #333; border-radius:4px; padding:18px; font-family:'Courier New',monospace; font-size:12px; color:#00ff88; line-height:1.6;">
<h3 style="color:#ff00ff; margin:0 0 12px 0; font-size:15px;">&#128187; DEBUG - Trilha do Prompt</h3>

<p><strong>Modelo:</strong> deepseek-chat</p>
<p><strong>Tom/Estilo:</strong> newsletter</p>
<p><strong>Busca Web:</strong> Ativada (Tavily, 5 resultados)</p>
<p><strong>Modo Debug:</strong> Ativado</p>
<p><strong>Duracao:</strong> 2340ms</p>
<p><strong>Timestamp:</strong> 06/08/2026 14:30:00</p>

<h4 style="color:#ff00ff; margin:16px 0 6px 0;">System Prompt ({{ chars }} caracteres):</h4>
<pre style="background:#111; color:#0f0; padding:12px; border-radius:3px; overflow-x:auto; white-space:pre-wrap; font-size:11px; max-height:400px; overflow-y:auto;">{{ system_prompt }}</pre>

<h4 style="color:#ff00ff; margin:16px 0 6px 0;">User Prompt ({{ chars }} caracteres):</h4>
<pre style="background:#111; color:#0f0; padding:12px; border-radius:3px; overflow-x:auto; white-space:pre-wrap; font-size:11px; max-height:400px; overflow-y:auto;">{{ user_prompt }}</pre>
</div>
```

## Arquitetura — Fluxo Modificado

```
executor.run_schedule(schedule_id)
  → busca prompt.debug_mode
  → monta user_prompt (com ou sem resultados de busca)
  → salva copia do user_prompt para debug
  → reconstroi system_prompt importando constantes do deepseek_client
  → call_deepseek(user_prompt, tone, enable_search=True)
  → se debug_mode:
      → gera HTML da secao debug com system_prompt + user_prompt + metadata
      → result_html = result_html + debug_section
  → send_email(email_to, subject, result_html + debug)
```

## Arquivos Modificados

### `app/models.py`

**Nova coluna na tabela `prompts`:**

```sql
ALTER TABLE prompts ADD COLUMN debug_mode BOOLEAN DEFAULT 0;
```

**CREATE TABLE atualizado** (incluir `debug_mode BOOLEAN DEFAULT 0`).

**`Prompt.create()`** — adicionar parametro `debug_mode=0`.

**`Prompt.update()`** — adicionar parametro `debug_mode=None` (COALESCE no SQL).

**`Schedule.get_by_id()`** — adicionar `p.debug_mode` na query JOIN.

**`Schedule.get_active_schedules()`** — adicionar `p.debug_mode` na query JOIN.

### `app/executor.py`

**Nova funcao auxiliar `_build_debug_section()`:**

```python
def _build_debug_section(system_prompt, user_prompt, model, tone,
                          enable_search, search_results_count, duration_ms):
    ...
    return html_string
```

**Modificacao no `run_schedule()` — branch AI:**

Apos `result_html, error = call_deepseek(...)` e antes de `send_email(...)`:

```python
debug_mode = False
if schedule_id and schedule:
    debug_mode = bool(schedule.get("debug_mode", 0))
elif prompt_id_override and prompt_row:
    debug_mode = bool(prompt_row.get("debug_mode", 0))

if debug_mode and result_html:
    from app.deepseek_client import SYSTEM_PROMPT_BASE, TONE_INSTRUCTIONS, SEARCH_INSTRUCTION, _get_model

    tone_instruction = TONE_INSTRUCTIONS.get(prompt_tone, TONE_INSTRUCTIONS["infografico"])
    full_system_prompt = SYSTEM_PROMPT_BASE + "\n\nEstilo solicitado: " + tone_instruction
    if enable_search:
        full_system_prompt += "\n\n" + SEARCH_INSTRUCTION

    search_info = f"{'Tavily' if enable_search else 'Desativada'}"
    if enable_search:
        search_info += f", {search_max_results} resultados"

    debug_html = _build_debug_section(
        system_prompt=full_system_prompt,
        user_prompt=user_prompt_raw,
        model=_get_model(),
        tone=prompt_tone,
        search_info=search_info,
        duration_ms=duration,
    )
    result_html += debug_html
    logger.info("Modo debug: adicionada secao de %d chars ao email", len(debug_html))
```

Nota: `user_prompt_raw` e a variavel `user_prompt` construida antes da chamada ao DeepSeek (ja incluindo resultados de busca se houver). Precisamos salvar uma referencia a ela antes de chama-la.

### `app/routes.py`

**`prompts_create()` (POST):**
```python
debug_mode = 1 if request.form.get("debug_mode") == "1" else 0
Prompt.create(..., debug_mode=debug_mode)
```

**`prompts_edit()` (POST):**
```python
debug_mode = 1 if request.form.get("debug_mode") == "1" else 0
Prompt.update(..., debug_mode=debug_mode)
```

### Templates

**`prompts/create.html`** — apos o campo `search_max_results`:
```html
<div class="form-group">
    <label>
        <input type="checkbox" name="debug_mode" value="1">
        Ativar modo debug
    </label>
    <small style="color:var(--muted);display:block;margin-left:24px;">
        Inclui a trilha completa do prompt no email (system + user prompt)
    </small>
</div>
```

**`prompts/edit.html`** — apos o campo `search_max_results`:
```html
<div class="form-group">
    <label>
        <input type="checkbox" name="debug_mode" value="1"
               {% if prompt.debug_mode %}checked{% endif %}>
        Ativar modo debug
    </label>
    <small style="color:var(--muted);display:block;margin-left:24px;">
        Inclui a trilha completa do prompt no email (system + user prompt)
    </small>
</div>
```

**`prompts/list.html`** — adicionar coluna "Debug" na tabela:
```html
<th>Debug</th>
...
<td data-label="Debug">
    <span class="badge badge-{{ 'success' if prompt.debug_mode else 'muted' }}">
        {{ 'On' if prompt.debug_mode else 'Off' }}
    </span>
</td>
```

### `tests/test_models.py`

Adicionar `debug_mode BOOLEAN DEFAULT 0` na definicao `CREATE TABLE IF NOT EXISTS prompts` do `setUp`.

## Formato da Secao Debug — Exemplo Visual

```
┌──────────────────────────────────────────────┐
│  (conteudo gerado pelo DeepSeek)             │
│  ...infografico HTML normal...               │
│                                              │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│                                              │
│  🖥 DEBUG - Trilha do Prompt                 │
│                                              │
│  Modelo: deepseek-chat                       │
│  Tom/Estilo: newsletter                      │
│  Busca Web: Tavily, 5 resultados             │
│  Modo Debug: Ativado                        │
│  Duracao: 2340ms                             │
│  Timestamp: 06/08/2026 14:30:00             │
│                                              │
│  System Prompt (1234 caracteres):            │
│  ┌──────────────────────────────────────┐    │
│  │ Voce e um assistente que gera        │    │
│  │ infograficos e resumos em HTML...    │    │
│  │ ...                                  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  User Prompt (567 caracteres):               │
│  ┌──────────────────────────────────────┐    │
│  │ [DADOS DE PESQUISA RECENTE]          │    │
│  │ 1. Titulo: Noticia X                 │    │
│  │ ...                                  │    │
│  │ Topico: Me envie as principais...    │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

## Testes

### Atualizar: `tests/test_models.py`

Adicionar coluna `debug_mode` na tabela de teste (ja coberto pelos testes existentes de CRUD).

### Atualizar: `tests/test_routes.py`

Verificar que o campo `debug_mode` aparece nas paginas de create/edit.

### Atualizar: `tests/test_integration.py`

Adicionar teste que verifica que o debug section NAO aparece quando `debug_mode=0` e
APARECE quando `debug_mode=1`.

### Novo teste em `tests/test_theme.py` ou `tests/test_integration.py`

Teste: `test_debug_mode_appends_section` — mock do DeepSeek + mock do email,
verifica que o corpo do email contem "DEBUG - Trilha do Prompt" apenas quando
debug_mode=1.

## Ordem de Implementacao

1. **`app/models.py`** — ALTER TABLE + CREATE TABLE + Prompt.create/update + JOIN
2. **`app/executor.py`** — funcao `_build_debug_section` + logica de debug no run_schedule
3. **`app/routes.py`** — campo `debug_mode` nos forms create/edit
4. **Templates** — `create.html`, `edit.html`, `list.html`
5. **`tests/test_models.py`** — atualizar schema de teste
6. **Rodar `./run_tests.sh`** — validar tudo

## Notas

- **Tamanho do email**: A secao debug pode adicionar 2-10KB ao email dependendo do
  tamanho dos prompts. O system prompt base tem ~1KB, o user prompt varia conforme
  resultados de busca.
- **Seguranca**: Nao ha risco de泄露ao de secrets — os prompts sao os mesmos que ja
  seriam enviados ao DeepSeek. Nenhuma credencial e incluida.
- **Estilo**: A secao debug usa cores de terminal (verde/ciano sobre preto) para
  contraste visual claro com o conteudo principal.
- **Scroll em pre**: Os blocos `<pre>` tem `max-height:400px` com `overflow-y:auto`
  para nao dominarem o email se os prompts forem muito longos.
