# AI Mail Scheduler

Aplicação local que agenda prompts de IA (DeepSeek) via crontab e envia os resultados por email (Gmail) em HTML com CSS inline.

---

## Funcionalidades

- **CRUD de Prompts**: crie instruções para o DeepSeek com tom e estilo configuráveis (infográfico, resumo, newsletter, análise)
- **Agendamento com Cron**: configure horários via construtor visual de expressões cron, com ativação/desativação por toggle
- **Web Search**: o DeepSeek busca informações atualizadas na web antes de gerar o conteúdo
- **Envio por Email (Gmail)**: resultados em HTML com CSS inline, compatíveis com clientes de email
- **Execução Manual**: botão "Executar Agora" para testar prompts sem esperar o agendamento
- **Dashboard**: cards com estatísticas (prompts ativos, agendamentos, execuções do dia, taxa de sucesso)
- **Histórico de Logs**: registro de data/hora, status, duração e erros de cada execução
- **Gerenciador de Cron**: sincroniza agendamentos do banco com o crontab do Linux automaticamente
- **Autenticação**: login/senha com hash (werkzeug), proteção em todas as rotas

---

## Stack Tecnológica

| Componente      | Tecnologia                       |
|-----------------|----------------------------------|
| Linguagem       | Python 3.12+                     |
| Framework Web   | Flask 3.1                        |
| Banco de Dados  | SQLite (zero config)             |
| IA              | DeepSeek API (deepseek-chat)     |
| Email           | Gmail SMTP (TLS porta 587)       |
| Scheduler       | Linux Crontab (via python-crontab) |
| Autenticação    | Flask-Login + werkzeug (bcrypt)  |
| Frontend        | Jinja2 + CSS puro (tema escuro)  |
| Configuração    | .env (python-dotenv)             |

---

## Estrutura do Projeto

```
.
├── app/
│   ├── __init__.py           # Factory Flask, LoginManager, user_loader
│   ├── models.py             # SQLite: users, prompts, schedules, execution_logs
│   ├── auth.py               # Login, registro, logout
│   ├── routes.py             # Todas as rotas (dashboard, CRUD, cron, logs)
│   ├── deepseek_client.py    # Cliente API DeepSeek (web search, retry, timeout)
│   ├── email_sender.py       # Envio Gmail SMTP com HTML wrapper
│   ├── executor.py           # Orquestrador: DeepSeek → email → log
│   ├── cron_manager.py       # Gerenciador de crontab (add/remove/sync)
│   └── templates/
│       ├── base.html         # Layout base (sidebar, tema escuro)
│       ├── login.html        # Página de login/registro
│       ├── dashboard.html    # Dashboard com cards de estatísticas
│       ├── cron_status.html  # Status do crontab
│       ├── prompts/
│       │   ├── list.html     # Lista de prompts
│       │   ├── create.html   # Formulário de criação
│       │   └── edit.html     # Formulário de edição
│       ├── schedules/
│       │   ├── list.html     # Lista de agendamentos (com toggle)
│       │   ├── create.html   # Formulário com construtor de cron
│       │   └── edit.html     # Formulário de edição
│       └── logs/
│           └── list.html     # Histórico de execuções
├── scripts/
│   ├── run_executor.sh       # Chamado pelo cron a cada execução
│   └── setup_cron.sh         # Sincroniza todos os schedules com o crontab
├── data/
│   ├── scheduler.db          # Banco SQLite (gerado automaticamente)
│   └── backlogs/             # Backups do banco
├── docs/                     # Documentação e planejamento
├── .env.example              # Template de variáveis de ambiente
├── requirements.txt          # Dependências Python
├── run.sh                    # Script para iniciar o servidor
└── README.md
```

---

## Instalação

### Pré-requisitos

- **Linux** (necessário para crontab)
- **Python 3.12+**
- **Git**

### 1. Clone o repositório

```bash
git clone <repo-url>
cd openCode
```

### 2. Crie o ambiente virtual e instale as dependências

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```env
SECRET_KEY=uma_string_aleatoria_segura

# DeepSeek API (obtenha em https://platform.deepseek.com)
DEEPSEEK_API_KEY=sk-seu-token-aqui
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_TIMEOUT=120
DEEPSEEK_MAX_RETRIES=2

# Gmail SMTP (use App Password, veja abaixo)
GMAIL_USER=seuemail@gmail.com
GMAIL_APP_PASSWORD=sua-senha-de-app-16-digitos
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_FROM_NAME=AI Mail Scheduler
```

#### Como gerar o App Password do Gmail

1. Acesse https://myaccount.google.com/security
2. Ative **Verificação em duas etapas** (obrigatório)
3. Volte em Segurança > **Senhas de aplicativo**
4. Selecione app: `Mail`, dispositivo: `Other` > nome: `AI Scheduler`
5. Copie a senha de 16 dígitos e cole em `GMAIL_APP_PASSWORD`

### 4. Inicie o servidor

```bash
./run.sh
```

Ou manualmente:

```bash
source venv/bin/activate
python -c "from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000, debug=True)"
```

Acesse: **http://localhost:5000**

### 5. Crie seu usuário

Na página de login, clique em **"Criar conta"** e registre-se. O primeiro usuário criado não requer convite.

---

## Uso

### Fluxo Básico

1. **Crie um Prompt** em `/prompts/create`
   - Título: identificação do prompt
   - Conteúdo: o que você quer que o DeepSeek pesquise/elabore
   - Tom: infográfico, resumo, newsletter ou análise
2. **Crie um Agendamento** em `/schedules/create`
   - Selecione o prompt
   - Configure o horário no construtor de cron visual (minuto, hora, dia, mês, dia da semana)
   - Informe o email de destino
3. **Sincronize o Cron** (botão na página de agendamentos)
   - Ou o sistema sincroniza automaticamente ao salvar
4. **Aguarde** — o cron dispara no horário agendado e você recebe o email

### Execução Manual

Na lista de prompts, clique em **"Executar"** — informe o email de destino e o prompt será processado imediatamente, sem esperar o agendamento.

### Ativar/Desativar Agendamentos

Na lista de agendamentos, use o **toggle switch** para ativar ou desativar um agendamento sem deletá-lo.

### Monitorar Execuções

A página `/logs` mostra o histórico completo com:
- Data/hora, prompt, status (sucesso/erro)
- Duração em segundos
- Se foi disparado por `cron` ou `manual`
- Mensagem de erro (quando houver)

---

## API Routes (Interface Web)

### Autenticação

| Método | Rota              | Descrição       | Protegida |
|--------|-------------------|-----------------|-----------|
| GET    | `/auth/login`     | Formulário      | Não       |
| POST   | `/auth/login`     | Autenticar      | Não       |
| GET    | `/auth/register`  | Criar conta     | Não       |
| POST   | `/auth/register`  | Salvar conta    | Não       |
| GET    | `/auth/logout`    | Sair            | Sim       |

### Dashboard

| Método | Rota | Descrição                | Protegida |
|--------|------|--------------------------|-----------|
| GET    | `/`  | Cards com estatísticas   | Sim       |

### Prompts

| Método | Rota                    | Descrição          |
|--------|-------------------------|--------------------|
| GET    | `/prompts`              | Listar             |
| GET    | `/prompts/create`       | Formulário         |
| POST   | `/prompts/create`       | Salvar             |
| GET    | `/prompts/<id>/edit`    | Editar             |
| POST   | `/prompts/<id>/edit`    | Salvar edição      |
| POST   | `/prompts/<id>/delete`  | Deletar            |
| POST   | `/prompts/<id>/run`     | Executar agora     |

### Agendamentos

| Método | Rota                       | Descrição          |
|--------|----------------------------|--------------------|
| GET    | `/schedules`               | Listar             |
| GET    | `/schedules/create`        | Formulário         |
| POST   | `/schedules/create`        | Salvar             |
| GET    | `/schedules/<id>/edit`     | Editar             |
| POST   | `/schedules/<id>/edit`     | Salvar edição      |
| POST   | `/schedules/<id>/delete`   | Deletar            |
| POST   | `/schedules/<id>/toggle`   | Ativar/desativar   |

### Logs e Cron

| Método | Rota            | Descrição               |
|--------|-----------------|-------------------------|
| GET    | `/logs`         | Histórico de execuções  |
| POST   | `/cron/sync`    | Sincronizar crontab     |
| GET    | `/cron/status`  | Ver entradas do crontab |

---

## Banco de Dados (SQLite)

O banco é criado automaticamente em `data/scheduler.db` na primeira execução.

### Tabelas

- **users** — credenciais dos usuários da interface web
- **prompts** — instruções para o DeepSeek (título, conteúdo, tom, formato)
- **schedules** — agendamentos (FK prompt, expressão cron, email destino)
- **execution_logs** — histórico de execuções (status, duração, erro)
- **schema_version** — controle de versão do schema

### Backup

```bash
cp data/scheduler.db "data/backups/scheduler_$(date +%Y%m%d).db"
```

---

## Funcionamento do Cron

O gerenciador de cron mantém as entradas do crontab do usuário Linux sincronizadas com a tabela `schedules`. Cada entrada é identificada por um comentário único:

```
# AI_SCHEDULER:3 | Toda quarta 8AM - Noticias financeiras
0 8 * * 3 /home/daniel/myDev/openCode/scripts/run_executor.sh 3
```

### Comandos úteis

```bash
# Ver entradas do crontab
crontab -l

# Ver logs de execução
tail -f data/executor.log

# Testar executor manualmente
./scripts/run_executor.sh <schedule_id>

# Sincronizar todos os agendamentos
./scripts/setup_cron.sh
```

### Precauções

- O app **nunca** limpa o crontab inteiro
- Somente entradas com o marcador `AI_SCHEDULER:` são gerenciadas
- Agendamentos inativos são removidos do crontab automaticamente

---

## Integração DeepSeek

### Modelo

Usa `deepseek-chat` (DeepSeek-V3), compatível com o formato OpenAI Chat Completions.

### Comportamento

- O system prompt instrui o modelo a gerar **HTML puro com CSS inline** (compatível com email)
- Quando `enable_search=True`, o modelo usa **web search** para buscar informações atualizadas
- Tratamento de erros: retry com backoff, timeout de 120s, rate limit handling
- Limpeza automática de blocos de código markdown (\`\`\`html) da resposta

### Custos (referência)

- ~$0.27 / milhão de tokens de input
- ~$1.10 / milhão de tokens de output
- Monitore via logs de duração no dashboard

---

## Configurações Avançadas (.env)

| Variável              | Padrão                    | Descrição                              |
|-----------------------|---------------------------|----------------------------------------|
| `SECRET_KEY`          | `dev-secret-change-me`    | Chave secreta Flask (sessão)           |
| `DEEPSEEK_API_KEY`    | —                         | Token da API DeepSeek                  |
| `DEEPSEEK_BASE_URL`   | `https://api.deepseek.com`| URL base da API                        |
| `DEEPSEEK_MODEL`      | `deepseek-chat`           | Modelo a ser usado                     |
| `DEEPSEEK_MAX_TOKENS` | `4096`                    | Tokens máximos na resposta             |
| `DEEPSEEK_TIMEOUT`    | `120`                     | Timeout da requisição (segundos)       |
| `DEEPSEEK_MAX_RETRIES`| `2`                       | Tentativas em caso de falha            |
| `GMAIL_USER`          | —                         | Email Gmail remetente                  |
| `GMAIL_APP_PASSWORD`  | —                         | Senha de aplicativo (16 dígitos)       |
| `SMTP_SERVER`         | `smtp.gmail.com`          | Servidor SMTP                          |
| `SMTP_PORT`           | `587`                     | Porta SMTP                             |
| `EMAIL_FROM_NAME`     | `AI Mail Scheduler`       | Nome do remetente nos emails           |

---

## Segurança

- **API Key DeepSeek**: armazenada apenas no `.env`, nunca no banco ou código
- **App Password Gmail**: mesma política
- **Senha do usuário**: hash com `werkzeug.security.generate_password_hash`
- **Sessão Flask**: secret key configurável via `.env`
- **SQLite**: arquivo com permissões restritas (recomendado `chmod 600`)
- **Crontab**: opera apenas no crontab do usuário local, sem root

---

## Resolução de Problemas

| Problema                            | Solução                                                        |
|-------------------------------------|----------------------------------------------------------------|
| DeepSeek retorna erro 401           | Verifique `DEEPSEEK_API_KEY` no `.env`                        |
| Email não chega / erro SMTP 535     | Confira `GMAIL_APP_PASSWORD` (precisa ser App Password, não a senha normal) |
| Cron não dispara                    | Execute `crontab -l` e verifique se as entradas existem; rode `./scripts/setup_cron.sh` |
| "Não foi possível acessar o crontab"| O usuário pode não ter permissão; verifique com `crontab -l` |
| Erro de timeout no DeepSeek         | Aumente `DEEPSEEK_TIMEOUT` no `.env`                          |
| Banco SQLite corrompido             | Restaure de `data/backups/` ou delete `data/scheduler.db` (será recriado) |
| Porta 5000 em uso                   | Altere a porta no `run.sh` ou use `--port`                    |

---

## Deploy com Docker

### Pré-requisitos

- Docker 24+ e Docker Compose v2+
- Git

### Estrutura Docker

A aplicação roda em **2 containers** gerenciados pelo Compose:

| Container          | Função                                              |
|--------------------|-----------------------------------------------------|
| `ai-scheduler-web` | Flask na porta 5000 com healthcheck HTTP            |
| `ai-scheduler-cron`| Supercronic + sync automático do crontab via SQLite |

O cron tradicional do Linux é substituído pelo **[Supercronic](https://github.com/aptible/supercronic)**, um runner feito para containers que roda em foreground e lida com sinais de término.

### Deploy rápido

```bash
# 1. Clone o repositório
git clone <repo-url> /opt/ai-mail-scheduler
cd /opt/ai-mail-scheduler

# 2. Configure o .env
cp .env.example .env
nano .env  # preencha DEEPSEEK_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD, SECRET_KEY

# 3. Crie o diretório de dados
mkdir -p data/backups

# 4. Gere uma SECRET_KEY forte (se ainda não tiver)
python3 -c "import secrets; print(secrets.token_hex(32))"

# 5. Build e start
docker compose build
docker compose up -d

# 6. Verifique os logs
docker compose logs -f

# 7. Acesse http://<servidor>:5000 e registre-se
```

### Comandos úteis

```bash
docker compose ps                   # Status dos containers
docker compose logs -f              # Todos os logs
docker compose logs cron -f         # Logs do cron
docker compose restart              # Reiniciar serviços
docker compose down                 # Parar tudo
docker compose up -d --build        # Rebuild e restart

# Ver crontab ativo dentro do container
docker compose exec cron cat /app/crontab.txt

# Backup do banco
cp data/scheduler.db "data/backups/scheduler_$(date +%Y%m%d_%H%M).db"

# Atualizar a aplicação
git pull && docker compose up -d --build
```

### Nginx + HTTPS (opcional)

```nginx
server {
    listen 80;
    server_name scheduler.seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d scheduler.seu-dominio.com
```

### Troubleshooting Docker

| Problema                              | Verificação                                            |
|---------------------------------------|--------------------------------------------------------|
| Container não inicia                  | `docker compose logs web`                              |
| Cron não executa                      | `docker compose exec cron cat /app/crontab.txt`        |
| Healthcheck falhando                  | `docker compose exec web curl localhost:5000/auth/login`|
| Permissão negada no volume            | `chmod -R 755 data/`                                   |
| Banco SQLite corrompido               | Restaurar de `data/backups/`                           |

---

## Desenvolvimento

### Estrutura de Testes

```
tests/
├── __init__.py
├── test_auth.py            # Hash e verificação de senhas
├── test_models.py          # CRUD de todas as tabelas SQLite
├── test_deepseek.py        # Cliente DeepSeek (mocked)
├── test_email.py           # Envio de email Gmail (mocked)
├── test_cron.py            # Gerenciador de crontab (mocked)
├── test_routes.py          # Todas as rotas Flask (integração)
├── test_integration.py     # Fluxos completos (integração)
└── run_tests.sh            # Script para rodar todos os testes
```

### Rodar todos os testes

```bash
./run_tests.sh
```

O script executa 7 módulos com **81 testes** no total e exibe um resumo colorido com o status de cada módulo.

### Rodar um módulo específico

```bash
source venv/bin/activate

# Modelos do banco (22 testes)
python -m unittest tests.test_models -v

# Autenticação (3 testes)
python -m unittest tests.test_auth -v

# Cliente DeepSeek mock (9 testes)
python -m unittest tests.test_deepseek -v

# Email sender mock (8 testes)
python -m unittest tests.test_email -v

# Cron manager mock (10 testes)
python -m unittest tests.test_cron -v

# Rotas Flask (23 testes)
python -m unittest tests.test_routes -v

# Integração completa (6 testes)
python -m unittest tests.test_integration -v
```

### Cobertura dos Testes

| Camada                 | Estratégia                                    |
|------------------------|-----------------------------------------------|
| Banco de dados         | SQLite em `/tmp` isolado; app context Flask   |
| DeepSeek API           | Mock completo com `unittest.mock.patch`       |
| Gmail SMTP             | Mock completo; sem envio real                 |
| Crontab                | Mock do `CronTab`; sem alterar crontab real   |
| Rotas Flask            | `app.test_client()` com banco isolado         |
| Integração             | Fluxos end-to-end com mocks de serviços externos |

### Testar carregamento da aplicação

```bash
source venv/bin/activate
python -c "from app import create_app; create_app(); print('OK')"
```

### Testar executor manualmente

```bash
python app/executor.py --schedule-id 1
```

### Atualizar dependências

```bash
pip install --upgrade -r requirements.txt
```

---

## Licença

MIT
