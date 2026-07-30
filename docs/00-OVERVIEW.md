# Visao Geral do Projeto

## Nome (provisorio): `ai-mail-scheduler`

## Objetivo

Aplicacao local que permite registrar prompts de IA (DeepSeek), agenda-los via crontab,
e receber os resultados processados por email (Gmail) em formato HTML com CSS inline.

Exemplo de uso: "Me envie todas as novidades do mundo financeiro as 8AM todas as quartas-feira,
em formato de infografico HTML por email."

---

## Stack Tecnologica (Decisoes Tomadas)

| Componente      | Escolha           | Justificativa                              |
|-----------------|-------------------|--------------------------------------------|
| Linguagem       | Python + Shell    | Python para logica principal, Shell para cron |
| Framework Web   | Flask             | Simples, leve, ideal para app local        |
| Banco de Dados  | SQLite            | Zero configuracao, arquivo unico           |
| IA              | DeepSeek API      | Via web search da propria API              |
| Email           | Gmail SMTP        | App Password (senha de aplicativo)         |
| Frontend        | HTML + CSS puro   | Templates Jinja2 do Flask                  |
| API Key Storage | .env              | Via python-dotenv                          |
| Autenticacao    | Login/senha       | Sessao Flask + hash de senha               |
| Porta           | 5000              | Padrao Flask                               |
| Historico       | Log de execucao   | Registro de data/hora/status, sem conteudo |
| Saida Email     | HTML + CSS inline | Infografico direto no corpo do email       |

---

## Estrutura de Diretorios (planejada)

```
/home/daniel/myDev/openCode/
├── docs/                    # Documentacao e planejamento
│   ├── 00-OVERVIEW.md
│   ├── 01-ARCHITECTURE.md
│   ├── 02-DATABASE.md
│   ├── 03-WEB-INTERFACE.md
│   ├── 04-DEEPSEEK-INTEGRATION.md
│   ├── 05-EMAIL-GMAIL.md
│   ├── 06-CRON-MANAGER.md
│   └── 07-SETUP-INSTALL.md
├── app/                     # Aplicacao Flask
│   ├── __init__.py
│   ├── models.py            # Modelos SQLite
│   ├── routes.py            # Rotas da interface web
│   ├── auth.py              # Autenticacao
│   ├── executor.py          # Executor chamado pelo cron
│   ├── deepseek_client.py   # Cliente API DeepSeek
│   ├── email_sender.py      # Envio de email Gmail
│   ├── cron_manager.py      # Gerenciador de crontab
│   └── templates/           # Templates HTML (Jinja2)
├── scripts/                 # Shell scripts auxiliares
│   ├── run_executor.sh      # Script chamado pelo cron
│   └── setup_cron.sh        # Script para instalar cron jobs
├── data/                    # Dados da aplicacao
│   └── scheduler.db         # Banco SQLite (gerado)
├── .env.example             # Exemplo de variaveis de ambiente
├── .gitignore
├── requirements.txt         # Dependencias Python
├── run.sh                   # Script para iniciar servidor Flask
└── Readme.txt               # (existente)
```

---

## Fluxo Resumido

```
[Usuario] -> [Interface Web Flask] -> [SQLite]
                  |
          registra prompt + agendamento
                  |
          [Cron Manager] atualiza crontab
                  |
          [cron] dispara no horario agendado
                  |
          [Executor Python] -> [DeepSeek API] -> [email Gmail]
                  |
          [Usuario] recebe email com resultado
```

---

## Dependencias Python (preliminar)

```
flask
flask-login
python-dotenv
requests         # ou openai/httpx para DeepSeek API
schedule         # opcional, para gerenciamento de agendamento
python-crontab   # para manipular crontab via Python
markdown         # para converter MD em HTML se necessario
```

---

## Proximas Etapas

Apos aprovacao do planejamento (.md files):
1. Configurar ambiente Python (venv)
2. Criar banco SQLite e modelos
3. Implementar autenticacao
4. Criar CRUD de prompts e agendamentos
5. Implementar cliente DeepSeek
6. Implementar envio de email Gmail
7. Criar executor que junta tudo
8. Criar gerenciador de cron
9. Criar interface web completa
10. Testes e documentacao final
