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

    if schedule_id:
        schedule = Schedule.get_by_id(schedule_id)
        if not schedule:
            duration = int((time.time() - started) * 1000)
            return duration, None, "Agendamento não encontrado"

        prompt_content = schedule["prompt_content"]
        prompt_tone = schedule["prompt_tone"]
        email_to = schedule["email_to"]

    result_html, error = call_deepseek(prompt_content, tone=prompt_tone, enable_search=True)
    duration = int((time.time() - started) * 1000)

    if error:
        if schedule_id:
            ExecutionLog.create(schedule_id, "error", error, duration, "cron")
            try:
                send_email(email_to,
                           f"[Scheduler] Erro na execução - {datetime.now().strftime('%d/%m/%Y')}",
                           f"<p>Erro ao gerar conteúdo: {error}</p>")
            except Exception:
                pass
        return duration, None, error

    if not result_html or len(result_html.strip()) < 50:
        error = "Resposta vazia ou muito curta do DeepSeek"
        if schedule_id:
            ExecutionLog.create(schedule_id, "error", error, duration, "cron")
        return duration, None, error

    subject = f"[Scheduler] {prompt_content[:60]} - {datetime.now().strftime('%d/%m/%Y')}"

    success, email_error = send_email(email_to, subject, result_html)
    if not success:
        if schedule_id:
            ExecutionLog.create(schedule_id, "error", f"Email: {email_error}", duration, "cron")
        return duration, None, f"Falha ao enviar email: {email_error}"

    if schedule_id:
        Schedule.update_last_run(schedule_id)
        ExecutionLog.create(schedule_id, "success", None, duration, "cron")

    return duration, result_html, None


if __name__ == "__main__":
    import argparse

    from app import create_app

    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule-id", type=int, required=True)
    args = parser.parse_args()

    app = create_app()

    logging.basicConfig(level=logging.INFO)
    print(f"Iniciando execução do schedule_id={args.schedule_id}")

    with app.app_context():
        duration, result, error = run_schedule(schedule_id=args.schedule_id)

    if error:
        print(f"Erro: {error}")
        sys.exit(1)
    print(f"Sucesso! Duração: {duration}ms")
