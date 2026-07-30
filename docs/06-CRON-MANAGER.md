# Gerenciador de Cron

## Estrategia

O app mantem as entradas de cron sincronizadas com a tabela `schedules` do banco.
Cada schedule ativo vira uma linha no crontab do usuario Linux.

---

## Biblioteca: `python-crontab`

- Instalacao: `pip install python-crontab`
- Permite ler, adicionar, remover entradas do crontab do usuario
- Nao requer permissoes root
- Usa `crontab -l` e `crontab -` por baixo

---

## Identificacao das Entradas

Cada entrada de cron do app sera identificada por um comentario unico:
```
# AI_SCHEDULER:{schedule_id}
```

Isso permite:
- Remover entradas especificas sem afetar outras
- Saber quais entradas pertencem ao app
- Evitar duplicatas ao sincronizar

---

## Formato da Entrada no Crontab

```
# AI_SCHEDULER:{schedule_id} | {description}
{minuto} {hora} {dia_mes} {mes} {dia_semana} /caminho/scripts/run_executor.sh {schedule_id}
```

Exemplo:
```
# AI_SCHEDULER:3 | Toda quarta 8AM - Noticias financeiras
0 8 * * 3 /home/daniel/myDev/openCode/scripts/run_executor.sh 3
```

---

## Funcoes Planejadas

```python
# assinaturas planejadas
def add_cron_job(schedule_id: int, cron_expr: str, description: str) -> bool:
    """Adiciona uma entrada no crontab"""

def remove_cron_job(schedule_id: int) -> bool:
    """Remove entrada do crontab pelo schedule_id"""

def update_cron_job(schedule_id: int, cron_expr: str) -> bool:
    """Atualiza entrada existente"""

def sync_all_schedules() -> dict:
    """
    Sincroniza todos os schedules ativos do banco com o crontab.
    Remove entradas de schedules inativos/deletados.
    Retorna: {"added": N, "removed": N, "errors": [...]}
    """

def get_cron_status() -> list:
    """Lista todas as entradas de cron do app atualmente no crontab"""

def clear_all_app_entries():
    """Remove TODAS as entradas do app do crontab (para desinstalar)"""
```

---

## Script `scripts/run_executor.sh`

```bash
#!/bin/bash
# Chamado pelo cron a cada execucao agendada
# Argumento: $1 = schedule_id

set -e

APP_DIR="/home/daniel/myDev/openCode"
VENV_PYTHON="$APP_DIR/venv/bin/python"  # se usar venv
EXECUTOR="$APP_DIR/app/executor.py"
LOG_FILE="$APP_DIR/data/executor.log"

SCHEDULE_ID=$1

if [ -z "$SCHEDULE_ID" ]; then
    echo "[$(date)] ERRO: schedule_id nao informado" >> "$LOG_FILE"
    exit 1
fi

echo "[$(date)] Iniciando execucao do schedule_id=$SCHEDULE_ID" >> "$LOG_FILE"

$VENV_PYTHON "$EXECUTOR" --schedule-id "$SCHEDULE_ID" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Execucao concluida com sucesso" >> "$LOG_FILE"
else
    echo "[$(date)] Execucao falhou com codigo $EXIT_CODE" >> "$LOG_FILE"
fi

exit $EXIT_CODE
```

---

## Script `scripts/setup_cron.sh`

```bash
#!/bin/bash
# Configura/atualiza todas as entradas de cron
# Pode ser chamado manualmente ou via interface web

APP_DIR="/home/daniel/myDev/openCode"
VENV_PYTHON="$APP_DIR/venv/bin/python"

cd "$APP_DIR"
$VENV_PYTHON -c "from app.cron_manager import sync_all_schedules; print(sync_all_schedules())"
```

---

## Fluxo de Sincronizacao

1. Usuario cria/edita/deleta um agendamento na interface web
2. Flag `needs_sync = True` (em memoria ou arquivo)
3. Usuario clica "Sincronizar Cron" OU o sistema sincroniza automaticamente
4. `sync_all_schedules()`:
   a. Le todos os schedules ativos do banco
   b. Le todas as entradas do crontab com marcador `AI_SCHEDULER:`
   c. Remove entradas que nao estao mais ativas no banco
   d. Adiciona/atualiza entradas para schedules ativos
   e. Aplica o novo crontab
5. Confirma ao usuario quantas entradas foram adicionadas/removidas

---

## Validacao de Expressao Cron

Antes de salvar, validar os 5 campos da expressao cron:

```python
import re

def validate_cron_expr(expr: str) -> bool:
    """Valida formato basico de expressao cron (5 campos)"""
    parts = expr.strip().split()
    if len(parts) != 5:
        return False

    valid_pattern = r'^(\*|\d+(-\d+)?(/\d+)?)(,\*|\d+(-\d+)?(/\d+)?)*$'
    return all(re.match(valid_pattern, p) for p in parts)
```

---

## Precaucoes

- **NUNCA** limpar o crontab inteiro (`cron.write()` sem antes ler)
- Sempre fazer backup do crontab atual antes de modificar
- Logar todas as operacoes de modificacao do crontab
- No `sync_all_schedules`, somente remover entradas com o marcador `AI_SCHEDULER:`
- Verificar se o usuario tem permissao para usar crontab (`crontab -l` precisa funcionar)

---

## Debug

```bash
# Ver entradas atuais do crontab
crontab -l

# Ver logs de execucao
tail -f /home/daniel/myDev/openCode/data/executor.log

# Testar executor manualmente
/home/daniel/myDev/openCode/scripts/run_executor.sh 1
```
