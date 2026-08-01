import os
import logging

logger = logging.getLogger(__name__)

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_SCRIPT = os.path.join(APP_DIR, "scripts", "run_executor.sh")
COMMENT_MARKER = "AI_SCHEDULER"


def _is_docker():
    if os.environ.get("CRON_MODE", "").lower() == "docker":
        return True
    return not os.path.exists("/usr/bin/crontab")


def _get_cron():
    if _is_docker():
        raise RuntimeError("Docker mode: crontab not available")
    from crontab import CronTab
    try:
        return CronTab(user=True)
    except Exception as e:
        raise RuntimeError(f"Nao foi possivel acessar o crontab: {e}")


def _build_comment(schedule_id, description=""):
    return f"{COMMENT_MARKER}:{schedule_id} | {description}"


def add_cron_job(schedule_id, cron_expr, description=""):
    if _is_docker():
        return True
    from crontab import CronTab
    cron = _get_cron()
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expressao cron invalida: {cron_expr}")

    for job in cron:
        if job.comment.startswith(f"{COMMENT_MARKER}:{schedule_id}"):
            cron.remove(job)
            break

    job = cron.new(
        command=f"{RUN_SCRIPT} {schedule_id}",
        comment=_build_comment(schedule_id, description)
    )
    job.setall(*parts)
    cron.write()
    return True


def remove_cron_job(schedule_id):
    if _is_docker():
        return True
    cron = _get_cron()
    for job in cron:
        if job.comment.startswith(f"{COMMENT_MARKER}:{schedule_id}"):
            cron.remove(job)
            cron.write()
            return True
    return False


def update_cron_job(schedule_id, cron_expr):
    if _is_docker():
        return True
    remove_cron_job(schedule_id)
    return add_cron_job(schedule_id, cron_expr)


def sync_all_schedules():
    from app.models import Schedule

    if _is_docker():
        active = Schedule.get_active_schedules()
        logger.info("Docker mode: %d schedules ativos encontrados", len(active))
        return {"added": 0, "removed": 0, "errors": [], "docker_mode": True,
                "active_count": len(active)}

    from crontab import CronTab
    cron = _get_cron()

    existing = {}
    for job in cron:
        if job.comment.startswith(f"{COMMENT_MARKER}:"):
            sid = int(job.comment.split(":")[1].split(" ")[0].split("|")[0].strip())
            existing[sid] = job

    active_schedules = Schedule.get_active_schedules()
    active_ids = set()
    result = {"added": 0, "removed": 0, "errors": []}

    for s in active_schedules:
        active_ids.add(s["id"])
        parts = s["cron_expr"].strip().split()
        if s["id"] in existing:
            job = existing[s["id"]]
            job.setall(*parts)
            job.comment = _build_comment(s["id"], s["description"])
        else:
            try:
                job = cron.new(
                    command=f"{RUN_SCRIPT} {s['id']}",
                    comment=_build_comment(s["id"], s["description"])
                )
                job.setall(*parts)
                result["added"] += 1
            except Exception as e:
                result["errors"].append(f"Sched {s['id']}: {e}")

    for sid, job in existing.items():
        if sid not in active_ids:
            cron.remove(job)
            result["removed"] += 1

    cron.write()
    return result


def get_cron_status():
    if _is_docker():
        from app.models import Schedule
        active = Schedule.get_active_schedules()
        return [{
            "comment": f"AI_SCHEDULER:{s['id']} | {s['description']}",
            "schedule": s["cron_expr"],
            "command": f"/app/scripts/run_cron.sh {s['id']}",
            "enabled": True,
            "docker_mode": True,
        } for s in active]

    from crontab import CronTab
    cron = _get_cron()
    entries = []
    for job in cron:
        if job.comment.startswith(f"{COMMENT_MARKER}:"):
            entries.append({
                "comment": job.comment,
                "schedule": str(job.slices),
                "command": job.command,
                "enabled": job.enabled,
            })
    return entries


def clear_all_app_entries():
    if _is_docker():
        return 0
    cron = _get_cron()
    to_remove = [j for j in cron if j.comment.startswith(f"{COMMENT_MARKER}:")]
    for job in to_remove:
        cron.remove(job)
    cron.write()
    return len(to_remove)
