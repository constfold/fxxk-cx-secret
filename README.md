# 处理超星学习通字体加密

基于 <https://github.com/SocialSisterYi/xuexiaoyi-to-xuexitong-tampermonkey-proxy>

## 接口

删除（我无法使用）的学小易接口，替换成了随便找的一个接口。**请求被风控的问题请自行解决。**

## OCR

通过 `CnOCR` 进行自动识别，请根据具体情况自行替换。

另外，在实际使用中，由于几乎每个答题页面都会随机生成一个字体，所以有时会出现不同的字体中有同一个加密文字使用多次的问题，所以我修改了数据库结构使加密字典以字体为单位。

## 使用

1. 安装 <https://greasyfork.org/zh-CN/scripts/443325>
2. 将 `API_HOST` 替换为你的主机和端口，如 `http://192.168.1.1:88`
3. 加入将主机名加入跨域
```javascript
// @connect        192.168.1.1
```

4. 在 `findAnswer` 修改
```javascript
// 拾取加密字体
var secFont = '';
if($TiMu.find(".font-cxsecret").length != 0){
    secFont = $("style[type='text/css']").text().match(/'(data:application\/font-ttf;.*?)'/)[1];
}
// 回传答案用以后端命中
var answers = $TiMu.find("a"),
    answersText='';
for(var i=0;i<answers.length;i++){
    answersText += ('#'+filterImg(answers.eq(i)));
}
GM_xmlhttpRequest({
    method: "POST",
    url: api_array[setting.api],
    data:'question='+encodeURIComponent(question)+'&answers='+encodeURIComponent(answersText)+'&secFont='+encodeURIComponent(secFont)+//原有的
```

  如需使用其他接口请自行依照情况替换 `app.py` 里的方法。