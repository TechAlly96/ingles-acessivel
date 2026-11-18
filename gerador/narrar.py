#!/usr/bin/env python3
"""Inglês Acessível - narra uma parte inteira em UM arquivo de áudio com capítulos.

Mesmo desenho do Concurso Acessível e do GIN (validado no celular), agora com três vozes:
- pt: narrador em português (pt_BR-faber-medium)
- a:  voz principal em inglês (en_US-ryan-medium)
- b:  segunda voz em inglês, nos diálogos (en_US-amy-medium)
O Piper roda como PROGRAMA SEPARADO e o ffmpeg converte para Opus.
Cada trecho (frase) é narrado uma vez e guardado em cache pelo hash do texto e da voz:
a mesma frase em inglês serve para a aula, a imersão e o desafio, e corrigir uma frase
só narra de novo aquela frase. Se nada mudou na parte, reaproveita o áudio já publicado.
Trecho "rep": bipe curto + silêncio proporcional à frase, para o aluno repetir em voz alta.
Uso: python3 gerador/narrar.py <parte> [--so-texto]
Variáveis: PIPER_PY, VOZES_DIR, AUDIO_CACHE, DADOS (padrão: dados).
NARRAR_TESTE=1 troca o Piper por tons de teste (para conferir a montagem sem as vozes)."""
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://techally96.github.io/ingles-acessivel/dados/"
VOZES = {"pt": "pt_BR-faber-medium", "a": "en_US-ryan-medium", "b": "en_US-amy-medium"}
TAXA = 22050              # todas as vozes são convertidas para esta taxa
LENTO = 0.8               # velocidade da frase lenta (ffmpeg atempo: muda o ritmo, não o tom)
SILENCIO_FRASE = "0.3"    # silêncio entre frases dentro de um mesmo trecho
ENTRE_TRECHOS = 0.35      # silêncio entre trechos de um capítulo
PAUSA_S = 0.9             # silêncio entre capítulos
REPETIR_FATOR = 1.6       # tempo para repetir = duração da frase x fator + folga
REPETIR_FOLGA = 1.0
VERSAO = "v1"             # mude para forçar nova narração de tudo
TESTE = os.environ.get("NARRAR_TESTE") == "1"


def ler(caminho, padrao=None):
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else padrao


def baixar_publicado(parte, arquivo, destino):
    try:
        req = urllib.request.Request(SITE + f"{parte}/{arquivo}", headers={"User-Agent": "ingles-acessivel"})
        with urllib.request.urlopen(req, timeout=120) as r:
            destino.write_bytes(r.read())
        return destino.stat().st_size > 0
    except Exception:
        return False


def silencio(seg):
    return b"\x00\x00" * int(TAXA * seg)


def bipe():
    """Bipe curto e suave (880 Hz, 0,15 s) que avisa: sua vez de falar."""
    n = int(TAXA * 0.15)
    amostras = (int(6000 * math.sin(2 * math.pi * 880 * i / TAXA) * min(1, i / 300, (n - i) / 300)) for i in range(n))
    return b"".join(struct.pack("<h", s) for s in amostras)


def para_pcm(arquivo, filtro=None):
    """Qualquer áudio -> PCM 16 bits mono na TAXA padrão."""
    cmd = ["ffmpeg", "-loglevel", "error", "-i", str(arquivo)] + (["-af", filtro] if filtro else []) + \
          ["-ar", str(TAXA), "-ac", "1", "-f", "s16le", "-"]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


class Narrador:
    def __init__(self, cache, tmp):
        self.cache, self.tmp = cache, Path(tmp)
        self.piper_py = os.environ.get("PIPER_PY", sys.executable)
        self.vozes = Path(os.environ.get("VOZES_DIR", "vozes")).resolve()
        self.novas = self.reaproveitadas = self.falhas = 0
        self.usados = set()

    def onnx(self, voz):
        modelo = self.vozes / f"{VOZES[voz]}.onnx"
        if not modelo.exists() and not TESTE:
            self.vozes.mkdir(parents=True, exist_ok=True)
            subprocess.run([self.piper_py, "-m", "piper.download_voices", VOZES[voz]], cwd=self.vozes, check=True)
        return modelo

    def sintetizar(self, voz, texto, wav):
        if TESTE:  # tom de teste com a duração aproximada da fala
            dur = max(0.4, len(texto) * 0.065)
            n = int(TAXA * dur)
            freq = {"pt": 300, "a": 500, "b": 650}[voz]
            with wave.open(str(wav), "wb") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(TAXA)
                w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * freq * i / TAXA))) for i in range(n)))
            return True
        base = [self.piper_py, "-m", "piper", "-m", str(self.onnx(voz)), "-f", str(wav)]
        r = None
        for extra in (["--sentence-silence", SILENCIO_FRASE], []):  # se a opção não existir, tenta sem
            r = subprocess.run(base + extra, input=texto, capture_output=True, text=True, timeout=600)
            if r.returncode == 0 and wav.exists() and wav.stat().st_size > 1000:
                return True
        print("   falha do Piper:", (r.stderr or "")[-300:])
        return False

    def trecho(self, voz, texto, lento=False):
        """PCM do trecho, do cache ou narrado agora. A versão lenta é derivada da normal."""
        chave = hashlib.sha1(f"{VERSAO}|{VOZES[voz]}|{SILENCIO_FRASE}|{'lento' + str(LENTO) if lento else ''}|{texto}"
                             .encode("utf-8")).hexdigest()[:16]
        item = self.cache / f"{chave}.flac"
        self.usados.add(item.name)
        if item.exists():
            self.reaproveitadas += 1
            return para_pcm(item)
        if lento:
            normal = self.trecho(voz, texto)
            fonte = self.tmp / "normal.wav"
            with wave.open(str(fonte), "wb") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(TAXA)
                w.writeframes(normal)
            pcm = para_pcm(fonte, f"atempo={LENTO}")
        else:
            wav = self.tmp / "novo.wav"
            wav.unlink(missing_ok=True)
            if not self.sintetizar(voz, texto, wav):
                self.falhas += 1
                return b""
            pcm = para_pcm(wav)
        # grava no cache de forma atômica (várias partes narram ao mesmo tempo)
        provisorio = self.cache / f".{chave}.{os.getpid()}.flac"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(TAXA), "-ac", "1",
                        "-i", "-", "-c:a", "flac", str(provisorio)], input=pcm, check=True)
        os.replace(provisorio, item)
        self.novas += 1
        return pcm

    def roteiro(self, roteiro):
        partes = []
        for t in roteiro:
            if "rep" in t:
                frase = self.trecho(t["rep"], t["t"])
                dur = len(frase) / 2 / TAXA
                partes.append(bipe() + silencio(dur * REPETIR_FATOR + REPETIR_FOLGA))
            else:
                pcm = self.trecho(t["v"], t["t"], t.get("lento", False))
                if pcm:
                    partes.append(pcm + silencio(ENTRE_TRECHOS))
        return b"".join(partes)


def main(parte):
    pasta = Path(os.environ.get("DADOS", "dados")) / parte
    conteudo = ler(pasta / "conteudo.json")
    if not conteudo:
        raise SystemExit(f"{parte}: conteudo.json não encontrado (rode montar_dados.py antes)")
    caps = conteudo["capitulos"]
    base = json.dumps([VERSAO, VOZES, LENTO, SILENCIO_FRASE, ENTRE_TRECHOS, PAUSA_S, REPETIR_FATOR, REPETIR_FOLGA,
                       [c["roteiro"] for c in caps]], ensure_ascii=False, sort_keys=True)
    assinatura = hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
    arquivo = f"audio-{assinatura}.ogg"
    if "--so-texto" in sys.argv:
        total = sum(len(t["t"]) for c in caps for t in c["roteiro"])
        print(f"{parte}: {len(caps)} capitulos | {total} caracteres | {arquivo}")
        return 0
    anterior = ler(pasta / "audio.json", {})
    destino = pasta / arquivo
    if not TESTE:
        if anterior.get("assinatura") == assinatura and (destino.exists() or baixar_publicado(parte, arquivo, destino)):
            print(f"{parte}: sem mudanca, audio reaproveitado ({arquivo})")
            return 0
        if not anterior:
            publicado = Path(tempfile.gettempdir()) / f"{parte}-audio.json"
            if baixar_publicado(parte, "audio.json", publicado):
                anterior = ler(publicado, {})
                if anterior.get("assinatura") == assinatura and baixar_publicado(parte, arquivo, destino):
                    (pasta / "audio.json").write_text(publicado.read_text(encoding="utf-8"), encoding="utf-8")
                    print(f"{parte}: sem mudanca, audio publicado reaproveitado ({arquivo})")
                    return 0
    cache = Path(os.environ.get("AUDIO_CACHE", "audio-cache")) / "trechos"
    cache.mkdir(parents=True, exist_ok=True)
    marcas, t = [], 0.0
    with tempfile.TemporaryDirectory() as tmp:
        narrador = Narrador(cache, tmp)
        junto = Path(tmp) / "parte.pcm"
        with open(junto, "wb") as saida:
            for n, c in enumerate(caps):
                pcm = narrador.roteiro(c["roteiro"])
                dur = len(pcm) / 2 / TAXA
                marcas.append({"id": c["id"], "inicio": round(t, 2), "fim": round(t + dur, 2)})
                saida.write(pcm + silencio(PAUSA_S))
                t += dur + PAUSA_S
                print(f"   {parte} [{n + 1}/{len(caps)}] {c['titulo'][:60]}", flush=True)
        if t <= len(caps) * PAUSA_S + 0.1:
            raise SystemExit(f"{parte}: nada foi narrado ({narrador.falhas} falhas)")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(TAXA), "-ac", "1",
                        "-i", str(junto), "-c:a", "libopus", "-b:a", "32k", "-ac", "1", "-application", "voip",
                        str(destino)], check=True)
    for velho in pasta.glob("audio-*.ogg"):
        if velho.name != arquivo:
            velho.unlink()
    (pasta / "audio.json").write_text(json.dumps({
        "parte": parte, "gerado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vozes": VOZES, "arquivo": arquivo, "assinatura": assinatura, "duracao": round(t, 1),
        "bytes": destino.stat().st_size, "falhas": narrador.falhas, "capitulos": marcas,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{parte}: audio gerado | {t / 60:.1f} min | {destino.stat().st_size // 1024} KB | falhas {narrador.falhas} "
          f"| trechos novos {narrador.novas}, do cache {narrador.reaproveitadas} | {arquivo}")
    return 0 if not narrador.falhas else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
