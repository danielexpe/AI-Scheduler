from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Prompt, Schedule, ExecutionLog, query
from app.executor import run_schedule

routes_bp = Blueprint("routes", __name__)


@routes_bp.route("/")
@login_required
def dashboard():
    stats = ExecutionLog.get_stats()
    recent_logs = ExecutionLog.get_recent(limit=5)
    return render_template("dashboard.html", stats=stats, logs=recent_logs)


# --- Prompts ---

@routes_bp.route("/prompts")
@login_required
def prompts_list():
    prompts = Prompt.get_all()
    return render_template("prompts/list.html", prompts=prompts)


@routes_bp.route("/prompts/create", methods=["GET", "POST"])
@login_required
def prompts_create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        tone = request.form.get("tone", "infografico")
        fmt = request.form.get("format", "html")

        if not title or not content:
            flash("Título e conteúdo são obrigatórios.", "error")
        else:
            Prompt.create(title, content, tone, fmt)
            flash("Prompt criado com sucesso.", "success")
            return redirect(url_for("routes.prompts_list"))

    return render_template("prompts/create.html")


@routes_bp.route("/prompts/<int:prompt_id>/edit", methods=["GET", "POST"])
@login_required
def prompts_edit(prompt_id):
    prompt = Prompt.get_by_id(prompt_id)
    if not prompt:
        flash("Prompt não encontrado.", "error")
        return redirect(url_for("routes.prompts_list"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        tone = request.form.get("tone", "infografico")
        fmt = request.form.get("format", "html")
        active = 1 if request.form.get("active") == "1" else 0

        if not title or not content:
            flash("Título e conteúdo são obrigatórios.", "error")
        else:
            Prompt.update(prompt_id, title, content, tone, fmt, active)
            flash("Prompt atualizado com sucesso.", "success")
            return redirect(url_for("routes.prompts_list"))

    return render_template("prompts/edit.html", prompt=prompt)


@routes_bp.route("/prompts/<int:prompt_id>/delete", methods=["POST"])
@login_required
def prompts_delete(prompt_id):
    Prompt.delete(prompt_id)
    flash("Prompt deletado.", "info")
    return redirect(url_for("routes.prompts_list"))


@routes_bp.route("/prompts/<int:prompt_id>/run", methods=["POST"])
@login_required
def prompts_run(prompt_id):
    prompt = Prompt.get_by_id(prompt_id)
    if not prompt:
        flash("Prompt não encontrado.", "error")
        return redirect(url_for("routes.prompts_list"))

    email_to = request.form.get("email_to", "").strip()
    if not email_to:
        flash("Informe um email de destino.", "error")
        return redirect(url_for("routes.prompts_list"))

    duration, result_html, error = run_schedule(None, prompt_id, email_to, prompt["content"], prompt["tone"])
    ExecutionLog.create(
        schedule_id=0,
        status="success" if result_html else "error",
        error_message=error,
        duration_ms=duration,
        triggered_by="manual"
    )

    if result_html:
        flash("Execução concluída. Verifique seu email.", "success")
    else:
        flash(f"Erro na execução: {error}", "error")

    return redirect(url_for("routes.prompts_list"))


# --- Schedules ---

@routes_bp.route("/schedules")
@login_required
def schedules_list():
    schedules = Schedule.get_all()
    return render_template("schedules/list.html", schedules=schedules)


@routes_bp.route("/schedules/create", methods=["GET", "POST"])
@login_required
def schedules_create():
    prompts = Prompt.get_active()
    if request.method == "POST":
        prompt_id = int(request.form.get("prompt_id", 0))
        description = request.form.get("description", "").strip()
        minute = request.form.get("minute", "*")
        hour = request.form.get("hour", "*")
        day = request.form.get("day", "*")
        month = request.form.get("month", "*")
        weekday = request.form.get("weekday", "*")
        email_to = request.form.get("email_to", "").strip()

        cron_expr = f"{minute} {hour} {day} {month} {weekday}"

        if not prompt_id or not email_to or not description:
            flash("Prompt, email e descrição são obrigatórios.", "error")
        else:
            sid = Schedule.create(prompt_id, cron_expr, description, email_to)
            try:
                from app.cron_manager import add_cron_job
                add_cron_job(sid, cron_expr, description)
            except Exception as e:
                flash(f"Agendamento salvo, mas erro ao atualizar crontab: {e}", "warning")
                return redirect(url_for("routes.schedules_list"))
            flash("Agendamento criado com sucesso.", "success")
            return redirect(url_for("routes.schedules_list"))

    return render_template("schedules/create.html", prompts=prompts)


@routes_bp.route("/schedules/<int:schedule_id>/edit", methods=["GET", "POST"])
@login_required
def schedules_edit(schedule_id):
    schedule = Schedule.get_by_id(schedule_id)
    if not schedule:
        flash("Agendamento não encontrado.", "error")
        return redirect(url_for("routes.schedules_list"))

    prompts = Prompt.get_active()

    if request.method == "POST":
        prompt_id = int(request.form.get("prompt_id", 0))
        description = request.form.get("description", "").strip()
        email_to = request.form.get("email_to", "").strip()
        active = 1 if request.form.get("active") == "1" else 0

        parts = schedule["cron_expr"].split()
        minute = request.form.get("minute", parts[0] if len(parts) > 0 else "*")
        hour = request.form.get("hour", parts[1] if len(parts) > 1 else "*")
        day = request.form.get("day", parts[2] if len(parts) > 2 else "*")
        month = request.form.get("month", parts[3] if len(parts) > 3 else "*")
        weekday = request.form.get("weekday", parts[4] if len(parts) > 4 else "*")
        cron_expr = f"{minute} {hour} {day} {month} {weekday}"

        if not prompt_id or not email_to:
            flash("Prompt e email são obrigatórios.", "error")
        else:
            Schedule.update(schedule_id, prompt_id, cron_expr, description, email_to, active)
            try:
                from app.cron_manager import update_cron_job
                update_cron_job(schedule_id, cron_expr)
            except Exception as e:
                flash(f"Agendamento salvo, mas erro ao atualizar crontab: {e}", "warning")
                return redirect(url_for("routes.schedules_list"))
            flash("Agendamento atualizado com sucesso.", "success")
            return redirect(url_for("routes.schedules_list"))

    return render_template("schedules/edit.html", schedule=schedule, prompts=prompts)


@routes_bp.route("/schedules/<int:schedule_id>/delete", methods=["POST"])
@login_required
def schedules_delete(schedule_id):
    Schedule.delete(schedule_id)
    try:
        from app.cron_manager import remove_cron_job
        remove_cron_job(schedule_id)
    except Exception:
        pass
    flash("Agendamento deletado.", "info")
    return redirect(url_for("routes.schedules_list"))


@routes_bp.route("/schedules/<int:schedule_id>/toggle", methods=["POST"])
@login_required
def schedules_toggle(schedule_id):
    Schedule.toggle(schedule_id)
    schedule = Schedule.get_by_id(schedule_id)
    try:
        from app.cron_manager import sync_all_schedules
        sync_all_schedules()
    except Exception:
        pass
    flash("Status do agendamento alterado.", "info")
    return redirect(url_for("routes.schedules_list"))


# --- Logs ---

@routes_bp.route("/logs")
@login_required
def logs_list():
    schedule_id = request.args.get("schedule_id", type=int)
    logs = ExecutionLog.get_recent(limit=50, schedule_id=schedule_id)
    return render_template("logs/list.html", logs=logs)


# --- Cron ---

@routes_bp.route("/cron/sync", methods=["POST"])
@login_required
def cron_sync():
    try:
        from app.cron_manager import sync_all_schedules, _is_docker
        result = sync_all_schedules()
        if _is_docker():
            flash(f"Cron gerenciado pelo supercronic. {result.get('active_count', 0)} schedules ativos.", "info")
        else:
            flash(f"Cron sincronizado: {result['added']} adicionados, {result['removed']} removidos.", "success")
    except Exception as e:
        flash(f"Erro ao sincronizar cron: {e}", "error")
    return redirect(url_for("routes.schedules_list"))


@routes_bp.route("/cron/status")
@login_required
def cron_status():
    try:
        from app.cron_manager import get_cron_status
        entries = get_cron_status()
    except Exception:
        entries = []
    return render_template("cron_status.html", entries=entries)
