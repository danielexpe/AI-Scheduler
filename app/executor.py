import os
import sys
import time
import re
import logging
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models import Schedule, ExecutionLog, Prompt
from app.deepseek_client import call_deepseek
from app.email_sender import send_email

logger = logging.getLogger(__name__)

EMAIL_WRAPPER_SIMPLE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background-color:#1a1a2e;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#1a1a2e;"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0">
<tr><td style="padding:20px;text-align:center;background-color:#16213e;">
<h1 style="color:#e94560;margin:0;font-size:24px;">AI Mail Scheduler</h1>
<p style="color:#a0a0b0;margin:5px 0 0 0;font-size:12px;">Gerado em {date}</p>
</td></tr>
<tr><td style="padding:20px;background-color:#0f3460;color:#e0e0e0;">
{body}
</td></tr>
<tr><td style="padding:15px;text-align:center;background-color:#16213e;">
<p style="color:#a0a0b0;font-size:11px;margin:0;">Email automatico pelo AI Mail Scheduler.</p>
</td></tr>
</table></td></tr></table></body></html>"""


def _run_static_task(schedule):
    started = time.time()
    content = schedule["static_content"] or ""
    is_html = schedule["static_is_html"]
    subject = schedule["static_subject"] or schedule["description"] or "Tarefa"

    if not is_html:
        body = content.replace("\n", "<br>\n")
    else:
        body = content

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    wrapped = EMAIL_WRAPPER_SIMPLE.format(date=now, body=body)

    duration = int((time.time() - started) * 1000)
    success, email_error = send_email(schedule["email_to"], subject, wrapped)
    if not success:
        logger.error("Static task falhou: %s", email_error)
        ExecutionLog.create(schedule["id"], "error", f"Email: {email_error}", duration, "cron")
        return duration, None, f"Falha ao enviar email: {email_error}"

    logger.info("Static task OK: %d chars em %dms", len(body), duration)
    return duration, wrapped, None


def _run_command_task(schedule):
    started = time.time()
    cmd = schedule["command_text"] or ""
    logger.info("Executando comando: %s", cmd[:80])

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
    except subprocess.TimeoutExpired:
        duration = int((time.time() - started) * 1000)
        error = f"Comando excedeu timeout de 30s: {cmd[:60]}"
        logger.error(error)
        ExecutionLog.create(schedule["id"], "error", error, duration, "cron")
        return duration, None, error
    except Exception as e:
        duration = int((time.time() - started) * 1000)
        error = f"Erro ao executar comando: {e}"
        logger.error(error)
        ExecutionLog.create(schedule["id"], "error", error, duration, "cron")
        return duration, None, error

    duration = int((time.time() - started) * 1000)
    stdout = result.stdout or ""
    stderr = result.stderr or ""

    body_parts = [f"<p><strong>Comando:</strong> <code>{cmd}</code></p>",
                  f"<p><strong>Exit code:</strong> {result.returncode}</p>"]
    if stdout:
        body_parts.append(f"<h3>STDOUT</h3><pre style='background:#1a1a2e;color:#0f0;padding:10px;overflow-x:auto;'>{stdout}</pre>")
    if stderr:
        body_parts.append(f"<h3>STDERR</h3><pre style='background:#1a1a2e;color:#e94560;padding:10px;overflow-x:auto;'>{stderr}</pre>")

    body = "\n".join(body_parts)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    wrapped = EMAIL_WRAPPER_SIMPLE.format(date=now, body=body)

    subject = f"[Scheduler] Comando: {cmd[:60]}"
    status = "success" if result.returncode == 0 else "warning"
    success, email_error = send_email(schedule["email_to"], subject, wrapped)
    if not success:
        logger.error("Command task falhou no email: %s", email_error)
        ExecutionLog.create(schedule["id"], "error", f"Email: {email_error}", duration, "cron")
        return duration, None, f"Falha ao enviar email: {email_error}"

    logger.info("Command task OK: exit=%d %d chars em %dms", result.returncode, len(body), duration)
    ExecutionLog.create(schedule["id"], status, None, duration, "cron")
    Schedule.update_last_run(schedule["id"])
    return duration, wrapped, None


def _build_debug_section(system_prompt, user_prompt, model, tone,
                          search_info, duration_ms):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    debug_html = f"""<hr>
<pre>
=== DEBUG - Trilha do Prompt ===

Modelo: {model}
Tom/Estilo: {tone}
Busca Web: {search_info}
Modo Debug: Ativado
Duracao: {duration_ms}ms
Timestamp: {timestamp}

--- System Prompt ({len(system_prompt)} caracteres) ---
{system_prompt}

--- User Prompt ({len(user_prompt)} caracteres) ---
{user_prompt}

=== FIM DEBUG ===
</pre>"""
    return debug_html


def run_schedule(schedule_id=None, prompt_id_override=None, email_to=None,
                 prompt_content=None, prompt_tone="infografico"):
    started = time.time()

    if schedule_id:
        schedule = Schedule.get_by_id(schedule_id)
        if not schedule:
            duration = int((time.time() - started) * 1000)
            logger.error("Agendamento %s nao encontrado", schedule_id)
            return duration, None, "Agendamento não encontrado"

        sched_type = schedule["schedule_type"] or "ai"
        logger.info("run_schedule iniciado schedule_id=%s type=%s", schedule_id, sched_type)

        if sched_type == "static":
            return _run_static_task(schedule)

        if sched_type == "command":
            return _run_command_task(schedule)

        prompt_content = schedule["prompt_content"]
        prompt_tone = schedule["prompt_tone"]
        prompt_title = schedule["prompt_title"] or prompt_content[:80]
        email_to = schedule["email_to"]
    else:
        prompt_title = prompt_content[:80] if prompt_content else "Execucao Manual"
        logger.info("run_schedule iniciado manual tone=%s", prompt_tone)

    logger.info("Chamando DeepSeek API (search=True)...")

    enable_search = True
    search_max_results = 5
    debug_mode = False
    if schedule_id and schedule:
        enable_search = bool(schedule["enable_search"]) if schedule["enable_search"] is not None else True
        search_max_results = schedule["search_max_results"] or 5
        debug_mode = bool(schedule["debug_mode"]) if schedule["debug_mode"] is not None else False
    elif prompt_id_override:
        prompt_row = Prompt.get_by_id(prompt_id_override)
        if prompt_row:
            enable_search = bool(prompt_row["enable_search"]) if prompt_row["enable_search"] is not None else True
            search_max_results = prompt_row["search_max_results"] or 5
            debug_mode = bool(prompt_row["debug_mode"]) if prompt_row["debug_mode"] is not None else False
            if not schedule_id:
                prompt_title = prompt_row["title"]

    user_prompt = f"Topico: {prompt_content}\n\nGere o infografico/relatorio em HTML com CSS inline conforme as instrucoes."

    search_used = False
    search_result_count = 0
    if enable_search:
        if schedule_id and schedule:
            search_query = schedule["prompt_title"] or prompt_content
        else:
            search_query = prompt_content
        try:
            from app.search_client import web_search
            context = web_search(search_query, max_results=search_max_results)
            if context:
                user_prompt = context + "\n\n" + user_prompt
                search_used = True
                search_result_count = context.count("Titulo:")
                logger.info("Busca web adicionou %d chars de contexto ao prompt", len(context))
            else:
                logger.warning("Busca web nao retornou resultados, seguindo sem contexto extra")
        except Exception as e:
            logger.warning("Erro na busca web: %s. Seguindo sem contexto extra.", e)

    user_prompt_final = user_prompt

    result_html, error = call_deepseek(user_prompt, tone=prompt_tone, enable_search=enable_search)
    duration = int((time.time() - started) * 1000)

    if error:
        logger.error("DeepSeek falhou: %s (duracao=%dms)", error, duration)
        if schedule_id:
            ExecutionLog.create(schedule_id, "error", error, duration, "cron")
            try:
                logger.info("Enviando email de erro...")
                send_email(email_to,
                           f"[Scheduler] Erro na execução - {datetime.now().strftime('%d/%m/%Y')}",
                           f"<p>Erro ao gerar conteúdo: {error}</p>")
            except Exception as e:
                logger.error("Falha ao enviar email de erro: %s", e)
        return duration, None, error

    if not result_html or len(result_html.strip()) < 50:
        error = "Resposta vazia ou muito curta do DeepSeek"
        logger.error(error)
        if schedule_id:
            ExecutionLog.create(schedule_id, "error", error, duration, "cron")
        return duration, None, error

    logger.info("DeepSeek OK - %d chars em %dms. Enviando email para %s...",
                 len(result_html), duration, email_to)

    if debug_mode and result_html:
        try:
            from app.deepseek_client import SYSTEM_PROMPT_BASE, TONE_INSTRUCTIONS, SEARCH_INSTRUCTION, _get_model

            tone_instruction = TONE_INSTRUCTIONS.get(prompt_tone, TONE_INSTRUCTIONS["infografico"])
            full_system_prompt = SYSTEM_PROMPT_BASE + "\n\nEstilo solicitado: " + tone_instruction
            if enable_search:
                full_system_prompt += "\n\n" + SEARCH_INSTRUCTION

            if search_used:
                search_label = f"Ativada (Tavily/DuckDuckGo, {search_result_count} resultados)"
            elif enable_search:
                search_label = "Ativada (sem resultados)"
            else:
                search_label = "Desativada"

            debug_html = _build_debug_section(
                system_prompt=full_system_prompt,
                user_prompt=user_prompt_final,
                model=_get_model(),
                tone=prompt_tone,
                search_info=search_label,
                duration_ms=duration,
            )

            stripped = re.sub(r'</body>\s*</html>\s*$', '', result_html, flags=re.IGNORECASE)
            body_match = re.search(r'<body[^>]*>', stripped, re.IGNORECASE)
            if body_match:
                stripped = stripped[body_match.end():]
            result_html = stripped + debug_html + '\n</body>\n</html>'
            logger.info("Modo debug: adicionada secao de %d chars ao email", len(debug_html))
        except Exception as e:
            logger.warning("Erro ao gerar secao debug: %s", e)

    subject = f"[Scheduler] {prompt_title[:80]} - {datetime.now().strftime('%d/%m/%Y')}"

    success, email_error = send_email(email_to, subject, result_html)
    if not success:
        logger.error("Falha no envio de email: %s", email_error)
        if schedule_id:
            ExecutionLog.create(schedule_id, "error", f"Email: {email_error}", duration, "cron")
        return duration, None, f"Falha ao enviar email: {email_error}"

    if schedule_id:
        Schedule.update_last_run(schedule_id)
        ExecutionLog.create(schedule_id, "success", None, duration, "cron")

    logger.info("Execucao concluida com sucesso em %dms", duration)
    return duration, result_html, None


if __name__ == "__main__":
    import argparse

    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)

    from app.logger_config import setup_logging, get_logger
    log_path = os.path.join(data_dir, "cron.log")
    setup_logging(log_path)
    cron_logger = get_logger("app.cron")
    cron_logger.info("Executor iniciado via cron (PID=%d)", os.getpid())

    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule-id", type=int, required=True)
    args = parser.parse_args()

    from app import create_app
    app = create_app()

    cron_logger.info("Executando schedule_id=%d", args.schedule_id)

    with app.app_context():
        duration, result, error = run_schedule(schedule_id=args.schedule_id)

    if error:
        cron_logger.error("FALHA schedule_id=%d: %s (duracao=%dms)", args.schedule_id, error, duration)
        sys.exit(1)
    cron_logger.info("SUCESSO schedule_id=%d - duracao=%dms", args.schedule_id, duration)
