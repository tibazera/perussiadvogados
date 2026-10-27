"""Perussi Advogados: site institucional + CRM básico."""
import json
import os
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import datajud

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao"),
    DATABASE=os.environ.get("DATABASE", os.path.join(BASE_DIR, "instance", "crm.db")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

ESCRITORIO = {
    "nome": "Perussi Advogados",
    "razao": "Paulo Henrique Gomes Perussi Sociedade Individual de Advocacia",
    "cnpj": "28.702.146/0001-06",
    "advogado": "Paulo Henrique Gomes Perussi",
    "oab": os.environ.get("OAB_NUMERO", "75.627"),
    "endereco": "Rua Senador Souza Naves, 626, 4º andar, sala 45, Centro",
    "cidade": "Londrina - PR, CEP 86010-160",
    "telefone": "(43) 3039-1839",
    "whatsapp": "(43) 98442-1839",
    "whatsapp_link": "https://wa.me/5543984421839",
    "email": "perussi@perussirodui.com.br",
    "horario": "Segunda a sexta, das 8h às 18h",
    "instagram": "https://www.instagram.com/perussiadvogados/",
    "facebook": "https://www.facebook.com/perussiroduiadv/",
}

AREAS = ["Trabalhista", "Cível", "Família", "Outra"]
STATUS_LEAD = ["Novo", "Em contato", "Consulta agendada", "Virou cliente", "Perdido"]
STATUS_PROCESSO = ["Em andamento", "Suspenso", "Acordo", "Sentença", "Recurso", "Arquivado"]
TIPOS_COMPROMISSO = ["Audiência", "Prazo", "Reunião", "Tarefa"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY, nome TEXT NOT NULL, telefone TEXT, email TEXT,
    area TEXT, mensagem TEXT, origem TEXT DEFAULT 'Site', status TEXT DEFAULT 'Novo',
    observacoes TEXT, criado_em TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY, nome TEXT NOT NULL, cpf_cnpj TEXT, telefone TEXT,
    email TEXT, endereco TEXT, observacoes TEXT, criado_em TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS processos (
    id INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    numero TEXT, area TEXT, parte_contraria TEXT, vara TEXT, status TEXT DEFAULT 'Em andamento',
    honorarios REAL, honorarios_recebidos REAL DEFAULT 0, observacoes TEXT,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS compromissos (
    id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, tipo TEXT, data TEXT NOT NULL, hora TEXT,
    processo_id INTEGER REFERENCES processos(id) ON DELETE SET NULL,
    concluido INTEGER DEFAULT 0, observacoes TEXT);
"""


# ---------------------------------------------------------------- banco

def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


MIGRACOES = {
    "processos": {"datajud_json": "TEXT", "datajud_consultado_em": "TEXT", "datajud_novidade": "INTEGER DEFAULT 0"},
}


def init_db():
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        for tabela, colunas in MIGRACOES.items():
            existentes = {r["name"] for r in db.execute(f"PRAGMA table_info({tabela})")}
            for col, tipo in colunas.items():
                if col not in existentes:
                    db.execute(f"ALTER TABLE {tabela} ADD COLUMN {col} {tipo}")
        db.commit()


def query(sql, args=(), one=False):
    rows = get_db().execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def form_values(fields):
    return [request.form.get(f, "").strip() or None for f in fields]


def to_float(value):
    if not value:
        return None
    try:
        return float(value.replace(".", "").replace(",", ".")) if "," in value else float(value)
    except ValueError:
        return None


# ---------------------------------------------------------------- auth

def admin_password_hash():
    senha = os.environ.get("ADMIN_PASSWORD")
    if not senha:
        return None
    return generate_password_hash(senha) if not senha.startswith(("scrypt:", "pbkdf2:")) else senha


ADMIN_USER = os.environ.get("ADMIN_USER", "paulo")
ADMIN_HASH = admin_password_hash()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"esc": ESCRITORIO, "ano": date.today().year}


# ---------------------------------------------------------------- site público

@app.get("/")
def home():
    foto = next((f for f in ("paulo.jpg", "paulo.jpeg", "paulo.png", "paulo.webp")
                 if os.path.exists(os.path.join(BASE_DIR, "static", "img", f))), None)
    return render_template("site.html", areas=AREAS[:3], foto_paulo=foto)


@app.post("/contato")
def contato():
    if request.form.get("website"):  # honeypot anti-spam
        return redirect(url_for("home"))
    nome, telefone, email, area, mensagem = form_values(
        ["nome", "telefone", "email", "area", "mensagem"])
    if not nome or not (telefone or email) or not request.form.get("lgpd"):
        flash("Informe seu nome, um telefone ou e-mail e aceite a política de privacidade.", "erro")
        return redirect(url_for("home") + "#contato")
    execute("INSERT INTO leads (nome, telefone, email, area, mensagem) VALUES (?,?,?,?,?)",
            (nome, telefone, email, area, (mensagem or "")[:3000]))
    flash("Mensagem recebida! Entraremos em contato em breve.", "ok")
    return redirect(url_for("home") + "#contato")


@app.get("/privacidade")
def privacidade():
    return render_template("privacidade.html")


# ---------------------------------------------------------------- login

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (ADMIN_HASH and request.form.get("usuario") == ADMIN_USER
                and check_password_hash(ADMIN_HASH, request.form.get("senha", ""))):
            session.clear()
            session["admin"] = True
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/admin") else url_for("dashboard"))
        flash("Usuário ou senha inválidos." if ADMIN_HASH
              else "Defina a variável ADMIN_PASSWORD para habilitar o acesso.", "erro")
    return render_template("admin/login.html")


@app.post("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- CRM

@app.get("/admin")
@login_required
def dashboard():
    hoje = date.today().isoformat()
    stats = {
        "leads_novos": query("SELECT COUNT(*) c FROM leads WHERE status='Novo'", one=True)["c"],
        "clientes": query("SELECT COUNT(*) c FROM clientes", one=True)["c"],
        "processos": query("SELECT COUNT(*) c FROM processos WHERE status!='Arquivado'", one=True)["c"],
        "novidades": query("SELECT COUNT(*) c FROM processos WHERE datajud_novidade=1", one=True)["c"],
        "a_receber": query("SELECT COALESCE(SUM(honorarios - COALESCE(honorarios_recebidos,0)),0) v "
                           "FROM processos WHERE honorarios IS NOT NULL", one=True)["v"],
    }
    agenda = query("""SELECT c.*, p.numero FROM compromissos c LEFT JOIN processos p ON p.id=c.processo_id
                      WHERE c.concluido=0 AND c.data <= date(?, '+7 day')
                      ORDER BY c.data, c.hora LIMIT 15""", (hoje,))
    leads = query("SELECT * FROM leads WHERE status='Novo' ORDER BY criado_em DESC LIMIT 5")
    movimentados = query("""SELECT p.id, p.numero, c.nome cliente FROM processos p
                            JOIN clientes c ON c.id=p.cliente_id WHERE p.datajud_novidade=1""")
    return render_template("admin/dashboard.html", stats=stats, agenda=agenda, leads=leads, hoje=hoje,
                           movimentados=movimentados)


# Leads ---------------------------------------------------------------

@app.get("/admin/leads")
@login_required
def leads():
    status = request.args.get("status")
    if status in STATUS_LEAD:
        rows = query("SELECT * FROM leads WHERE status=? ORDER BY criado_em DESC", (status,))
    else:
        rows = query("SELECT * FROM leads ORDER BY criado_em DESC")
    contagem = {r["status"]: r["c"] for r in query("SELECT status, COUNT(*) c FROM leads GROUP BY status")}
    return render_template("admin/leads.html", leads=rows, status_lista=STATUS_LEAD,
                           filtro=status, contagem=contagem)


@app.route("/admin/leads/novo", methods=["GET", "POST"])
@app.route("/admin/leads/<int:id>", methods=["GET", "POST"])
@login_required
def lead_form(id=None):
    lead = query("SELECT * FROM leads WHERE id=?", (id,), one=True) if id else None
    if id and not lead:
        abort(404)
    if request.method == "POST":
        campos = ["nome", "telefone", "email", "area", "mensagem", "origem", "status", "observacoes"]
        vals = form_values(campos)
        if not vals[0]:
            flash("Nome é obrigatório.", "erro")
        else:
            if id:
                execute(f"UPDATE leads SET {', '.join(c + '=?' for c in campos)} WHERE id=?", (*vals, id))
            else:
                id = execute(f"INSERT INTO leads ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})", vals)
            flash("Lead salvo.", "ok")
            return redirect(url_for("leads"))
    return render_template("admin/lead_form.html", lead=lead, areas=AREAS, status_lista=STATUS_LEAD)


@app.post("/admin/leads/<int:id>/converter")
@login_required
def lead_converter(id):
    lead = query("SELECT * FROM leads WHERE id=?", (id,), one=True) or abort(404)
    cliente_id = execute(
        "INSERT INTO clientes (nome, telefone, email, observacoes) VALUES (?,?,?,?)",
        (lead["nome"], lead["telefone"], lead["email"],
         f"Origem: {lead['origem']} ({lead['area'] or 'sem área'}). {lead['mensagem'] or ''}".strip()))
    execute("UPDATE leads SET status='Virou cliente' WHERE id=?", (id,))
    flash("Lead convertido em cliente.", "ok")
    return redirect(url_for("cliente_detalhe", id=cliente_id))


@app.post("/admin/leads/<int:id>/excluir")
@login_required
def lead_excluir(id):
    execute("DELETE FROM leads WHERE id=?", (id,))
    flash("Lead excluído.", "ok")
    return redirect(url_for("leads"))


# Clientes ------------------------------------------------------------

@app.get("/admin/clientes")
@login_required
def clientes():
    q = request.args.get("q", "").strip()
    sql = """SELECT c.*, (SELECT COUNT(*) FROM processos p WHERE p.cliente_id=c.id) n_processos
             FROM clientes c"""
    if q:
        like = f"%{q}%"
        rows = query(sql + " WHERE c.nome LIKE ? OR c.cpf_cnpj LIKE ? OR c.telefone LIKE ? ORDER BY c.nome",
                     (like, like, like))
    else:
        rows = query(sql + " ORDER BY c.nome")
    return render_template("admin/clientes.html", clientes=rows, q=q)


@app.route("/admin/clientes/novo", methods=["GET", "POST"])
@app.route("/admin/clientes/<int:id>/editar", methods=["GET", "POST"])
@login_required
def cliente_form(id=None):
    cliente = query("SELECT * FROM clientes WHERE id=?", (id,), one=True) if id else None
    if id and not cliente:
        abort(404)
    if request.method == "POST":
        campos = ["nome", "cpf_cnpj", "telefone", "email", "endereco", "observacoes"]
        vals = form_values(campos)
        if not vals[0]:
            flash("Nome é obrigatório.", "erro")
        else:
            if id:
                execute(f"UPDATE clientes SET {', '.join(c + '=?' for c in campos)} WHERE id=?", (*vals, id))
            else:
                id = execute(f"INSERT INTO clientes ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})", vals)
            flash("Cliente salvo.", "ok")
            return redirect(url_for("cliente_detalhe", id=id))
    return render_template("admin/cliente_form.html", cliente=cliente)


@app.get("/admin/clientes/<int:id>")
@login_required
def cliente_detalhe(id):
    cliente = query("SELECT * FROM clientes WHERE id=?", (id,), one=True) or abort(404)
    processos = query("SELECT * FROM processos WHERE cliente_id=? ORDER BY criado_em DESC", (id,))
    return render_template("admin/cliente_detalhe.html", cliente=cliente, processos=processos)


@app.post("/admin/clientes/<int:id>/excluir")
@login_required
def cliente_excluir(id):
    execute("DELETE FROM clientes WHERE id=?", (id,))
    flash("Cliente excluído.", "ok")
    return redirect(url_for("clientes"))


# Processos -----------------------------------------------------------

@app.get("/admin/processos")
@login_required
def processos():
    status = request.args.get("status")
    sql = "SELECT p.*, c.nome cliente FROM processos p JOIN clientes c ON c.id=p.cliente_id"
    rows = (query(sql + " WHERE p.status=? ORDER BY p.criado_em DESC", (status,))
            if status in STATUS_PROCESSO else query(sql + " ORDER BY p.criado_em DESC"))
    return render_template("admin/processos.html", processos=rows, status_lista=STATUS_PROCESSO, filtro=status)


@app.route("/admin/processos/novo", methods=["GET", "POST"])
@app.route("/admin/processos/<int:id>", methods=["GET", "POST"])
@login_required
def processo_form(id=None):
    processo = query("SELECT * FROM processos WHERE id=?", (id,), one=True) if id else None
    if id and not processo:
        abort(404)
    if request.method == "POST":
        campos = ["cliente_id", "numero", "area", "parte_contraria", "vara", "status", "observacoes"]
        vals = form_values(campos)
        hon = [to_float(request.form.get("honorarios")), to_float(request.form.get("honorarios_recebidos")) or 0]
        if not vals[0] or not query("SELECT 1 FROM clientes WHERE id=?", (vals[0],), one=True):
            flash("Selecione um cliente.", "erro")
        else:
            todos = campos + ["honorarios", "honorarios_recebidos"]
            if id:
                execute(f"UPDATE processos SET {', '.join(c + '=?' for c in todos)} WHERE id=?", (*vals, *hon, id))
            else:
                id = execute(f"INSERT INTO processos ({', '.join(todos)}) VALUES ({', '.join('?' * len(todos))})",
                             (*vals, *hon))
            flash("Processo salvo.", "ok")
            return redirect(url_for("processo_form", id=id))
    compromissos = query("SELECT * FROM compromissos WHERE processo_id=? ORDER BY data, hora", (id,)) if id else []
    dj = json.loads(processo["datajud_json"]) if processo and processo["datajud_json"] else None
    return render_template("admin/processo_form.html", processo=processo, compromissos=compromissos, dj=dj,
                           clientes=query("SELECT id, nome FROM clientes ORDER BY nome"),
                           areas=AREAS, status_lista=STATUS_PROCESSO,
                           cliente_pre=request.args.get("cliente_id", type=int))


@app.post("/admin/processos/<int:id>/excluir")
@login_required
def processo_excluir(id):
    execute("DELETE FROM processos WHERE id=?", (id,))
    flash("Processo excluído.", "ok")
    return redirect(url_for("processos"))


def atualizar_datajud(processo):
    """Consulta o Datajud e grava o resultado. Retorna (ok, mensagem)."""
    try:
        resultado = datajud.consultar(processo["numero"])
    except datajud.DatajudErro as e:
        return False, str(e)
    if resultado is None:
        return False, "Processo não encontrado no Datajud (pode estar em segredo de justiça ou ainda não indexado)."
    anterior = json.loads(processo["datajud_json"]) if processo["datajud_json"] else None
    ultimo_antes = anterior["movimentos"][0]["data"] if anterior and anterior["movimentos"] else None
    ultimo_agora = resultado["movimentos"][0]["data"] if resultado["movimentos"] else None
    novidade = 1 if anterior is not None and ultimo_agora and ultimo_agora != ultimo_antes else processo["datajud_novidade"] or 0
    execute("UPDATE processos SET datajud_json=?, datajud_consultado_em=?, datajud_novidade=? WHERE id=?",
            (json.dumps(resultado, ensure_ascii=False), datetime.now().isoformat(timespec="minutes"),
             novidade, processo["id"]))
    return True, "Nova movimentação encontrada!" if novidade and anterior else "Dados do Datajud atualizados."


@app.post("/admin/processos/<int:id>/datajud")
@login_required
def processo_datajud(id):
    processo = query("SELECT * FROM processos WHERE id=?", (id,), one=True) or abort(404)
    ok, msg = atualizar_datajud(processo)
    flash(msg, "ok" if ok else "erro")
    return redirect(url_for("processo_form", id=id))


@app.post("/admin/processos/<int:id>/visto")
@login_required
def processo_visto(id):
    execute("UPDATE processos SET datajud_novidade=0 WHERE id=?", (id,))
    return redirect(url_for("processo_form", id=id))


@app.post("/admin/processos/datajud")
@login_required
def processos_datajud_todos():
    procs = query("SELECT * FROM processos WHERE numero IS NOT NULL AND status != 'Arquivado'")
    ok = sum(atualizar_datajud(p)[0] for p in procs)
    novos = query("SELECT COUNT(*) c FROM processos WHERE datajud_novidade=1", one=True)["c"]
    flash(f"{ok} de {len(procs)} processos consultados no Datajud. {novos} com movimentação nova.", "ok")
    return redirect(url_for("processos"))


# Agenda --------------------------------------------------------------

@app.get("/admin/agenda")
@login_required
def agenda():
    mostrar = request.args.get("mostrar", "pendentes")
    sql = """SELECT a.*, p.numero, c.nome cliente FROM compromissos a
             LEFT JOIN processos p ON p.id=a.processo_id LEFT JOIN clientes c ON c.id=p.cliente_id"""
    rows = query(sql + (" WHERE a.concluido=0" if mostrar == "pendentes" else "") + " ORDER BY a.data, a.hora")
    return render_template("admin/agenda.html", compromissos=rows, mostrar=mostrar, hoje=date.today().isoformat())


@app.route("/admin/agenda/novo", methods=["GET", "POST"])
@app.route("/admin/agenda/<int:id>", methods=["GET", "POST"])
@login_required
def compromisso_form(id=None):
    comp = query("SELECT * FROM compromissos WHERE id=?", (id,), one=True) if id else None
    if id and not comp:
        abort(404)
    if request.method == "POST":
        campos = ["titulo", "tipo", "data", "hora", "processo_id", "observacoes"]
        vals = form_values(campos)
        concluido = 1 if request.form.get("concluido") else 0
        if not vals[0] or not vals[2]:
            flash("Título e data são obrigatórios.", "erro")
        else:
            todos = campos + ["concluido"]
            if id:
                execute(f"UPDATE compromissos SET {', '.join(c + '=?' for c in todos)} WHERE id=?",
                        (*vals, concluido, id))
            else:
                execute(f"INSERT INTO compromissos ({', '.join(todos)}) VALUES ({', '.join('?' * len(todos))})",
                        (*vals, concluido))
            flash("Compromisso salvo.", "ok")
            return redirect(url_for("agenda"))
    procs = query("SELECT p.id, p.numero, c.nome cliente FROM processos p JOIN clientes c ON c.id=p.cliente_id "
                  "ORDER BY c.nome")
    return render_template("admin/compromisso_form.html", comp=comp, processos=procs, tipos=TIPOS_COMPROMISSO,
                           processo_pre=request.args.get("processo_id", type=int))


@app.post("/admin/agenda/<int:id>/concluir")
@login_required
def compromisso_concluir(id):
    execute("UPDATE compromissos SET concluido = 1 - concluido WHERE id=?", (id,))
    return redirect(request.referrer or url_for("agenda"))


@app.post("/admin/agenda/<int:id>/excluir")
@login_required
def compromisso_excluir(id):
    execute("DELETE FROM compromissos WHERE id=?", (id,))
    flash("Compromisso excluído.", "ok")
    return redirect(url_for("agenda"))


# ---------------------------------------------------------------- filtros

@app.template_filter("brl")
def brl(value):
    if value is None:
        return "-"
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("data_br")
def data_br(value):
    if not value:
        return ""
    v = str(value)
    if len(v) == 14 and v.isdigit():  # formato AAAAMMDDHHMMSS usado por alguns tribunais
        v = f"{v[:4]}-{v[4:6]}-{v[6:8]}T{v[8:10]}:{v[10:12]}"
    d = v[:10].split("-")
    if len(d) != 3:
        return value
    hora = v[11:16] if len(v) >= 16 and v[11:16] != "00:00" else ""
    return f"{d[2]}/{d[1]}/{d[0]}" + (f" {hora}" if hora else "")


init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", 5000)))
