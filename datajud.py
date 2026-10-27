"""Consulta à API pública do Datajud (CNJ).

Documentação: https://datajud-wiki.cnj.jus.br/api-publica/
A chave pública é divulgada pelo CNJ e pode mudar; defina DATAJUD_API_KEY para sobrescrever.
"""
import json
import os
import re
import urllib.error
import urllib.request

API_URL = "https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search"
CHAVE_PUBLICA = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Código TR (segmento 8 = Justiça Estadual) -> sigla do TJ
TJ_POR_CODIGO = {
    "01": "ac", "02": "al", "03": "ap", "04": "am", "05": "ba", "06": "ce", "07": "dft", "08": "es",
    "09": "go", "10": "ma", "11": "mt", "12": "ms", "13": "mg", "14": "pa", "15": "pb", "16": "pr",
    "17": "pe", "18": "pi", "19": "rj", "20": "rn", "21": "rs", "22": "ro", "23": "rr", "24": "sc",
    "25": "se", "26": "sp", "27": "to",
}


class DatajudErro(Exception):
    pass


def somente_digitos(numero):
    return re.sub(r"\D", "", numero or "")


def alias_tribunal(numero):
    """Descobre o índice do tribunal a partir do número CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO)."""
    d = somente_digitos(numero)
    if len(d) != 20:
        raise DatajudErro("Número CNJ deve ter 20 dígitos (ex.: 0000123-45.2024.5.09.0001).")
    justica, tr = d[13], d[14:16]
    if justica == "5":
        return "tst" if tr == "00" else f"trt{int(tr)}"
    if justica == "4":
        return f"trf{int(tr)}"
    if justica == "8" and tr in TJ_POR_CODIGO:
        return f"tj{TJ_POR_CODIGO[tr]}"
    if justica == "3":
        return "stj"
    raise DatajudErro("Tribunal não suportado para este número.")


def consultar(numero, timeout=20):
    """Retorna um dict resumido do processo, ou None se não encontrado."""
    alias = alias_tribunal(numero)
    corpo = json.dumps({"query": {"match": {"numeroProcesso": somente_digitos(numero)}}}).encode()
    req = urllib.request.Request(
        API_URL.format(alias=alias), data=corpo, method="POST",
        headers={"Authorization": "APIKey " + os.environ.get("DATAJUD_API_KEY", CHAVE_PUBLICA),
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dados = json.load(resp)
    except urllib.error.HTTPError as e:
        raise DatajudErro(f"Datajud respondeu com erro {e.code}.") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise DatajudErro("Não foi possível conectar ao Datajud.") from e

    hits = dados.get("hits", {}).get("hits", [])
    if not hits:
        return None
    # Pode haver um registro por grau (1º grau, 2º grau); junta os movimentos de todos.
    fontes = [h["_source"] for h in hits]
    principal = max(fontes, key=lambda s: s.get("dataHoraUltimaAtualizacao", ""))
    movimentos = []
    for s in fontes:
        for m in s.get("movimentos", []):
            compl = ", ".join(c.get("nome") or c.get("descricao", "") for c in m.get("complementosTabelados", []))
            movimentos.append({"data": m.get("dataHora", ""), "nome": m.get("nome", ""),
                               "complemento": compl, "grau": s.get("grau", "")})
    movimentos.sort(key=lambda m: m["data"], reverse=True)
    return {
        "tribunal": principal.get("tribunal") or alias.upper(),
        "grau": principal.get("grau"),
        "classe": (principal.get("classe") or {}).get("nome"),
        "orgao": (principal.get("orgaoJulgador") or {}).get("nome"),
        "assuntos": [a.get("nome") for a in principal.get("assuntos", []) if isinstance(a, dict)],
        "ajuizamento": principal.get("dataAjuizamento"),
        "atualizado_tribunal": principal.get("dataHoraUltimaAtualizacao"),
        "movimentos": movimentos,
    }
