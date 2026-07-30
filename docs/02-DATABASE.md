# Schema do Banco de Dados (SQLite)

## Tabelas

### `users`

Armazena usuarios que podem acessar a interface web.

| Coluna     | Tipo     | Descricao                           |
|------------|----------|-------------------------------------|
| id         | INTEGER  | PK, autoincrement                   |
| username   | TEXT     | Nome de usuario, UNIQUE, NOT NULL   |
| password   | TEXT     | Hash da senha (werkzeug generate)   |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP           |

---

### `prompts`

Armazena os prompts (instrucoes para o DeepSeek).

| Coluna     | Tipo     | Descricao                                     |
|------------|----------|-----------------------------------------------|
| id         | INTEGER  | PK, autoincrement                             |
| title      | TEXT     | Titulo descritivo do prompt, NOT NULL         |
| content    | TEXT     | Conteudo do prompt, NOT NULL                  |
| tone       | TEXT     | Tom/estilo desejado (ex: infografico, resumo) |
| format     | TEXT     | Formato de saida (html, pdf - futuro)         |
| active     | BOOLEAN  | DEFAULT 1, permite desativar sem deletar      |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP                     |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP                     |

---

### `schedules`

Armazena os agendamentos (vincula prompt + horario cron).

| Coluna       | Tipo    | Descricao                                   |
|--------------|---------|---------------------------------------------|
| id           | INTEGER | PK, autoincrement                           |
| prompt_id    | INTEGER | FK -> prompts.id, NOT NULL                  |
| cron_expr    | TEXT    | Expressao cron (ex: 0 8 * * 3), NOT NULL    |
| description  | TEXT    | Descricao legivel: "Toda quarta 8AM"        |
| email_to     | TEXT    | Email destino, NOT NULL                     |
| active       | BOOLEAN | DEFAULT 1                                   |
| last_run_at  | DATETIME| Ultima execucao (NULL se nunca)             |
| created_at   | DATETIME| DEFAULT CURRENT_TIMESTAMP                   |
| updated_at   | DATETIME| DEFAULT CURRENT_TIMESTAMP                   |

---

### `execution_logs`

Armazena log de execucoes (sem conteudo do resultado).

| Coluna        | Tipo     | Descricao                                      |
|---------------|----------|------------------------------------------------|
| id            | INTEGER  | PK, autoincrement                              |
| schedule_id   | INTEGER  | FK -> schedules.id, NOT NULL                   |
| status        | TEXT     | 'success', 'error', 'timeout'                  |
| error_message | TEXT     | Mensagem de erro se status='error', nullable   |
| duration_ms   | INTEGER  | Duracao da execucao em milissegundos           |
| triggered_by  | TEXT     | 'cron' ou 'manual'                             |
| created_at    | DATETIME | DEFAULT CURRENT_TIMESTAMP                      |

---

## Relacionamentos

```
users (1) ----< (nao tem FK direta, interface unica)
prompts (1) ----< schedules (many)
schedules (1) ----< execution_logs (many)
```

## Indices

```sql
CREATE INDEX idx_schedules_prompt_id ON schedules(prompt_id);
CREATE INDEX idx_schedules_active ON schedules(active);
CREATE INDEX idx_execution_logs_schedule_id ON execution_logs(schedule_id);
CREATE INDEX idx_execution_logs_created_at ON execution_logs(created_at);
```

## SQL de Criacao

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tone TEXT DEFAULT 'infografico',
    format TEXT DEFAULT 'html',
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    cron_expr TEXT NOT NULL,
    description TEXT,
    email_to TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    last_run_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    duration_ms INTEGER,
    triggered_by TEXT DEFAULT 'cron',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id)
);
```

---

## Migrations

SQLite nao suporta migrations nativamente. Estrategia escolhida:

- **Simples**: script `app/models.py` usa `CREATE TABLE IF NOT EXISTS`
- Para mudancas futuras: script manual de ALTER ou recriar com backup
- Versionamento manual via numero de schema no banco (tabela `schema_version`)

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Backup

- Cron job diario opcional para copiar `data/scheduler.db` para `data/backups/scheduler_YYYYMMDD.db`
- Manter ultimos 7 backups
