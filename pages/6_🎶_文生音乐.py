import streamlit as st
import json
import time
import requests
import Sign
import mysql.connector
from mysql.connector import Error
from Home import record_app_access  # 假设主代码文件名为 Home.py

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 记录用户访问应用
record_app_access(st.session_state.user_id, "music_generation")


# ----------------- 数据库连接函数 -----------------
def create_connection():
    try:
        conn = mysql.connector.connect(
            host='dbconn.sealosbja.site',  # 替换为你的公网IP或域名
            port=43789,  # 明确指定端口，MySQL默认是3306
            user='root',  # 替换为你的MySQL用户名
            password='12345678',  # 替换为你的MySQL密码
            database='chatbot_db'  # 替换为你的数据库名
        )
        return conn
    except Error as e:
        st.error(f"连接数据库时发生错误: {str(e)}")
        return None


# ----------------- 数据库操作函数 -----------------
def save_doubao_history(chat_id, role, message, generation_method=None, gender=None, genre=None, mood=None,
                        timbre=None):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO doubao_music_history 
                          (chat_id, role, message, generation_method, gender, genre, mood, timbre)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                       (chat_id, role, message, generation_method, gender, genre, mood, timbre))
        conn.commit()
    except Error as e:
        st.error(f"保存豆包历史记录时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def save_suno_history(chat_id, role, message, is_instrumental=None,
                      music1_title=None, music1_video=None, music1_tags=None,
                      music2_title=None, music2_video=None, music2_tags=None):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO suno_music_history 
                          (chat_id, role, message, is_instrumental,
                           music1_title, music1_video, music1_tags,
                           music2_title, music2_video, music2_tags)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                       (chat_id, role, message, is_instrumental,
                        music1_title, music1_video, music1_tags,
                        music2_title, music2_video, music2_tags))
        conn.commit()
    except Error as e:
        st.error(f"保存Suno历史记录时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def load_doubao_history(chat_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT role, message, generation_method, gender, genre, mood, timbre 
                          FROM doubao_music_history 
                          WHERE chat_id = %s ORDER BY timestamp''', (chat_id,))
        history = cursor.fetchall()
        return history
    except Error as e:
        st.error(f"加载豆包历史记录时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


def load_suno_history(chat_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT role, message, is_instrumental, 
                                 music1_title, music1_video, music1_tags,
                                 music2_title, music2_video, music2_tags
                          FROM suno_music_history 
                          WHERE chat_id = %s ORDER BY timestamp''', (chat_id,))
        history = cursor.fetchall()
        return history
    except Error as e:
        st.error(f"加载Suno历史记录时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


def create_new_music_chat(user_id, model_type):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO music_chats (user_id, model_type) VALUES (%s, %s)',
                       (user_id, model_type))
        conn.commit()
        chat_id = cursor.lastrowid
        return chat_id
    except Error as e:
        st.error(f"创建新音乐对话时发生错误: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            conn.close()


def delete_music_chat(chat_id):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM music_chats WHERE id = %s', (chat_id,))
        cursor.execute('DELETE FROM doubao_music_history WHERE chat_id = %s', (chat_id,))
        cursor.execute('DELETE FROM suno_music_history WHERE chat_id = %s', (chat_id,))
        conn.commit()
    except Error as e:
        st.error(f"删除音乐对话时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def get_user_music_chats(user_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(''' 
            SELECT c.id, 
                   c.model_type,
                   DATE(c.timestamp) as chat_date,
                   TIME_FORMAT(c.timestamp, '%H:%i') as chat_time,
                   COALESCE((
                       SELECT SUBSTRING(message,1,30) 
                       FROM doubao_music_history 
                       WHERE chat_id = c.id AND role = 'user' 
                       ORDER BY timestamp ASC LIMIT 1
                   ), (
                       SELECT SUBSTRING(message,1,30) 
                       FROM suno_music_history 
                       WHERE chat_id = c.id AND role = 'user' 
                       ORDER BY timestamp ASC LIMIT 1
                   ), '新对话') as preview
            FROM music_chats c
            WHERE c.user_id = %s
            ORDER BY c.timestamp DESC
        ''', (user_id,))
        chats = cursor.fetchall()
        return chats
    except Error as e:
        st.error(f"获取用户音乐对话列表时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


# ----------------- 豆包模型相关函数 -----------------
STATUS_CODE_SUCCESS = 0
QUERY_STATUS_CODE_WAITING = 0
QUERY_STATUS_CODE_HANDING = 1
QUERY_STATUS_CODE_SUCCESS = 2
QUERY_STATUS_CODE_FAILED = 3

# 豆包API配置
ACTION_GEN = "GenSongV4"
ACTION_QUERY = "QuerySong"
VERSION = "2024-08-12"
REGION = "cn-beijing"
SERVICE = 'imagination'
HOST = "open.volcengineapi.com"
PATH = "/"


def get_response(response):
    """解析API响应"""
    response_json = json.loads(response.text)
    return (
        response_json.get('Code'),
        response_json.get('Message'),
        response_json.get('Result'),
        response_json.get('ResponseMetadata')
    )


def generate_song(input_type, input_content, gender, genre, mood, timbre, ak, sk):
    """生成歌曲"""
    query = {'Action': ACTION_GEN, 'Version': VERSION}
    body = {
        'Gender': gender,
        'Genre': genre,
        'Mood': mood,
        'Timbre': timbre,
    }

    # 根据输入类型设置不同的参数
    if input_type == "根据提示词生成":
        body['Prompt'] = input_content
    else:  # Lyrics
        body['Lyrics'] = input_content

    x_content_sha256 = Sign.hash_sha256(json.dumps(body))
    headers = {
        "Content-Type": 'application/json',
        'Host': HOST,
        'X-Date': Sign.get_x_date(),
        'X-Content-Sha256': x_content_sha256
    }

    authorization = Sign.get_authorization(
        "POST", headers=headers, query=query,
        service=SERVICE, region=REGION, ak=ak, sk=sk
    )
    headers["Authorization"] = authorization

    response = requests.post(
        Sign.get_url(HOST, PATH, ACTION_GEN, VERSION),
        data=json.dumps(body),
        headers=headers
    )

    code, message, result, _ = get_response(response)
    if code != STATUS_CODE_SUCCESS or not response.ok:
        raise RuntimeError(response.text)

    return result['TaskID'], result['PredictedWaitTime'] + 5


def query_song(task_id, ak, sk):
    """查询歌曲生成状态"""
    body = {'TaskID': task_id}
    x_content_sha256 = Sign.hash_sha256(json.dumps(body))

    query = {'Action': ACTION_QUERY, 'Version': VERSION}
    headers = {
        "Content-Type": 'application/json',
        'Host': HOST,
        'X-Date': Sign.get_x_date(),
        'X-Content-Sha256': x_content_sha256
    }

    authorization = Sign.get_authorization(
        "POST", headers=headers, query=query,
        service=SERVICE, region=REGION, ak=ak, sk=sk
    )
    headers["Authorization"] = authorization

    while True:
        response = requests.post(
            Sign.get_url(HOST, PATH, ACTION_QUERY, VERSION),
            data=json.dumps(body),
            headers=headers
        )

        if not response.ok:
            raise RuntimeError(response.text)

        code, message, result, _ = get_response(response)
        status = result.get('Status')

        if status == QUERY_STATUS_CODE_FAILED:
            raise RuntimeError(response.text)
        elif status == QUERY_STATUS_CODE_SUCCESS:
            return result.get('SongDetail')
        elif status == QUERY_STATUS_CODE_WAITING or status == QUERY_STATUS_CODE_HANDING:
            time.sleep(5)
        else:
            raise RuntimeError("未知状态")


# ----------------- Suno模型相关函数 -----------------
def submit_music_task(prompt, is_instrumental, api_key):
    """提交音乐生成任务"""
    endpoint = "https://api.ttapi.io/suno/v1/music"
    headers = {
        "Content-Type": "application/json",
        "TT-API-KEY": api_key
    }
    data = {
        "mv": "chirp-v4",
        "custom": "false",
        "instrumental": str(is_instrumental).lower(),
        "gpt_description_prompt": prompt,
    }
    response = requests.post(endpoint, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get('data', {}).get('jobId')
    st.error(f"提交失败，状态码：{response.status_code}")
    return None


def check_music_status(job_id, api_key):
    """检查音乐生成状态"""
    endpoint = "https://api.ttapi.io/suno/v1/fetch"
    headers = {
        "Content-Type": "application/json",
        "TT-API-KEY": api_key
    }
    response = requests.post(endpoint, headers=headers, json={"jobId": job_id})
    if response.status_code == 200:
        return response.json()
    st.error(f"状态查询失败，状态码：{response.status_code}")
    return None


def generate_music(prompt, is_instrumental, api_key):
    """生成音乐主流程"""
    try:
        job_id = submit_music_task(prompt, is_instrumental, api_key)
        if not job_id:
            return None

        # 最长等待10分钟（每30秒检查一次）
        for _ in range(20):
            time.sleep(30)
            result = check_music_status(job_id, api_key)
            if not result:
                continue

            status = result.get('status')
            if status == 'SUCCESS':
                return result.get('data', {}).get('musics', [])
            if status in ['FAILED', 'CANCELLED']:
                st.error(f"生成失败：{result.get('message')}")
                return None

        st.error("生成超时，请稍后重试")
        return None
    except Exception as e:
        st.error(f"发生异常：{str(e)}")
        return None


# ----------------- 页面布局和主逻辑 -----------------
# 页面配置
st.set_page_config(page_title="AI音乐生成", page_icon="🎵")
st.title("🎵 AI音乐生成")

# 获取用户对话
chats = get_user_music_chats(st.session_state.user_id)


# 显示对话选择器
def display_chat_selector(chats):
    st.sidebar.markdown("## 历史对话")
    date_groups = {}
    for chat in chats:
        date = chat[2]  # chat_date
        if date not in date_groups:
            date_groups[date] = []
        date_groups[date].append(chat)

    for date in sorted(date_groups.keys(), reverse=True):
        with st.sidebar.expander(f"🗓️ {date}"):
            for chat in date_groups[date]:
                chat_id, model_type, _, time, preview = chat
                model_name = "豆包" if model_type == "doubao" else "Suno"
                btn_text = f"{time[:5]} | {model_name} | {preview[:20]}..."
                if st.button(btn_text, key=f"music_chat_{chat_id}"):
                    st.session_state.music_chat_id = chat_id
                    st.session_state.music_model_type = model_type
                    st.session_state.show_message = f"success|已加载对话 [{time[:5]}]"
                    st.rerun()


display_chat_selector(chats)

# 新建对话按钮
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("✨ 新建豆包对话"):
        chat_id = create_new_music_chat(st.session_state.user_id, "doubao")
        st.session_state.music_chat_id = chat_id
        st.session_state.music_model_type = "doubao"
        st.session_state.show_message = "success|豆包对话创建成功"
        st.rerun()

with col2:
    if st.button("✨ 新建Suno对话"):
        chat_id = create_new_music_chat(st.session_state.user_id, "suno")
        st.session_state.music_chat_id = chat_id
        st.session_state.music_model_type = "suno"
        st.session_state.show_message = "success|Suno对话创建成功"
        st.rerun()

# 添加API密钥输入
st.sidebar.markdown("## API配置")

if 'music_model_type' in st.session_state:
    if st.session_state.music_model_type == "doubao":
        st.sidebar.markdown("### 豆包API配置")
        doubao_ak = st.sidebar.text_input("输入豆包AK", key="doubao_ak")
        doubao_sk = st.sidebar.text_input("输入豆包SK", type="password", key="doubao_sk")
    elif st.session_state.music_model_type == "suno":
        st.sidebar.markdown("### Suno API配置")
        suno_api_key = st.sidebar.text_input("输入Suno API Key", type="password", key="suno_api_key")

# 提示信息处理
if 'show_message' in st.session_state:
    msg_type, message = st.session_state.show_message.split("|")
    if msg_type == "success":
        st.success(message)
    elif msg_type == "info":
        st.info(message)
    del st.session_state.show_message

# 确保用户选择了对话
if 'music_chat_id' not in st.session_state or st.session_state.music_chat_id is None:
    st.warning("请先选择对话或新建对话")
    st.stop()

# 检查API密钥是否已提供
if st.session_state.music_model_type == "doubao":
    if 'doubao_ak' not in st.session_state or not st.session_state.doubao_ak or \
       'doubao_sk' not in st.session_state or not st.session_state.doubao_sk:
        st.warning("请先在侧边栏输入豆包AK和SK")
        st.stop()
elif st.session_state.music_model_type == "suno":
    if 'suno_api_key' not in st.session_state or not st.session_state.suno_api_key:
        st.warning("请先在侧边栏输入Suno API Key")
        st.stop()

# 显示当前模型类型
if st.session_state.music_model_type == "doubao":
    st.markdown("### 当前模型: 豆包音乐生成模型")
else:
    st.markdown("### 当前模型: Suno音乐生成模型")

# 显示历史对话
if st.session_state.music_model_type == "doubao":
    history = load_doubao_history(st.session_state.music_chat_id)
    for role, message, method, gender, genre, mood, timbre in history:
        with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
            st.markdown(message)
            if role == "user":
                st.caption(f"生成方式: {method} | 性别: {gender} | 风格: {genre} | 情绪: {mood} | 音色: {timbre}")

    # 豆包模型输入表单
    with st.form("doubao_form"):
        # 添加输入类型选择
        input_type = st.radio("选择生成方式:", ["根据提示词生成", "根据歌词生成"])

        input_content = st.text_area("描述你想创作的歌曲内容:",
                                     placeholder="例如: 写一首关于烟花的歌",
                                     height=100)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            gender = st.selectbox("歌手性别:", ["Female", "Male"])
        with col2:
            genre = st.selectbox("音乐风格:",
                                 ["Folk", "Pop", "Rock", "Chinese Style", "Hip Hop/Rap", "R&B/Soul", "Punk",
                                  "Electronic", "Jazz", "Reggae", "DJ", "Pop Punk", "Disco", "Future Bass",
                                  "Pop Rap", "Trap Rap", "R&B Rap", "Chinoiserie Electronic", "GuFeng Music",
                                  "Pop Rock", "Jazz Pop", "Bossa Nova", "Contemporary R&B"])
        with col3:
            mood = st.selectbox("歌曲情绪:", ['Happy', 'Dynamic/Energetic', 'Sentimental/Melancholic/Lonely',
                                              'Inspirational/Hopeful', 'Nostalgic/Memory', 'Excited', 'Sorrow/Sad',
                                              'Chill', 'Romantic', 'Miss', 'Groovy/Funky', 'Dreamy/Ethereal',
                                              'Calm/Relaxing'])
        with col4:
            timbre = st.selectbox("歌曲音色:",
                                  ["Warm", "Bright", "Husky", "Electrified voice", "Sweet_AUDIO_TIMBRE",
                                   "Cute_AUDIO_TIMBRE", "Loud and sonorous", "Powerful", "Sexy/Lazy"])
        submitted = st.form_submit_button("生成音乐")

    if submitted and input_content:
        # 保存用户输入
        save_doubao_history(st.session_state.music_chat_id, "user", input_content,
                            input_type, gender, genre, mood, timbre)

        with st.spinner("正在生成音乐，请稍候..."):
            try:
                task_id, wait_time = generate_song(input_type, input_content, gender, genre, mood, timbre,
                                                  st.session_state.doubao_ak, st.session_state.doubao_sk)
                song_detail = query_song(task_id, st.session_state.doubao_ak, st.session_state.doubao_sk)

                if song_detail:
                    audio_url = song_detail.get('AudioUrl')
                    st.success("音乐生成成功！")
                    st.write(audio_url)
                    # 保存AI输出
                    save_doubao_history(st.session_state.music_chat_id, "assistant", audio_url)
                    st.rerun()
                else:
                    st.error("未能获取音乐文件")
            except Exception as e:
                st.error(f"生成音乐时出错: {str(e)}")
                delete_music_chat(st.session_state.music_chat_id)
                st.session_state.music_chat_id = None
                st.rerun()

elif st.session_state.music_model_type == "suno":
    history = load_suno_history(st.session_state.music_chat_id)
    for role, message, is_instrumental, title1, video1, tags1, title2, video2, tags2 in history:
        with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
            if role == "user":
                st.markdown(message)
                st.caption(f"纯音乐: {'是' if is_instrumental else '否'}")
            else:
                st.success("🎉 生成成功！为您推荐以下两首音乐：")
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(title1)
                    st.video(video1)
                    st.caption(f"风格标签: {tags1}")
                with col2:
                    st.subheader(title2)
                    st.video(video2)
                    st.caption(f"风格标签: {tags2}")

    # Suno模型输入表单
    with st.form('suno_form'):
        prompt = st.text_area(
            '请输入音乐描述：',
            '例如：一首充满节日气氛的圣诞歌曲，包含铃铛声和欢快的节奏',
            height=150
        )
        is_instrumental = st.checkbox("生成纯音乐（无歌词）")
        submitted = st.form_submit_button('生成音乐')

    if submitted and prompt:
        # 保存用户输入
        save_suno_history(st.session_state.music_chat_id, "user", prompt, is_instrumental)

        with st.spinner("⏳ 正在生成音乐，这可能需要5-10分钟，请耐心等待..."):
            musics = generate_music(prompt, is_instrumental, st.session_state.suno_api_key)

        if musics and len(musics) >= 2:
            st.success("🎉 生成成功！为您推荐以下两首音乐：")

            # 获取视频数据并保存
            music1 = musics[0]
            music2 = musics[1]

            # 获取视频数据（这里简化处理，实际应用中需要下载视频）
            video1_data = requests.get(music1.get('videoUrl')).content
            video2_data = requests.get(music2.get('videoUrl')).content

            # 保存AI输出
            save_suno_history(st.session_state.music_chat_id, "assistant", prompt, is_instrumental,
                              music1.get('title'), video1_data, music1.get('tags'),
                              music2.get('title'), video2_data, music2.get('tags'))
            st.rerun()

        elif musics:
            st.warning("⚠️ 只成功生成了一首音乐：")
            st.video(musics[0].get('videoUrl'))
        else:
            st.error("❌ 音乐生成失败，请检查输入内容或稍后重试")
            delete_music_chat(st.session_state.music_chat_id)
            st.session_state.music_chat_id = None
            st.rerun()