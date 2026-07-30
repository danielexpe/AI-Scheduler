# Interface Web (Flask)

## Tecnologias

- **Backend**: Flask (Python)
- **Templates**: Jinja2 (engine padrao do Flask)
- **CSS**: Estilo inline/mesmo arquivo (sem build tools, sem npm)
- **JS**: Minimo, apenas para UX (confirm dialogs, toggle switches)

---

## Estrutura de Templates

```
app/templates/
├── base.html              # Layout base (navbar, head, footer)
├── login.html             # Pagina de login
├── dashboard.html         # Dashboard principal
├── prompts/
│   ├── list.html          # Lista de prompts
│   ├── create.html        # Formulario de criacao
│   ├── edit.html          # Formulario de edicao
│   └── preview.html       # Preview opcional
├── schedules/
│   ├── list.html          # Lista de agendamentos
│   ├── create.html        # Formulario de criacao
│   └── edit.html          # Formulario de edicao
└── logs/
    └── list.html          # Historico de execucoes
```

---

## Rotas

### Autenticacao

| Metodo | Rota            | Descricao         | Protegida |
|--------|-----------------|-------------------|-----------|
| GET    | /auth/login     | Formulario login  | Nao       |
| POST   | /auth/login     | Processar login   | Nao       |
| GET    | /auth/logout    | Logout            | Sim       |
| GET    | /auth/register  | Criar conta       | Nao       |
| POST   | /auth/register  | Processar registro| Nao       |

### Dashboard

| Metodo | Rota     | Descricao                           | Protegida |
|--------|----------|-------------------------------------|-----------|
| GET    | /        | Resumo: ultimos logs, stats basicas | Sim       |

### Prompts (CRUD)

| Metodo | Rota               | Descricao                | Protegida |
|--------|--------------------|--------------------------|-----------|
| GET    | /prompts           | Listar prompts           | Sim       |
| GET    | /prompts/create    | Formulario novo prompt   | Sim       |
| POST   | /prompts/create    | Salvar novo prompt       | Sim       |
| GET    | /prompts/<id>/edit | Formulario editar prompt | Sim       |
| POST   | /prompts/<id>/edit | Salvar edicao            | Sim       |
| POST   | /prompts/<id>/delete| Deletar prompt          | Sim       |
| POST   | /prompts/<id>/run  | Executar agora           | Sim       |

### Schedules (Agendamentos)

| Metodo | Rota                  | Descricao                   | Protegida |
|--------|-----------------------|-----------------------------|-----------|
| GET    | /schedules            | Listar agendamentos         | Sim       |
| GET    | /schedules/create     | Formulario novo agendamento | Sim       |
| POST   | /schedules/create     | Salvar novo agendamento     | Sim       |
| GET    | /schedules/<id>/edit  | Formulario editar           | Sim       |
| POST   | /schedules/<id>/edit  | Salvar edicao               | Sim       |
| POST   | /schedules/<id>/delete| Deletar agendamento         | Sim       |
| POST   | /schedules/<id>/toggle| Ativar/desativar            | Sim       |

### Logs

| Metodo | Rota                         | Descricao                | Protegida |
|--------|------------------------------|--------------------------|-----------|
| GET    | /logs                        | Listar logs de execucao  | Sim       |
| GET    | /logs?schedule_id=<id>       | Filtrar por agendamento  | Sim       |

### Cron (Admin)

| Metodo | Rota          | Descricao                 | Protegida |
|--------|---------------|---------------------------|-----------|
| POST   | /cron/sync    | Sincronizar crontab       | Sim       |
| GET    | /cron/status  | Status atual do crontab   | Sim       |

---

## Design da Interface

### Pagina de Login
- Campo usuario
- Campo senha
- Botao "Entrar"
- Link "Criar conta" (primeiro acesso)

### Dashboard
- Cards com numeros: total prompts ativos, total agendamentos ativos, execucoes hoje, taxa de sucesso
- Lista das ultimas 5 execucoes (tabela compacta)
- Menu lateral: Dashboard, Prompts, Agendamentos, Logs, Configuracoes

### Lista de Prompts
- Tabela com colunas: Titulo, Formato, Ativo, Acoes
- Filtro por ativo/inativo
- Botoes: Novo Prompt, Executar Agora (icone play), Editar, Deletar

### Formulario de Prompt (Create/Edit)
- Campo: Titulo (text)
- Campo: Conteudo do Prompt (textarea grande, ~10 linhas)
- Campo: Tom/Estilo (select: infografico, resumo, analise, newsletter)
- Campo: Formato saida (select: html - fixo por enquanto)
- Botao: Salvar

### Lista de Agendamentos
- Tabela com colunas: Prompt (titulo), Descricao, Cron, Email, Ativo, Ultima Exec, Acoes
- Toggle para ativar/desativar com um clique
- Botoes: Novo Agendamento, Editar, Deletar, Sincronizar Cron

### Formulario de Agendamento (Create/Edit)
- Select: Prompt (dropdown com prompts ativos)
- Campo: Descricao legivel (ex: "Toda quarta 8AM - Noticias financeiras")
- **Construtor de Cron Visual**:
  - Minuto (0-59)
  - Hora (0-23)
  - Dia do mes (* ou 1-31)
  - Mes (* ou 1-12)
  - Dia da semana (* ou 0-6, onde 0=Domingo)
  - Preview da expressao cron final + descricao em portugues
- Campo: Email destino
- Botao: Salvar

### Lista de Logs
- Tabela: Data/Hora, Prompt, Status (badge verde/vermelho), Duracao, Disparado por
- Filtros: por status, por agendamento, por periodo (ultimos 7/30 dias)

### Status do Cron
- Mostrar entradas atuais do crontab relacionadas ao app
- Botao "Sincronizar Cron" (reescreve entradas baseado nos schedules ativos)

---

## CSS / Estilo

- Tema escuro (dark mode) por padrao, com toggle para claro
- CSS minimalista inspirado em terminais (fonte monospace em alguns elementos)
- Cores: fundo #1a1a2e, cards #16213e, accent #0f3460, texto #e0e0e0
- Responsivo (funciona bem em desktop, ok em mobile)
- Sem dependencias externas de CSS (sem Bootstrap, Tailwind, etc.)
