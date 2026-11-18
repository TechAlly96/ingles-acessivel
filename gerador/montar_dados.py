#!/usr/bin/env python3
"""Inglês Acessível - transforma o curso (conteudo/curso.json) nos dados do app (JSON).

Fonte da verdade: conteudo/curso.json. Cada aula tem explicação em português,
frases [inglês, português] e uma conversa [quem (a/b), inglês, português].
Na explicação, o que estiver entre {chaves} é inglês e é narrado pela voz em inglês.

Cada parte vira um áudio com capítulos (um capítulo por frase, para pular com ⏭).
O roteiro de cada capítulo é uma lista de trechos:
  {"v": "pt"|"a"|"b", "t": texto, "lento": bool}  fala (pt = narrador, a/b = vozes em inglês)
  {"rep": "a"|"b", "t": texto}                      bipe + silêncio para o aluno repetir
Saída: <saida>/partes.json e <saida>/<parte>/conteudo.json
Somente biblioteca padrão (roda no Termux e no GitHub).
Uso: python3 gerador/montar_dados.py [pasta_de_saida]   (padrão: dados)
     python3 gerador/montar_dados.py dados --duracoes  (depois da narração)"""
import html
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CURSO = RAIZ / "conteudo" / "curso.json"
NIVEIS = {"Comece aqui": "geral", "Básico": "basico", "Intermediário": "intermediario", "Avançado": "avancado"}
NOME_NIVEL = {"basico": "básico", "intermediario": "intermediário", "avancado": "avançado"}


# ---------- trechos do roteiro ----------
def pt(texto):
    """Texto em português; {trechos} entre chaves viram fala em inglês."""
    saida = []
    for k, pedaco in enumerate(re.split(r"\{([^}]+)\}", texto)):
        pedaco = re.sub(r"\s+", " ", pedaco).strip()
        if pedaco:
            saida.append({"v": "a" if k % 2 else "pt", "t": pedaco})
    return saida


def en(texto, voz="a", lento=False):
    return [{"v": voz, "t": texto, **({"lento": True} if lento else {})}]


def rep(texto, voz="a"):
    return [{"rep": voz, "t": texto}]


def falado(titulo):
    """'Aula 1 — Apresentações' -> 'Aula 1, Apresentações.' (para a voz)."""
    t = titulo.replace(" — ", ", ")
    return t if t.endswith((".", "!", "?")) else t + "."


def html_pt(texto):
    seguro = html.escape(texto, quote=False)
    return re.sub(r"\{([^}]+)\}", r'<em lang="en">\1</em>', seguro)


def html_frase(e, p):
    return f'<p><strong lang="en">{html.escape(e)}</strong><br>{html.escape(p)}</p>'


def cap(cid, titulo, roteiro, texto_html):
    fala = " ".join(t["t"] for t in roteiro if "v" in t)
    return {"id": cid, "titulo": titulo, "html": texto_html, "fala": fala, "roteiro": roteiro}


# ---------- montagem das partes ----------
def aula_completa(aulas, i):
    a = aulas[i]
    caps, n = [], 0

    def novo(titulo, roteiro, h):
        nonlocal n
        caps.append(cap(f"c{n:02d}", titulo, roteiro, h))
        n += 1

    novo("Explicação", pt(falado(a["titulo"]) + " " + a["explicacao"]), f"<p>{html_pt(a['explicacao'])}</p>")
    if i > 1 and aulas[i - 1]["frases"]:
        ant = aulas[i - 1]["frases"][:6]
        r = pt("Primeiro, uma revisão rápida da aula anterior. Repita depois do bipe.")
        for e, _ in ant:
            r += en(e) + rep(e)
        novo("Revisão da aula anterior", r, "".join(html_frase(e, p) for e, p in ant))
    if a["frases"]:
        for k, (e, p) in enumerate(a["frases"]):
            r = (pt("Agora, as frases novas. Ouça, entenda e repita.") if k == 0 else [])
            r += en(e, lento=True) + pt(p) + en(e) + rep(e) + en(e) + rep(e)
            novo(e, r, html_frase(e, p))
    d = a["conversa"]
    if d:
        r = pt("Agora, a conversa. Primeiro, fala por fala, com tradução.")
        for q, e, p in d:
            r += en(e, q) + pt(p)
        novo("Conversa, fala por fala", r, "".join(f'<p><strong lang="en">{q.upper()}: {html.escape(e)}</strong><br>{html.escape(p)}</p>' for q, e, p in d))
        r = pt("Agora a conversa inteira, só em inglês. Imagine a cena.")
        for q, e, _ in d:
            r += en(e, q)
        novo("Conversa completa", r, "".join(f'<p lang="en">{q.upper()}: {html.escape(e)}</p>' for q, e, _ in d))
        r = pt("Sua vez. Repita cada fala depois do bipe.")
        for q, e, _ in d:
            r += en(e, q) + rep(e, q)
        novo("Sua vez: repita as falas", r, "".join(f'<p lang="en">{html.escape(e)}</p>' for _, e, _ in d))
    if a["frases"] and i > 0:
        r = pt("Revisão final. Só em inglês.")
        for e, _ in a["frases"]:
            r += en(e) + rep(e)
        novo("Revisão final", r, "".join(f'<p lang="en">{html.escape(e)}</p>' for e, _ in a["frases"]))
        fim = f"Fim da {a['titulo'].split(' — ')[0]}. Ouça esta aula de novo amanhã. Quando ela ficar fácil, siga para a próxima."
        novo("Encerramento", pt(fim), f"<p>{html.escape(fim)}</p>")
    return caps


def imersao(aulas, nivel):
    caps = [cap("c00", "Abertura", pt(f"Imersão do nível {NOME_NIVEL[nivel]}. A partir de agora, só inglês, sem tradução. "
                                      "Não tente traduzir na cabeça. Só ouça e repita depois do bipe, como uma criança "
                                      "que ouve a família. Vamos lá."),
                "<p>Só inglês, sem tradução: ouça e repita depois do bipe.</p>")]
    for a in aulas:
        r = en(a["titulo_en"] + ".")
        for e, _ in a["frases"]:
            r += en(e, lento=True) + en(e) + rep(e)
        for _ in range(2):
            for q, e, _p in a["conversa"]:
                r += en(e, q)
        for e, _ in a["frases"]:
            r += en(e) + rep(e)
        caps.append(cap(f"c{len(caps):02d}", a["titulo_en"], r,
                        "".join(f'<p lang="en">{html.escape(e)}</p>' for e, _ in a["frases"])))
    return caps


def desafio(aulas, nivel):
    caps = [cap("c00", "Abertura", pt(f"Desafio do nível {NOME_NIVEL[nivel]}. Agora é ao contrário: você ouve a frase em "
                                      "português e, depois do bipe, fala em inglês. Em seguida vem a resposta certa, e "
                                      "você repete mais uma vez. Errar aqui é ótimo: é o erro, seguido da resposta, que "
                                      "mais grava na memória."),
                "<p>Ouça em português, fale em inglês depois do bipe, confira a resposta e repita.</p>")]
    for a in aulas:
        r = pt(falado(a["titulo"]))
        for e, p in a["frases"]:
            r += pt("Como se diz em inglês: " + p) + rep(e) + en(e) + rep(e)
        caps.append(cap(f"c{len(caps):02d}", a["titulo"], r, "".join(html_frase(e, p) for e, p in a["frases"])))
    return caps


def detalhe(caps, aula=None):
    if aula is not None:
        nf, nc = len(aula["frases"]), 1 if aula["conversa"] else 0
        return f"{nf} frases" + (" e 1 conversa" if nc else "") if nf else "Como o curso funciona"
    return f"{len(caps) - 1} aulas"


def gravar(saida, pid, titulo, curto, dia, caps, info):
    pasta = saida / pid
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "conteudo.json").write_text(json.dumps(
        {"id": pid, "titulo": titulo, "curto": curto, "dia": dia, "capitulos": caps},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    trechos = sum(len(c["roteiro"]) for c in caps)
    print(f"{pid}: {len(caps)} capitulos, {trechos} trechos")
    return {"id": pid, "titulo": titulo, "curto": curto, "dia": dia, "seq": True,
            "capitulos": len(caps), "detalhe": info}


def main(saida):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    aulas = json.loads(CURSO.read_text(encoding="utf-8"))
    partes, por_nivel = [], {}
    # Sequência guiada: boas-vindas -> aulas do nível -> imersão do nível -> ... -> desafios -> recomeça
    for i, a in enumerate(aulas):
        nivel = NIVEIS[a["nivel"]]
        if nivel != "geral":
            por_nivel.setdefault(nivel, []).append(a)
        partes.append(gravar(saida, a["id"], a["titulo"], a["titulo"].split(" — ")[-1], nivel,
                             aula_completa(aulas, i), detalhe(None, a)))
        prox = aulas[i + 1] if i + 1 < len(aulas) else None
        if nivel != "geral" and (not prox or NIVEIS[prox["nivel"]] != nivel):
            k = list(NOME_NIVEL).index(nivel) + 1
            caps = imersao(por_nivel[nivel], nivel)
            partes.append(gravar(saida, f"i{k}_imersao_{nivel}", f"Imersão do nível {NOME_NIVEL[nivel]}",
                                 f"Imersão: nível {NOME_NIVEL[nivel]}", "imersao", caps, detalhe(caps)))
    for k, nivel in enumerate(NOME_NIVEL, 1):
        if nivel in por_nivel:
            caps = desafio(por_nivel[nivel], nivel)
            partes.append(gravar(saida, f"d{k}_desafio_{nivel}", f"Desafio do nível {NOME_NIVEL[nivel]}",
                                 f"Desafio: nível {NOME_NIVEL[nivel]}", "desafio", caps, detalhe(caps)))
    (saida / "partes.json").write_text(json.dumps(partes, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Total: {len(partes)} partes, {sum(len(a['frases']) for a in aulas)} frases")
    return 0


def duracoes(saida):
    """Depois da narração: copia a duração de cada audio.json para partes.json (mostrada no app)."""
    saida = Path(saida)
    partes = json.loads((saida / "partes.json").read_text(encoding="utf-8"))
    for p in partes:
        info = saida / p["id"] / "audio.json"
        if info.exists():
            p["duracao"] = json.loads(info.read_text(encoding="utf-8"))["duracao"]
    (saida / "partes.json").write_text(json.dumps(partes, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    total = sum(p.get("duracao", 0) for p in partes)
    print(f"Audio total: {total / 3600:.1f} h em {sum(1 for p in partes if 'duracao' in p)} de {len(partes)} partes")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pasta = args[0] if args else "dados"
    sys.exit(duracoes(pasta) if "--duracoes" in sys.argv else main(pasta))
