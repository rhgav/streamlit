import streamlit as st
import websocket
from datetime import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import ssl
import os
from wsgiref.handlers import format_date_time
from time import mktime
import _thread as thread

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 解析URL类
class Url:
    def __init__(self, host, path, schema):
        self.host = host
        self.path = path
        self.schema = schema


class Ws_Param:
    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID, "status": 2}

        # 业务参数(business)
        self.BusinessArgs = {
            "tts": {
                "vcn": "x4_lingxiaoxuan_oral",  # 发音人
                "volume": 50,  # 音量
                "rhy": 0,  # 是否返回拼音标注
                "speed": 50,  # 语速
                "pitch": 50,  # 音调
                "bgs": 0,  # 背景音
                "reg": 0,  # 英文发音方式
                "rdn": 0,  # 数字发音方式
                "audio": {
                    "encoding": "lame",  # 音频格式
                    "sample_rate": 24000,  # 采样率
                    "channels": 1,  # 声道数
                    "bit_depth": 16,  # 位深
                }
            }
        }

        # 文本数据
        self.Data = {
            "text": {
                "encoding": "utf8",
                "compress": "raw",
                "format": "plain",
                "status": 2,
                "seq": 0,
                "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")  # base64编码
            }
        }


# 计算sha256并编码为base64
def sha256base64(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    digest = base64.b64encode(sha256.digest()).decode(encoding='utf-8')
    return digest


# 解析URL
def parse_url(request_url):
    stidx = request_url.index("://")
    host = request_url[stidx + 3:]
    schema = request_url[:stidx + 3]
    edidx = host.index("/")
    if edidx <= 0:
        raise Exception("invalid request url:" + request_url)
    path = host[edidx:]
    host = host[:edidx]
    u = Url(host, path, schema)
    return u


# 构建WebSocket认证请求URL
def assemble_ws_auth_url(request_url, method="GET", api_key="", api_secret=""):
    u = parse_url(request_url)
    host = u.host
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(host, date, method, path)
    signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
    authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
        api_key, "hmac-sha256", "host date request-line", signature_sha)
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }
    return request_url + "?" + urlencode(values)


# WebSocket收到消息处理
def on_message(ws, message):
    try:
        message = json.loads(message)
        code = message["header"]["code"]
        sid = message["header"]["sid"]
        if "payload" in message:
            audio = message["payload"]["audio"]['audio']
            audio = base64.b64decode(audio)
            status = message["payload"]['audio']["status"]
            if status == 2:
                ws.close()
            if code != 0:
                errMsg = message["message"]
                print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
            else:
                with open('../demo.mp3', 'ab') as f:
                    f.write(audio)

    except Exception as e:
        print("Error parsing message:", e)


# WebSocket错误处理
def on_error(ws, error):
    print("Error:", error)


# WebSocket关闭处理
def on_close(ws):
    print("WebSocket closed")


# WebSocket连接建立处理
def on_open(ws):
    def run(*args):
        d = {"header": wsParam.CommonArgs,
             "parameter": wsParam.BusinessArgs,
             "payload": wsParam.Data,
             }
        d = json.dumps(d)
        ws.send(d)
        if os.path.exists('../demo.mp3'):
            os.remove('../demo.mp3')

    thread.start_new_thread(run, ())


# Streamlit页面
st.set_page_config(page_title="文生语音应用")

st.title('🎤 文生语音应用 🎶')

appid = 'ebd7d2f3'
apisecret = 'NTk4Nzk0NDU2ZWIyNTE5NmRmNTdhNTcz'
apikey = '162511796bb0bd52d0920700da21585e'

with st.form("语音生成表单"):
    text_input = st.text_area("请输入文本", "我爱编程，欢迎使用文生语音应用！")
    submitted = st.form_submit_button("生成语音")

    if submitted:
        with st.spinner("正在生成语音..."):
            # 初始化Ws_Param对象
            wsParam = Ws_Param(APPID=appid, APISecret=apisecret, APIKey=apikey, Text=text_input)
            requrl = 'wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6'
            wsUrl = assemble_ws_auth_url(requrl, "GET", apikey, apisecret)
            ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
            ws.on_open = on_open
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

            # 提供下载链接
            if os.path.exists('../demo.mp3'):
                st.audio('./demo.mp3', format='audio/mp3')
                st.success("语音生成完成！")
