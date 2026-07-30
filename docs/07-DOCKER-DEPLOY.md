# Deploy com Docker — Planejamento

## Objetivo

Containerizar a aplicação `ai-mail-scheduler` para deploy em produção, garantindo que todos os componentes (Flask, crontab, SQLite, scripts) funcionem corretamente dentro de containers Docker.

---

## Decisões de Arquitetura

| Decisão                     | Escolha                  | Justificativa                                              |
|-----------------------------|--------------------------|------------------------------------------------------------|
| Container único vs múltiplos| **2 containers**         | Web (Flask) + Cron (executor) separados para isolamento    |
| Base image                  | `python:3.12-slim`       | Leve, oficial, Python 3.12                                 |
| Orquestração                | `docker compose`         | Simples, adequado para single-server                       |
| Cron no container           | `supercronic`            | Alternativa leve ao cron tradicional, feito para containers |
| Banco de dados              | Volume bind mount        | SQLite persiste em volume no host                          |
| Logs                        | Volume + stdout          | `executor.log` em volume, Flask logs via stdout            |
| Porta                       | `5000` (interna)         | Mapeada para porta desejada no host                        |
| Healthcheck                 | `curl localhost:5000`    | Verifica se Flask está respondendo                         |
| Restart policy              | `unless-stopped`         | Reinicia automaticamente em falhas                         |

---

## Estrutura de Arquivos (planejada)

```
.
├── Dockerfile
├── docker-compose.yml
├── .env                          # (existente, referenciado pelo compose)
├── .dockerignore
├── scripts/
│   └── entrypoint-cron.sh        # Entrypoint do container de cron
├── requirements.txt              # (existente)
├── run.sh                        # (existente)
└── ...
```

---

## Dockerfile

### Imagem base e camadas

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x scripts/*.sh run.sh

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/auth/login || exit 1
```

### Entrypoints

Dois entrypoints distintos, selecionados via `command` no compose:

**Serviço Web:**
```dockerfile
CMD ["python", "-c", "from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000)"]
```

**Serviço Cron:**
```bash
#!/bin/bash
# entrypoint-cron.sh
# 1. Configura supercronic com os schedules ativos do banco
# 2. Roda sync a cada 60s para manter crontab atualizado
# 3. Executa supercronic em foreground

while true; do
    python -c "from app.cron_manager import sync_all_schedules; sync_all_schedules()"
    sleep 60
done &

exec supercronic /app/crontab.txt
```

---

## Docker Compose

```yaml
version: "3.8"

services:
  web:
    build: .
    container_name: ai-scheduler-web
    ports:
      - "${APP_PORT:-5000}:5000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data          # SQLite + logs persistentes
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    command: python -c "from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000)"

  cron:
    build: .
    container_name: ai-scheduler-cron
    env_file:
      - .env
    volumes:
      - ./data:/app/data          # Mesmo volume, compartilha DB
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    entrypoint: ["/app/scripts/entrypoint-cron.sh"]
    depends_on:
      web:
        condition: service_healthy
```

---

## Gerenciamento do Cron no Container

### Problema

O `python-crontab` manipula o crontab do **usuário Linux do host**. Dentro do container, o crontab tradicional (`cron` daemon) não está disponível na imagem `slim`, e mesmo se instalado, não é a prática recomendada para containers.

### Solução: Supercronic

[Supercronic](https://github.com/aptible/supercronic) é um runner de cron escrito em Go, feito para containers:
- Roda em **foreground** (compatível com Docker)
- Lê arquivo crontab padrão
- Não precisa de daemon, systemd, ou root
- Suporta logging para stdout/stderr
- Lida bem com sinais de término (SIGTERM)

### Mecanismo

1. O container `cron` tem um loop que a cada **60 segundos** lê os schedules ativos do SQLite e gera um arquivo `/app/crontab.txt`
2. O `supercronic` roda esse arquivo continuamente
3. Cada entrada chama: `python -m app.executor --schedule-id <ID>`

### crontab.txt (exemplo gerado)

```
# AI_SCHEDULER:3 | Toda quarta 8AM - Noticias
0 8 * * 3 cd /app && python -m app.executor --schedule-id 3

# AI_SCHEDULER:5 | Diario 9AM - Resumo
0 9 * * * cd /app && python -m app.executor --schedule-id 5
```

### entrypoint-cron.sh

```bash
#!/bin/bash
set -e

# Função que sincroniza schedules do SQLite -> crontab.txt
sync_crontab() {
    python -c "
import os, sys
sys.path.insert(0, '/app')
from app import create_app
app = create_app()
with app.app_context():
    from app.models import Schedule
    schedules = Schedule.get_active_schedules()
    with open('/app/crontab.txt', 'w') as f:
        for s in schedules:
            f.write(f'# AI_SCHEDULER:{s[\"id\"]} | {s[\"description\"]}\n')
            f.write(f'{s[\"cron_expr\"]} cd /app && python -m app.executor --schedule-id {s[\"id\"]}\n\n')
    print(f'Synced {len(schedules)} schedules')
"
}

# Sincroniza imediatamente
sync_crontab

# Loop de sincronização em background
while true; do
    sleep 60
    sync_crontab
done &

# Supercronic em foreground
exec /usr/local/bin/supercronic /app/crontab.txt
```

---

## .dockerignore

```
venv/
__pycache__/
*.pyc
.git/
.gitignore
docs/
data/scheduler.db
data/executor.log
data/backups/
*.swp
.vscode/
.idea/
README.md
```

---

## Volumes e Persistência

| Caminho no container | Descrição                               | Persistência    |
|----------------------|-----------------------------------------|-----------------|
| `/app/data`          | SQLite (`scheduler.db`), logs, backups  | Bind mount `./data` |
| `/app/.env`          | Carregado via `env_file` do compose     | Fora do volume, via compose |

### Backup do SQLite

Adicionar ao `entrypoint-cron.sh` um job diário:

```bash
# No crontab.txt:
0 2 * * * cp /app/data/scheduler.db /app/data/backups/scheduler_$(date +\%Y\%m\%d).db
```

---

## Healthcheck

### Container Web

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/auth/login"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

### Container Cron

```yaml
healthcheck:
  test: ["CMD", "pgrep", "supercronic"]
  interval: 30s
  timeout: 5s
  retries: 3
```

---

## Deploy — Passo a Passo

### Pré-requisitos no servidor

- Docker 24+ e Docker Compose v2+
- Git
- Porta desejada liberada no firewall (ex: 5000)

### 1. Clonar o repositório

```bash
git clone <repo-url> /opt/ai-mail-scheduler
cd /opt/ai-mail-scheduler
```

### 2. Configurar .env

```bash
cp .env.example .env
nano .env  # preencher DEEPSEEK_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD, SECRET_KEY
```

**Importante:** Gerar uma `SECRET_KEY` forte:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Criar diretório de dados

```bash
mkdir -p data/backups
chmod 755 data
```

### 4. Build e start

```bash
docker compose build
docker compose up -d
```

### 5. Verificar logs

```bash
docker compose logs -f
docker compose logs cron -f   # apenas container cron
docker compose logs web -f    # apenas container web
```

### 6. Criar usuário

Acessar `http://<servidor>:5000/auth/register` e criar o primeiro usuário.

### 7. Verificar health

```bash
docker compose ps
# STATUS deve mostrar "healthy" para ambos serviços
```

---

## Comandos Úteis (Produção)

```bash
# Status dos containers
docker compose ps

# Reiniciar serviços
docker compose restart

# Atualizar a aplicação
git pull
docker compose build
docker compose up -d

# Backup manual do banco
cp data/scheduler.db "data/backups/scheduler_$(date +%Y%m%d_%H%M).db"

# Restaurar banco
cp data/backups/scheduler_20260728_1200.db data/scheduler.db

# Acessar shell do container web
docker compose exec web bash

# Ver crontab ativo dentro do container cron
docker compose exec cron cat /app/crontab.txt

# Limpar logs antigos (manter últimos 30 dias)
find data/backups/ -name "scheduler_*" -mtime +30 -delete
```

---

## Monitoramento

### Logs

- **Flask**: stdout do container `web` (acessível via `docker compose logs`)
- **Executor**: `/app/data/executor.log` (no volume, acessível via `docker compose exec cron cat /app/data/executor.log`)

### Métricas sugeridas para futuro

- Prometheus + Grafana para métricas de execução
- Uptime Kuma para monitorar healthcheck HTTP
- Notificação (email/Discord) em caso de falha consecutiva de execuções

---

## Segurança

| Item                       | Ação                                                            |
|----------------------------|-----------------------------------------------------------------|
| `.env`                     | Fora do volume, nunca commitado; `chmod 600 .env`              |
| Porta Flask                | Expor apenas se necessário; usar reverse proxy (nginx) com HTTPS |
| SQLite                     | Permissões restritas no volume (`chmod 600 data/scheduler.db`) |
| Dependências               | `--no-cache-dir` no pip install; imagem slim                    |
| Secrets                    | Nunca no Dockerfile; usar `.env` + `env_file`                  |
| Usuário no container       | Rodar como não-root (adicionar `USER 1000` ao Dockerfile)      |

---

## Configuração com Nginx Reverse Proxy (opcional)

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

Com Certbot para HTTPS:

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d scheduler.seu-dominio.com
```

---

## Troubleshooting

| Problema                              | Verificação                                            |
|---------------------------------------|--------------------------------------------------------|
| Container não inicia                  | `docker compose logs web`                              |
| Cron não executa                      | `docker compose exec cron cat /app/crontab.txt`        |
| Email não envia                       | Verificar `GMAIL_APP_PASSWORD` no `.env`               |
| DeepSeek erro 401                     | Verificar `DEEPSEEK_API_KEY` no `.env`                 |
| Banco SQLite corrompido               | Restaurar de `data/backups/`                           |
| Porta já em uso                       | Alterar `APP_PORT` no `.env` ou no `docker-compose.yml`|
| Permissão negada no volume            | `chmod -R 755 data/`                                   |

---

## Próximas Etapas (após aprovação)

1. Criar `Dockerfile`
2. Criar `docker-compose.yml`
3. Criar `.dockerignore`
4. Criar `scripts/entrypoint-cron.sh`
5. Adicionar `supercronic` ao build
6. Testar build e execução local
7. Validar healthchecks
8. Testar fluxo completo (criar prompt → agendar → receber email)
9. Documentar deploy no README.md
