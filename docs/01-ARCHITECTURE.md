# Arquitetura do Sistema

## Diagrama de Componentes

```
+--------------------------------------------------------------+
|                     INTERFACE WEB (Flask)                      |
|  http://localhost:5000                                        |
|  +-----------+  +-----------+  +-----------+  +------------+ |
|  |  Login    |  | Dashboard |  | Prompts   |  | Agendamentos| |
|  |  /auth    |  |  /        |  | /prompts  |  | /schedules | |
|  +-----------+  +-----------+  +-----------+  +------------+ |
|                                                               |
|  +----------------------------------------------------------+|
|  |                    SQLite Database                        ||
|  |  users | prompts | schedules | execution_logs            ||
|  +----------------------------------------------------------+|
+--------------------------------------------------------------+
        |                    |                    |
        v                    v                    v
+---------------+   +----------------+   +----------------+
| Cron Manager  |   | DeepSeek Client|   | Email Sender   |
| (python-      |   | (API REST)     |   | (SMTP Gmail)   |
|  crontab)     |   |                |   |                |
+---------------+   +----------------+   +----------------+
        |                    |                    |
        v                    v                    v
+---------------+   +----------------+   +----------------+
| Linux Crontab |   | DeepSeek API   |   | Gmail SMTP     |
| /var/spool/   |   | api.deepseek.  |   | smtp.gmail.com |
| cron/crontabs |   | com            |   | :587           |
+---------------+   +----------------+   +----------------+
```

---

## Fluxo de Dados

### 1. Registro de Prompt/Agendamento

```
Usuario -> Formulario Web -> Flask Route -> SQLite INSERT
                                              |
Flask -> Cron Manager -> Atualiza crontab do Linux
```

### 2. Execucao Agendada (via cron)

```
crontab dispara -> scripts/run_executor.sh
                         |
                    app/executor.py
                         |
                    +----+----+
                    |         |
               Busca prompt  Busca config do
               no SQLite     schedule no SQLite
                    |         |
                    +----+----+
                         |
                    deepseek_client.py
                    (envia prompt + instrucoes)
                         |
                    DeepSeek API
                    (web search + geracao)
                         |
                    email_sender.py
                    (formata HTML + envia)
                         |
                    Gmail SMTP -> Usuario recebe email
                         |
                    SQLite INSERT (execution_logs)
```

### 3. Execucao Manual (Botao "Executar Agora")

```
Usuario clica "Executar Agora" na interface
    -> Flask route /prompts/<id>/run
    -> Mesmo fluxo do executor (DeepSeek + Email)
    -> Redireciona com mensagem de sucesso/erro
```

---

## Componentes e Responsabilidades

### `app/__init__.py`
- Factory function para criar app Flask
- Configuracao de secret key, banco de dados, login manager
- Registro de blueprints

### `app/models.py`
- Definicao das tabelas SQLite
- Classes: User, Prompt, Schedule, ExecutionLog
- Relacionamentos entre tabelas

### `app/routes.py`
- Rotas da interface web
- CRUD de prompts e schedules
- Dashboard com listagem e status
- Botao de execucao manual

### `app/auth.py`
- Login/logout
- Protecao de rotas com @login_required
- Hash de senha (werkzeug)

### `app/executor.py`
- Script chamado pelo cron (ou botao manual)
- Recebe ID do agendamento como argumento
- Orquestra: busca prompt -> chama DeepSeek -> envia email -> log

### `app/deepseek_client.py`
- Funcao que envia prompt para API DeepSeek
- Configura web search
- Retorna resposta formatada

### `app/email_sender.py`
- Conexao SMTP com Gmail
- Formata HTML com CSS inline
- Envia email para destinatario configurado

### `app/cron_manager.py`
- Adiciona/remove entradas no crontab do usuario Linux
- Usa biblioteca python-crontab
- Cada agendamento vira uma linha no crontab

### `scripts/run_executor.sh`
- Script shell chamado pelo cron
- Ativa venv (se aplicavel)
- Executa app/executor.py com argumento do ID

### `scripts/setup_cron.sh`
- Instala/atualiza todos os cron jobs baseado nos schedules ativos no banco
- Pode ser chamado via Flask (botao "Sincronizar Cron") ou manualmente

---

## Seguranca

- **API Key DeepSeek**: armazenada apenas no .env, nunca no banco ou codigo
- **App Password Gmail**: armazenada no .env, mesma politica
- **Senha do usuario web**: hash bcrypt/werkzeug, nunca plain text
- **Sessao Flask**: secret key aleatoria no .env
- **SQLite**: arquivo com permissoes restritas (chmod 600)
- **Crontab**: usa crontab do usuario local, sem permissoes de root

---

## Tratamento de Erros

| Ponto de falha          | Tratamento                                    |
|-------------------------|-----------------------------------------------|
| DeepSeek API offline    | Loga erro, envia email de falha (opcional)    |
| Gmail SMTP offline      | Loga erro, tenta reenvio (ate 3x)             |
| Cron nao dispara        | Interface mostra ultimo status de execucao    |
| Banco SQLite corrompido | Backup simples (.db.bak)                      |
| Prompt vazio            | Validacao no formulario e no executor         |
