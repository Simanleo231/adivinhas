
from flask import (Flask, render_template, request,
                   session, redirect, url_for, flash)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin,
                          login_user, logout_user,
                          login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import random, copy
import unicodedata


def normalizar(texto):
    """Minúsculas, sem espaços nas pontas e sem acentos —
    para comparar respostas de forma justa (ex.: 'mercurio' == 'mercúrio')."""
    texto = texto.lower().strip()
    sem_acentos = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sem_acentos if unicodedata.category(c) != "Mn")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","super-chave-secreta-123")
database_url = os.environ.get("DATABASE_URL")

if database_url:
    # O Render fornece um URL que começa por "postgres://"
    # mas o SQLAlchemy moderno exige "postgresql://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # Sem variável → estamos em local → usar SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///adivinhas.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ─── Configuração do Flask-Login ──────────────────
login_manager = LoginManager(app)
# Rota para onde redirecionar se aceder a página protegida
login_manager.login_view = "login"
login_manager.login_message = "Faz login para continuar."

# ─── Modelo: Utilizador ───────────────────────────
# UserMixin adiciona os métodos que o Flask-Login precisa:
# is_authenticated, is_active, is_anonymous, get_id()
class Utilizador(db.Model, UserMixin):
    id             = db.Column(db.Integer, primary_key=True)
    nome           = db.Column(db.String(50),  nullable=False)
    email          = db.Column(db.String(120), nullable=False, unique=True)
    password_hash  = db.Column(db.String(256), nullable=False)

    # Relação: um utilizador tem muitas pontuações
    pontuacoes = db.relationship("Pontuacao", backref="utilizador",
                                 lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ─── Modelo: Pontuacao ────────────────────────────
class Pontuacao(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    pontos       = db.Column(db.Integer, nullable=False)
    data         = db.Column(db.DateTime, default=datetime.utcnow)
    # Chave estrangeira — liga cada score a um utilizador
    utilizador_id = db.Column(db.Integer,
                              db.ForeignKey("utilizador.id"),
                              nullable=False)


# Flask-Login usa esta função para recarregar o utilizador
# a partir do id guardado na sessão
@login_manager.user_loader
def load_user(user_id):
    return Utilizador.query.get(int(user_id))


with app.app_context():
    db.create_all()

ADIVINHAS = [
    # ─── Cultura geral ───────────────────────────────
    {"pergunta": "Qual é o animal mais rápido do mundo?",
     "resposta": "guepardo"},
    {"pergunta": "Quantas cores tem o arco-íris?",
     "resposta": "sete"},
    {"pergunta": "Qual é o planeta mais próximo do Sol?",
     "resposta": "mercúrio"},
    {"pergunta": "Em que continente fica o Egito?",
     "resposta": "áfrica"},
    {"pergunta": "Qual é o maior oceano do mundo?",
     "resposta": "pacífico"},
    {"pergunta": "Qual é a capital de Portugal?",
     "resposta": "lisboa"},
    {"pergunta": "Qual é o maior planeta do sistema solar?",
     "resposta": "júpiter"},
    {"pergunta": "Quantos lados tem um quadrado?",
     "resposta": "quatro"},
    {"pergunta": "Quem é considerado o rei da selva?",
     "resposta": "leão"},
    {"pergunta": "Qual é o metal precioso de cor amarela?",
     "resposta": "ouro"},

    # ─── Charadas / piadas 😄 ─────────────────────────
    {"pergunta": "🤔 O que é que quanto mais se tira, maior fica?",
     "resposta": "buraco"},
    {"pergunta": "🤔 O que é que tem dentes mas não morde?",
     "resposta": "pente"},
    {"pergunta": "🤔 O que é que cai em pé e corre deitado?",
     "resposta": "chuva"},
    {"pergunta": "🤔 Sou alto quando jovem e baixo quando velho. O que sou?",
     "resposta": "vela"},
    {"pergunta": "🤔 O que é que tem cidades mas não tem casas, "
                 "tem montanhas mas não tem árvores?",
     "resposta": "mapa"},
    {"pergunta": "😂 Qual é o chá que não se bebe? (dica: pões na cabeça)",
     "resposta": "chapéu"},
    {"pergunta": "😂 O que é que está sempre no canto mas dá a volta ao mundo?",
     "resposta": "selo"},
]

# ─── ROTA: Registo ────────────────────────────────
@app.route("/registo", methods=["GET", "POST"])
def registo():
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    if request.method == "POST":
        nome     = request.form["nome"].strip()
        email    = request.form["email"].strip().lower()
        password = request.form["password"]

        # Verificar se o email já existe
        if Utilizador.query.filter_by(email=email).first():
            flash("Este email já está registado.", "erro")
            return redirect(url_for("registo"))

        # Criar utilizador com password em hash
        novo = Utilizador(nome=nome, email=email)
        novo.set_password(password)
        db.session.add(novo)
        db.session.commit()

        login_user(novo)   # login automático após registo
        return redirect(url_for("inicio"))

    return render_template("registo.html")


# ─── ROTA: Login ──────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    if request.method == "POST":
        email    = request.form["email"].strip().lower()
        password = request.form["password"]
        utilizador = Utilizador.query.filter_by(email=email).first()

        if utilizador and utilizador.check_password(password):
            login_user(utilizador)
            return redirect(url_for("inicio"))
        else:
            flash("Email ou password incorretos.", "erro")

    return render_template("login.html")


# ─── ROTA: Logout ─────────────────────────────────
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))
# ─── ROTA: Página inicial ─────────────────────────
@app.route("/")
@login_required
def inicio():
    top5 = (Pontuacao.query
            .order_by(Pontuacao.pontos.desc())
            .limit(5).all())
    return render_template("index.html", top5=top5)


# ─── ROTA: Iniciar jogo ───────────────────────────
@app.route("/jogar")
@login_required
def jogar():
    lista = copy.deepcopy(ADIVINHAS)
    random.shuffle(lista)
    session["adivinhas"] = lista
    session["indice"]   = 0
    session["pontuacao"] = 0
    return redirect(url_for("pergunta"))


# ─── ROTA: Desistir (sair das perguntas sem guardar) ──
@app.route("/desistir")
@login_required
def desistir():
    session.pop("adivinhas", None)
    session.pop("indice", None)
    session.pop("pontuacao", None)
    flash("Desististe. Não faz mal, há-de correr melhor. 🙃", "info")
    return redirect(url_for("inicio"))


# ─── ROTA: Mostrar pergunta ───────────────────────
@app.route("/pergunta")
@login_required
def pergunta():
    indice    = session.get("indice", 0)
    lista     = session.get("adivinhas", [])
    pontuacao = session.get("pontuacao", 0)
    if indice >= len(lista):
        return redirect(url_for("fim"))
    return render_template(
        "pergunta.html",
        pergunta  = lista[indice]["pergunta"],
        numero    = indice + 1,
        total     = len(lista),
        pontuacao = pontuacao,
    )


# ─── ROTA: Verificar resposta ─────────────────────
@app.route("/verificar", methods=["POST"])
@login_required
def verificar():
    indice = session.get("indice", 0)
    lista  = session.get("adivinhas", [])

    # Sessão expirada / sem jogo a decorrer → recomeça em vez de rebentar
    if not lista or indice >= len(lista):
        return redirect(url_for("jogar"))

    resposta_user = request.form.get("resposta", "")
    resp_correta  = lista[indice]["resposta"]
    acertou       = normalizar(resposta_user) == normalizar(resp_correta)
    session["pontuacao"] = session.get("pontuacao", 0) + (100 if acertou else -50)
    session["indice"]    = indice + 1
    session.modified = True
    proxima = session["indice"] < len(lista)
    return render_template(
        "resultado.html",
        acertou          = acertou,
        resposta_correta = resp_correta,
        pontuacao        = session["pontuacao"],
        proxima          = proxima,
        numero           = indice + 1,
        total            = len(lista),
    )


# ─── ROTA: Ecrã final ────────────────────────────
@app.route("/fim")
@login_required
def fim():
    # Sem jogo a terminar (ex.: refresh depois de já guardar) → volta ao início.
    # Evita gravar a mesma pontuação várias vezes no leaderboard.
    if "adivinhas" not in session:
        return redirect(url_for("inicio"))

    pontuacao = session.get("pontuacao", 0)
    total     = len(session.get("adivinhas", []))

    # Guardar na DB ligado ao utilizador autenticado
    registo = Pontuacao(pontos=pontuacao,
                        utilizador_id=current_user.id)
    db.session.add(registo)
    db.session.commit()

    # Limpar o jogo da sessão para um refresh não voltar a guardar
    session.pop("adivinhas", None)
    session.pop("indice", None)
    session.pop("pontuacao", None)

    return render_template("fim.html",
                           pontuacao=pontuacao,
                           total=total)


# ─── ROTA: Perfil ─────────────────────────────────
@app.route("/perfil")
@login_required
def perfil():
    historico = (Pontuacao.query
                 .filter_by(utilizador_id=current_user.id)
                 .order_by(Pontuacao.data.desc())
                 .all())
    melhor = max((p.pontos for p in historico), default=0)
    return render_template("perfil.html",
                           historico=historico,
                           melhor=melhor)


if __name__ == "__main__":
    app.run(debug=True)