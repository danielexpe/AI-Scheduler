from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import Schedule
from app.executor import run_schedule
import logging

tasks_bp = Blueprint("tasks", __name__)
logger = logging.getLogger(__name__)


@tasks_bp.route("/tasks")
@login_required
def tasks_list():
    tasks = Schedule.get_tasks()
    return render_template("tasks/list.html", tasks=tasks)


@tasks_bp.route("/tasks/create", methods=["GET", "POST"])
@login_required
def tasks_create():
    if request.method == "POST":
        task_type = request.form.get("task_type", "static")
        description = request.form.get("description", "").strip()
        email_to = request.form.get("email_to", "").strip()

        minute = request.form.get("minute", "*")
        hour = request.form.get("hour", "*")
        day = request.form.get("day", "*")
        month = request.form.get("month", "*")
        weekday = request.form.get("weekday", "*")
        cron_expr = f"{minute} {hour} {day} {month} {weekday}"

        if not email_to or not description:
            flash("Descricao e email sao obrigatorios.", "error")
            return render_template("tasks/create.html")

        static_content = None
        static_is_html = 0
        static_subject = None
        command_text = None

        if task_type == "static":
            static_content = request.form.get("static_content", "").strip()
            static_is_html = 1 if request.form.get("static_is_html") == "1" else 0
            static_subject = request.form.get("static_subject", "").strip() or description
            if not static_content:
                flash("Conteudo e obrigatorio para tarefa estatica.", "error")
                return render_template("tasks/create.html")
        elif task_type == "command":
            command_text = request.form.get("command_text", "").strip()
            if not command_text:
                flash("Comando e obrigatorio para tarefa de comando.", "error")
                return render_template("tasks/create.html")

        sid = Schedule.create(
            prompt_id=None, cron_expr=cron_expr, description=description,
            email_to=email_to, schedule_type=task_type,
            static_content=static_content, static_is_html=static_is_html,
            static_subject=static_subject, command_text=command_text,
        )
        logger.info("Tarefa criada: id=%d type=%s cron='%s' email=%s",
                     sid, task_type, cron_expr, email_to)

        try:
            from app.cron_manager import add_cron_job
            add_cron_job(sid, cron_expr, description)
        except Exception as e:
            flash(f"Tarefa salva, mas erro ao atualizar crontab: {e}", "warning")
            return redirect(url_for("tasks.tasks_list"))

        flash("Tarefa criada com sucesso.", "success")
        return redirect(url_for("tasks.tasks_list"))

    return render_template("tasks/create.html")


@tasks_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def tasks_edit(task_id):
    task = Schedule.get_by_id(task_id)
    if not task:
        flash("Tarefa nao encontrada.", "error")
        return redirect(url_for("tasks.tasks_list"))

    if request.method == "POST":
        task_type = request.form.get("task_type", task["schedule_type"] or "static")
        description = request.form.get("description", "").strip()
        email_to = request.form.get("email_to", "").strip()
        active = 1 if request.form.get("active") == "1" else 0

        parts = (task["cron_expr"] or "* * * * *").split()
        minute = request.form.get("minute", parts[0] if len(parts) > 0 else "*")
        hour = request.form.get("hour", parts[1] if len(parts) > 1 else "*")
        day = request.form.get("day", parts[2] if len(parts) > 2 else "*")
        month = request.form.get("month", parts[3] if len(parts) > 3 else "*")
        weekday = request.form.get("weekday", parts[4] if len(parts) > 4 else "*")
        cron_expr = f"{minute} {hour} {day} {month} {weekday}"

        if not email_to:
            flash("Email e obrigatorio.", "error")
            return render_template("tasks/edit.html", task=task)

        static_content = task.get("static_content")
        static_is_html = task.get("static_is_html") or 0
        static_subject = task.get("static_subject")
        command_text = task.get("command_text")

        if task_type == "static":
            static_content = request.form.get("static_content", "").strip()
            static_is_html = 1 if request.form.get("static_is_html") == "1" else 0
            static_subject = request.form.get("static_subject", "").strip() or description
        elif task_type == "command":
            command_text = request.form.get("command_text", "").strip()

        Schedule.update(
            schedule_id=task_id, prompt_id=task["prompt_id"],
            cron_expr=cron_expr, description=description, email_to=email_to,
            active=active, schedule_type=task_type,
            static_content=static_content, static_is_html=static_is_html,
            static_subject=static_subject, command_text=command_text,
        )
        logger.info("Tarefa atualizada: id=%d type=%s", task_id, task_type)

        try:
            from app.cron_manager import update_cron_job
            update_cron_job(task_id, cron_expr)
        except Exception as e:
            flash(f"Tarefa salva, mas erro ao atualizar crontab: {e}", "warning")
            return redirect(url_for("tasks.tasks_list"))

        flash("Tarefa atualizada com sucesso.", "success")
        return redirect(url_for("tasks.tasks_list"))

    return render_template("tasks/edit.html", task=task)


@tasks_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def tasks_delete(task_id):
    Schedule.delete(task_id)
    try:
        from app.cron_manager import remove_cron_job
        remove_cron_job(task_id)
    except Exception:
        pass
    logger.info("Tarefa deletada: id=%d", task_id)
    flash("Tarefa deletada.", "info")
    return redirect(url_for("tasks.tasks_list"))


@tasks_bp.route("/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def tasks_toggle(task_id):
    Schedule.toggle(task_id)
    try:
        from app.cron_manager import sync_all_schedules
        sync_all_schedules()
    except Exception:
        pass
    flash("Status da tarefa alterado.", "info")
    return redirect(url_for("tasks.tasks_list"))


@tasks_bp.route("/tasks/<int:task_id>/run", methods=["POST"])
@login_required
def tasks_run(task_id):
    duration, result_html, error = run_schedule(schedule_id=task_id)
    if result_html:
        flash("Tarefa executada. Verifique seu email.", "success")
    else:
        flash(f"Erro: {error}", "error")
    return redirect(url_for("tasks.tasks_list"))
