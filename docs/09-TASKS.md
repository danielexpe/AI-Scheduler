# Tarefas (Agendamento sem IA)

## Objetivo

Permitir agendar o envio de emails que **nao dependem de IA** (DeepSeek).
Dois novos tipos de tarefa alem dos prompts de IA existentes:

| Tipo | Descricao | Exemplo |
|------|-----------|---------|
| `static` | Email com conteudo HTML/texto fixo definido pelo usuario | "Relatorio semanal de vendas" com HTML pronto |
| `command` | Email com a saida de um comando Linux executado no container cron | `df -h`, `free -m`, `docker ps`, script personalizado |

---

## Decisoes de Design

| Decisao | Escolha | Justificativa |
|---------|---------|---------------|
| Interface | Nova aba **"Tarefas"** no menu lateral | Separacao clara: Prompts = IA, Tarefas = sem IA |
| Conteudo estatico | Textarea com toggle HTML/Texto simples | Flexibilidade: tanto HTML puro quanto texto formatado automaticamente |
| Comando Linux | Campo de texto livre | Maxima flexibilidade. Container roda como usuario `scheduler` sem privilegios |
| Modelagem | Compartilhar tabela `schedules` | Adicionar coluna `schedule_type` + colunas nullable. Evita duplicacao de logica de agendamento |
| Nomenclatura | "Tarefas" no menu, `task_type` no codigo | Portugues na UI, ingles no codigo |

---

## Banco de Dados

### Alteracao na tabela `schedules`

```sql
ALTER TABLE schedules ADD COLUMN schedule_type TEXT DEFAULT 'ai';
ALTER TABLE schedules ADD COLUMN static_content TEXT;
ALTER TABLE schedules ADD COLUMN static_is_html INTEGER DEFAULT 0;
ALTER TABLE schedules ADD COLUMN command_text TEXT;
ALTER TABLE schedules ADD COLUMN static_subject TEXT;
```

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `schedule_type` | TEXT | `ai`, `static`, `command` |
| `static_content` | TEXT (nullable) | Conteudo HTML/texto fixo |
| `static_is_html` | INTEGER | 1=HTML, 0=texto simples |
| `command_text` | TEXT (nullable) | Comando Linux a executar |
| `static_subject` | TEXT (nullable) | Assunto do email para tipo static |

---

## Estrutura de Rotas

### Nova blueprint: `tasks_bp` (prefixo `/tasks`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/tasks` | Lista todas as tarefas (filtra schedules com `schedule_type != 'ai'`) |
| GET/POST | `/tasks/create` | Formulario de criacao (tipo: static ou command, campos condicionais) |
| GET/POST | `/tasks/<id>/edit` | Edicao de tarefa |
| POST | `/tasks/<id>/delete` | Exclusao |
| POST | `/tasks/<id>/toggle` | Ativar/desativar |
| POST | `/tasks/<id>/run` | Execucao manual (envia email sem aguardar cron) |

### Alteracao nas rotas existentes

| Rota | Alteracao |
|------|-----------|
| `/prompts` | Sem alteracao (continua so prompts de IA) |
| `/schedules/create` | Adicionar opcao de selecionar tarefa alem de prompt |
| `Schedule.get_all()` | Filtrar/identificar `schedule_type` |
| Dashboard | Card extra: "Tarefas ativas" |

---

## Templates Jinja2

```
app/templates/tasks/
├── list.html        # Lista de tarefas com colunas: tipo, descricao, destino, cron, status
├── create.html      # Formulario: selector de tipo, campos condicionais via JS
└── edit.html        # Mesmo formulario do create, preenchido
```

---

## Logica de Execucao

### Fluxo atualizado do `executor.py`

```python
def run_schedule(schedule_id):
    schedule = Schedule.get_by_id(schedule_id)
    
    if schedule["schedule_type"] == "ai":
        # Fluxo existente: DeepSeek -> email
        ...
    elif schedule["schedule_type"] == "static":
        # Conteudo fixo -> email
        ...
    elif schedule["schedule_type"] == "command":
        # Executar comando -> capturar saida -> email
        ...
```

### Tipo `static`

1. Se `static_is_html=1`: usar `static_content` diretamente como body HTML
2. Se `static_is_html=0`: converter quebras de linha em `<br>`, envelopar no template HTML
3. Assunto: `static_subject` (ou fallback: descricao da tarefa)

### Tipo `command`

1. Executar `command_text` via `subprocess.run(cmd, shell=True, capture_output=True, timeout=30)`
2. Timeout de 30 segundos para evitar comandos travados
3. Capturar stdout e stderr
4. Formatar saida como `<pre>` dentro do template HTML
5. Se exit code != 0, incluir stderr e marcar log como warning
6. Assunto: `[Scheduler] Comando: {command_text[:60]}`

---

## Seguranca

| Risco | Mitigacao |
|-------|-----------|
| Comando malicioso (`rm -rf /`) | Container roda como usuario `scheduler` (nao-root), sem sudo. Volume `./data` e montado, mas o sistema de arquivos do container e efemero. |
| Comando travado (infinito) | `timeout=30s` no `subprocess.run`. Stderr enviado no email. |
| Injecao de HTML no tipo static | O toggle "HTML" fica visivel com aviso. HTML vai direto no email (sem sanitizacao — proposital, o usuario quer controle total). |
| Vazamento de senhas no comando | Aviso na UI: "Nao inclua senhas ou tokens no comando. A saida sera enviada por email." |

---

## Interface do Usuario

### Menu lateral

```
[Painel]
[Prompts]      <- existente
[Tarefas]      <- NOVO
[Agendamentos] <- existente (mostra tudo: ai + static + command)
[Logs]
[Cron]
```

### Formulario de criacao de Tarefa

Campos comuns:
- Tipo: [dropdown: Estatico / Comando Linux]
- Descricao
- Email destino
- Agendamento (cron builder, mesmo do Schedule)

Campos condicionais (tipo Estatico):
- Toggle: HTML | Texto simples
- Assunto do email
- Conteudo (textarea grande)

Campos condicionais (tipo Comando):
- Comando (textarea)
- Aviso de seguranca (texto fixo na UI)

---

## Impacto no Codigo Existente

| Arquivo | Mudanca |
|---------|---------|
| `app/models.py` | `Schedule.create/update` aceitar novos campos. Nova query `get_tasks()`. |
| `app/routes.py` | Sem alteracao (prompts continuam iguais) |
| `app/tasks.py` | **NOVO** — blueprint de tarefas |
| `app/executor.py` | Adicionar branches `static` e `command` no `run_schedule` |
| `app/cron_manager.py` | Sem alteracao (ja sincroniza todos os schedules ativos) |
| `app/templates/base.html` | Adicionar link "Tarefas" no menu |
| `app/templates/tasks/*.html` | **NOVOS** — 3 templates |
| `app/templates/dashboard.html` | Card extra "Tarefas ativas" |
| `scripts/run_cron.sh` | Sem alteracao |
| `scripts/entrypoint-cron.sh` | Sem alteracao |
| `tests/` | Novos testes: `test_tasks.py`, `test_executor_static_command.py` |

---

## Sequencia de Implementacao

1. **Migracao do banco**: Adicionar colunas na tabela `schedules`
2. **Model**: Atualizar `Schedule.create/update/get_all`
3. **Executor**: Adicionar branches `static` e `command`
4. **Blueprint + Templates**: Criar `tasks.py` e os 3 templates
5. **Menu + Dashboard**: Atualizar navegacao e cards
6. **Testes**: Testar criacao, execucao manual, execucao via cron, seguranca do comando
