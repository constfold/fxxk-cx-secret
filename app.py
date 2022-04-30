#!/bin/python3

import json
import traceback
import urllib.parse
from pathlib import Path
import difflib

import requests
from flask import Flask, request

from sec_font import secFont2Map, secFontDec, secFontEnc

app = Flask(__name__)


class CacheDAO:
    def __init__(self, file='cache.json'):
        self.cacheFile = Path(file)
        if not self.cacheFile.is_file():
            self.cacheFile.open('w').write('{}')
        self.fp = self.cacheFile.open('r+', encoding='utf8')

    def getCache(self, question):
        self.fp.seek(0)
        data = json.load(self.fp)
        if isinstance(data, dict):
            return data.get(question)

    def addCache(self, question, answer):
        self.fp.seek(0)
        data: dict = json.load(self.fp)
        data.update({question: answer})
        self.fp.seek(0)
        json.dump(data, self.fp, ensure_ascii=False, indent=4)


cache = CacheDAO()

API_HOST = 'http://119.6.233.156:309/xuexitong'


def searchTimu(q, options, cx_id, html, url, course):
    headers = {
        'Content-type': 'application/x-www-form-urlencoded'
    }
    data = 'question=' + urllib.parse.quote(q)\
        + '&options=' + urllib.parse.quote(options)\
        + '&cx_id=' + cx_id\
        + '&html=' + urllib.parse.quote(html)\
        + '&url=' + urllib.parse.quote(url)\
        + '&course=' + urllib.parse.quote(course)\
        + '&version=8.0.13'
    res = requests.post(API_HOST + '/temporary_sea',
                        headers=headers, data=data)

    j = json.loads(res.content)
    print(j)
    return j['data']


def searchView():
    try:
        # 过滤请求问题
        if request.method == 'GET':
            question = request.args['question']
            fontHash = None
            fontText = None
        elif request.method == 'POST':
            # formData = dict(urllib.parse.parse_qsl(request.data.decode()))
            formData = request.form
            question = formData['question']
            if (targetAnswers := formData.get('answers')):
                targetAnswers = targetAnswers.split('#')[1:]
            else:
                targetAnswers = None
            if (secFontB64 := formData.get('secFont')):
                (fontText, fontHash) = secFont2Map(secFontB64)  # 计算加密字体hashMap
                question = secFontDec(fontHash, fontText, question)  # 解码加密字体
                print(question)
            else:
                fontHash = None
                fontText = None
        question = (
            question
            .replace('题型说明：请输入题型说明', '')
            .strip('\x0a\x09')
        )
        answer = cache.getCache(question)
        hit = True
        if answer is None:
            opt = formData['options']
            cx_id = formData['cx_id']
            html = formData['html']
            url = formData['url']
            course = formData['course']
            answer = searchTimu(question, opt, cx_id,
                                html, url, course)  # 进行搜题
            cache.addCache(question, answer)
            hit = False

        print(f'原始答案: {answer}')
        # 直接命中原目标答案
        if answer != '错误' and answer != '正确':
            if targetAnswers is not None:
                for originAnswer in targetAnswers:
                    if difflib.SequenceMatcher(
                        None,
                        secFontDec(fontHash, fontText, originAnswer) if (
                            fontHash is not None) else originAnswer,
                        answer
                    ).quick_ratio() >= 0.95:  # 比较答案相似度
                        answer = originAnswer
                        break
            # 编码答案文本 (可能不一一对应)
            else:
                answer = secFontEnc(fontHash, answer)

        return {
            "code": 1,
            "messsage": "",
            "data": answer,
            "hit": hit,
            "encryption": (fontHash is not None)
        }
    except Exception as err:
        traceback.print_exc()
        return {
            "code": -1,
            "messsage": err.__str__(),
            "data": "🙌没有人 👐比我 ☝️更懂 👌做题"
        }


def notice():
    return ''


app.add_url_rule('/temporary_sea', 'search',
                 searchView, methods=['GET', 'POST'])

app.add_url_rule('/cxtimu/notice', 'notice', notice, methods=['GET'])

app.run('0.0.0.0', 88)
