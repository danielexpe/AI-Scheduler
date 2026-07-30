from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, UserModel

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.get_by_username(username)
        if user and check_password_hash(user["password"], password):
            login_user(UserModel(user), remember=True)
            flash("Login realizado com sucesso.", "success")
            return redirect(url_for("routes.dashboard"))

        flash("Usuário ou senha inválidos.", "error")

    return render_template("login.html", register=False)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        if not username or not password:
            flash("Preencha todos os campos.", "error")
        elif len(password) < 4:
            flash("A senha deve ter pelo menos 4 caracteres.", "error")
        elif password != confirm:
            flash("As senhas não conferem.", "error")
        elif User.get_by_username(username):
            flash("Usuário já existe.", "error")
        else:
            User.create(username, generate_password_hash(password))
            flash("Conta criada com sucesso. Faça login.", "success")
            return redirect(url_for("auth.login"))

    return render_template("login.html", register=True)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout realizado.", "info")
    return redirect(url_for("auth.login"))
