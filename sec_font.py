import base64
import hashlib
import re
import sqlite3
from io import BytesIO
from pathlib import Path
from typing import IO, Dict, Union, Tuple

from colorama import Back, Fore, Style
from fontTools.ttLib.ttFont import TTFont
from cnocr import CnOcr
import numpy as np

from PIL import ImageFont, Image, ImageDraw

ocr = CnOcr()


class FontHashDAO:
    def __init__(self, file='sqlite.db'):
        self.conn = sqlite3.connect(file)

    def findChar(self, fontHash: str, enc: str) -> str:
        cur = self.conn.execute(
            "SELECT ch FROM textmap WHERE font_hash=(?) and enc_ch=(?)", (fontHash, enc))
        if resp := cur.fetchone():
            return resp[0]

    def findHash(self, fontHash: str, char: str) -> str:
        cur = self.conn.execute(
            "SELECT enc_ch FROM textmap WHERE ch=(?) and font_hash=(?)", (char, fontHash))
        if resp := cur.fetchone():
            return resp[0]

    def fontExist(self, font) -> bool:
        cur = self.conn.execute(
            'SELECT COUNT(*) FROM textmap WHERE font_hash=(?)', (font,))
        if resp := cur.fetchone():
            return resp[0] != 0

    def addKv(self, k: str, v: str, font: str):
        self.conn.execute(
            'INSERT INTO textmap VALUES ((?),(?),(?))', (v, font, k))
        self.conn.commit()


def secFont2Map(file: Union[IO, Path, str]) -> Tuple[str, str]:
    '以加密字体计算hashMap'
    dao = FontHashDAO()
    if isinstance(file, str):
        file = base64.b64decode(file[47:])

    if isinstance(file, Path):
        desc = file.open('rb')
        file = desc.read()
        desc.close()
    tt = TTFont(BytesIO(file))
    text = getAllGlyphInFont(tt)
    hash = hashlib.sha256(file).digest().hex()
    if not dao.fontExist(hash):
        # build unrecognized font
        m = recognizeFont(file, text)
        for (k, v) in m.items():
            dao.addKv(k, v, hash)

    return (text, hash)


def getAllGlyphInFont(font: TTFont) -> str:
    glyph = ''
    for table in font['cmap'].tables:
        for g in table.cmap.keys():
            glyph += chr(g)
    return glyph


def recognizeFont(font: bytes, text: str) -> Dict[str, str]:
    font = ImageFont.truetype(BytesIO(font), 14)

    (width, height) = font.getsize(text)
    img = Image.new("L", (width, height), (255,))
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), text, font=font)
    pix = np.asarray(img)
    t = ocr.ocr(pix)

    # only rendered in single line
    assert len(t) == 1
    (rawtext, c) = t[0]

    # could not be less
    assert c > 0.5

    textMap = {}
    assert len(rawtext) == len(text)
    for (k, v) in zip(text, rawtext):
        textMap[k] = v

    return textMap


def secFontDec(fontHash, fontText, source) -> str:
    '解码字体加密'
    dao = FontHashDAO()
    resultStr = ''
    for char in source:
        if char in fontText:
            originChar = dao.findChar(fontHash, char)
            if originChar is not None:
                resultStr += originChar
            else:
                print(Fore.RED+f'解码失败: {char}({fontHash})'+Fore.RESET)
        else:
            resultStr += char
    print(Fore.GREEN+f'字体加密解码: {source} -> {resultStr}'+Fore.RESET)
    return resultStr


def secFontEnc(hashMap, source) -> str:
    '编码字体加密'
    dao = FontHashDAO()
    hashMap = dict(zip(hashMap.values(), hashMap.keys()))
    resultStr = ''
    for char in source:
        if (fontHash := dao.findHash(char)):
            if (unicodeID := hashMap.get(fontHash)):
                if (result := re.match(r'^uni([0-9A-Z]{4})$', unicodeID)):
                    encChar = chr(int(result.group(1), 16))
                    resultStr += encChar
            else:
                resultStr += char
        else:
            resultStr += char
    print(Fore.GREEN+f'字体加密编码: {source} -> {resultStr}'+Fore.RESET)
    return resultStr


if __name__ == "__main__":
    import rich
    (fontText, fontHash) = secFont2Map(Path('cx-secret.ttf'))
    rich.print(fontText, fontHash)
    p = secFontDec(fontHash, fontText, "为了实圷圵华圸族伟圳复兴,圴个圼圲圵壙共产党圶结带领圵壙人圸创造的伟圳成圻")
    print(p)
