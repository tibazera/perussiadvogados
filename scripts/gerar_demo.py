"""Gera uma versão estática de demonstração (site + CRM com dados fictícios) em docs/.

Uso: python scripts/gerar_demo.py  ->  publicar a pasta docs/ (GitHub Pages, Netlify etc.)
"""
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "docs")
sys.path.insert(0, RAIZ)
os.environ["DATABASE"] = os.path.join(tempfile.mkdtemp(), "demo.db")
os.environ.setdefault("ADMIN_PASSWORD", "demo")

from app import app, execute  # noqa: E402

PAGINAS = {
    "/": "index.html",
    "/privacidade": "privacidade.html",
    "/admin/login": "admin/login.html",
    "/admin": "admin/index.html",
    "/admin/leads": "admin/leads.html",
    "/admin/leads/1": "admin/lead-1.html",
    "/admin/clientes": "admin/clientes.html",
    "/admin/clientes/1": "admin/cliente-1.html",
    "/admin/processos": "admin/processos.html",
    "/admin/processos/1": "admin/processo-1.html",
    "/admin/processos/2": "admin/processo-2.html",
    "/admin/agenda": "admin/agenda.html",
}

AVISO = """<style>.whats-float{bottom:64px!important}</style><div style="position:fixed;left:0;right:0;bottom:0;z-index:99;background:#c9a45c;color:#0f1f3a;
text-align:center;padding:8px 12px;font:600 13px system-ui">Versão de demonstração · dados fictícios · botões desativados</div>
<script>document.addEventListener('submit',function(e){e.preventDefault();
if(e.target.querySelector('[name=senha]')){location.href='index.html';return;}
alert('Demonstração: na versão final esta ação é salva no sistema.');});</script>"""


def d(dias):
    return (date.today() + timedelta(days=dias)).isoformat()


def popular():
    leads = [
        ("Marcos Oliveira", "(43) 99811-2233", "marcos@email.com", "Trabalhista",
         "Fui demitido sem receber as verbas rescisórias e as horas extras.", "Site", "Novo"),
        ("Ana Paula Ribeiro", "(43) 99702-4455", None, "Família",
         "Gostaria de orientação sobre pensão alimentícia.", "Instagram", "Novo"),
        ("José Carlos Lima", "(43) 98455-6677", "jose.lima@email.com", "Trabalhista",
         "Trabalhei 3 anos sem carteira assinada.", "WhatsApp", "Em contato"),
        ("Fernanda Souza", "(43) 99123-8899", "fe.souza@email.com", "Trabalhista",
         "Sofri acidente de trabalho e fui dispensada.", "Indicação", "Consulta agendada"),
        ("Ricardo Mendes", "(43) 99988-1122", None, "Cível", "Problema com contrato de compra.", "Site", "Perdido"),
    ]
    for l in leads:
        execute("INSERT INTO leads (nome, telefone, email, area, mensagem, origem, status) VALUES (?,?,?,?,?,?,?)", l)

    clientes = [
        ("Carla Regina Martins", "123.456.789-00", "(43) 99654-3210", "carla@email.com", "Rua Pará, 100, Londrina"),
        ("Pedro Henrique Alves", "987.654.321-00", "(43) 98877-6655", None, "Av. Higienópolis, 500, Londrina"),
        ("Luciana Ferreira", "456.789.123-00", "(43) 99543-2109", "luciana@email.com", "Cambé - PR"),
    ]
    for c in clientes:
        execute("INSERT INTO clientes (nome, cpf_cnpj, telefone, email, endereco) VALUES (?,?,?,?,?)", c)

    procs = [
        (1, "0000412-18.2025.5.09.0018", "Trabalhista", "Supermercados Exemplo Ltda", "1ª Vara do Trabalho de Londrina",
         "Em andamento", 8000, 2000),
        (2, "0001033-77.2024.5.09.0663", "Trabalhista", "Transportadora Modelo S.A.", "5ª Vara do Trabalho de Londrina",
         "Recurso", 12000, 6000),
        (3, "0012345-67.2025.8.16.0014", "Família", "-", "Vara de Família de Londrina", "Em andamento", 4500, 4500),
    ]
    for p in procs:
        execute("""INSERT INTO processos (cliente_id, numero, area, parte_contraria, vara, status, honorarios,
                   honorarios_recebidos) VALUES (?,?,?,?,?,?,?,?)""", p)

    dj1 = {"tribunal": "TRT9", "grau": "G1", "classe": "Ação Trabalhista - Rito Ordinário",
           "orgao": "1ª VARA DO TRABALHO DE LONDRINA", "assuntos": ["Horas Extras", "Verbas Rescisórias"],
           "ajuizamento": "2025-03-10T00:00:00", "atualizado_tribunal": d(-2) + "T10:00:00",
           "movimentos": [
               {"data": d(-2) + "T14:32:00", "nome": "Designada audiência de instrução", "complemento": ""},
               {"data": d(-30) + "T09:10:00", "nome": "Juntada de petição", "complemento": "Réplica"},
               {"data": d(-60) + "T16:00:00", "nome": "Audiência inicial realizada", "complemento": "sem acordo"},
               {"data": "2025-03-10T08:00:00", "nome": "Distribuído por sorteio", "complemento": ""}]}
    dj2 = {"tribunal": "TRT9", "grau": "G2", "classe": "Recurso Ordinário Trabalhista",
           "orgao": "3ª TURMA", "assuntos": ["Vínculo Empregatício"], "ajuizamento": "2024-05-02T00:00:00",
           "atualizado_tribunal": d(-20) + "T10:00:00",
           "movimentos": [
               {"data": d(-20) + "T11:00:00", "nome": "Conclusos para julgamento", "complemento": ""},
               {"data": d(-90) + "T15:00:00", "nome": "Recebido recurso ordinário", "complemento": ""},
               {"data": d(-120) + "T10:00:00", "nome": "Sentença", "complemento": "procedente em parte"}]}
    agora = date.today().isoformat() + "T08:00"
    execute("UPDATE processos SET datajud_json=?, datajud_consultado_em=?, datajud_novidade=1 WHERE id=1",
            (json.dumps(dj1, ensure_ascii=False), agora))
    execute("UPDATE processos SET datajud_json=?, datajud_consultado_em=? WHERE id=2",
            (json.dumps(dj2, ensure_ascii=False), agora))

    comps = [
        ("Prazo: manifestação sobre laudo", "Prazo", d(-1), None, 2),
        ("Reunião com Fernanda Souza", "Reunião", d(0), "15:00", None),
        ("Audiência de instrução", "Audiência", d(3), "14:30", 1),
        ("Enviar documentos para cálculo", "Tarefa", d(5), None, 1),
        ("Audiência de conciliação", "Audiência", d(12), "09:00", 3),
    ]
    for c in comps:
        execute("INSERT INTO compromissos (titulo, tipo, data, hora, processo_id) VALUES (?,?,?,?,?)", c)


def relativizar(html, pagina):
    profundidade = pagina.count("/")
    prefixo = "../" * profundidade

    def troca(m):
        attr, url = m.group(1), m.group(2)
        caminho, _, ancora = url.partition("#")
        caminho = caminho.split("?")[0]
        if caminho.startswith("/static/"):
            novo = prefixo + caminho[1:]
        elif caminho in PAGINAS:
            novo = prefixo + PAGINAS[caminho]
        elif caminho == "" and ancora:
            return m.group(0)
        else:
            novo = "#"
        return f'{attr}="{novo}{"#" + ancora if ancora else ""}"'

    return re.sub(r'(href|src|action)="(/[^"]*)"', troca, html)


def main():
    with app.app_context():
        popular()
    shutil.rmtree(SAIDA, ignore_errors=True)
    shutil.copytree(os.path.join(RAIZ, "static"), os.path.join(SAIDA, "static"),
                    ignore=shutil.ignore_patterns("*.zip"))
    c = app.test_client()
    for rota, arquivo in PAGINAS.items():
        with c.session_transaction() as s:
            s["admin"] = rota != "/admin/login"
        r = c.get(rota)
        assert r.status_code == 200, (rota, r.status_code)
        html = relativizar(r.get_data(as_text=True), arquivo).replace("</body>", AVISO + "</body>")
        os.makedirs(os.path.dirname(os.path.join(SAIDA, arquivo)), exist_ok=True)
        with open(os.path.join(SAIDA, arquivo), "w", encoding="utf-8") as f:
            f.write(html)
    open(os.path.join(SAIDA, ".nojekyll"), "w").close()
    print(f"Demo gerada em {SAIDA} ({len(PAGINAS)} páginas)")


if __name__ == "__main__":
    main()
