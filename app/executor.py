import os
import sys
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models import Schedule, ExecutionLog
from app.deepseek_client import call_deepseek
from app.email_sender import send_email

logger = logging.getLogger(__name__)


def run_schedule(schedule_id=None, prompt_id_override=None, email_to=None,
                 prompt_content=None, prompt_tone="infografico"):
    started = time.time()
    logger.info("run_schedule iniciado schedule_id=%s tone=%s", schedule_id, prompt_tone)

    if schedule_id:
        schedule = Schedule.get_by_id(schedule_id)
        if not schedule:
            duration = int((time.time() - started) * 1000)
            logger.error("Agendamento %s nao encontrado", schedule_id)
            return duration, None, "Agendamento não encontrado"

        prompt_content = schedule["prompt_content"]
        prompt_tone = schedule["prompt_tone"]
        email_to = schedule["email_to"]
        logger.info("Schedule carregado: email_to=%s prompt=%s...",
                     email_to, prompt_content[:80] if prompt_content else "")

    logger.info("Chamando DeepSeek API (search=True)...")
    result_html, error = call_deepseek(prompt_content, tone=prompt_tone, enable_search=True)
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

    subject = f"[Scheduler] {prompt_content[:60]} - {datetime.now().strftime('%d/%m/%Y')}"

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
