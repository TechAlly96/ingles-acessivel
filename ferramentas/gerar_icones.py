#!/usr/bin/env python3
"""Gera os ícones do app (requer Pillow; rodar uma vez, os PNG ficam no repositório)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

APP = Path(__file__).resolve().parent.parent / "app"
FUNDO, AMARELO, BRANCO = (7, 18, 38), (255, 210, 63), (255, 255, 255)


def fonte(tam):
    for nome in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nome, tam)
        except OSError:
            pass
    return ImageFont.load_default(tam)


def desenhar(tam, margem):
    img = Image.new("RGB", (tam, tam), FUNDO)
    d = ImageDraw.Draw(img)
    s = (tam - 2 * margem * tam / 512) / 512   # escala dentro da área segura
    o = margem * tam / 512                     # deslocamento da margem
    P = lambda x, y: (o + x * s, o + y * s)
    # fone de ouvido: arco + duas conchas (ouvir)
    d.arc([*P(96, 96), *P(416, 416)], 180, 360, fill=AMARELO, width=int(34 * s))
    for x in (96, 352):
        d.rounded_rectangle([*P(x, 250), *P(x + 64, 390)], radius=int(22 * s), fill=AMARELO)
    # balão de fala com "EN" (falar inglês)
    d.rounded_rectangle([*P(176, 236), *P(336, 352)], radius=int(26 * s), fill=BRANCO)
    d.polygon([P(206, 346), P(250, 346), P(198, 392)], fill=BRANCO)
    d.text(P(256, 294), "EN", fill=FUNDO, font=fonte(int(70 * s)), anchor="mm")
    return img


desenhar(192, 0).save(APP / "icone-192.png")
desenhar(512, 0).save(APP / "icone-512.png")
desenhar(512, 60).save(APP / "icone-maskable-512.png")
print("icones gerados")
