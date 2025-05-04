import streamlit as st
import dashscope
from dashscope.audio.tts import SpeechSynthesizer
from dashscope.audio.tts_v2 import SpeechSynthesizer as SpeechSynthesizerV2
from io import BytesIO
from Home import record_app_access
import mysql.connector
from mysql.connector import Error

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 记录用户访问应用
record_app_access(st.session_state.user_id, "voice_generation")

# 页面配置
st.set_page_config(page_title="文生语音应用", page_icon="🔊")
st.title('🎤 文生语音应用 🔊')

# 返回主界面按钮
st.sidebar.markdown("---")
if st.sidebar.button("🔙 返回主界面"):
    st.switch_page("Home.py")

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
def save_voice_chat_history(chat_id, role, message, model_type=None, voice_choice=None, audio_data=None, audio_format=None):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        if audio_data is not None:
            cursor.execute('''INSERT INTO voice_chat_history 
                            (chat_id, role, message, model_type, voice_choice, audio_data, audio_format)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                         (chat_id, role, message, model_type, voice_choice, audio_data, audio_format))
        else:
            cursor.execute('''INSERT INTO voice_chat_history 
                            (chat_id, role, message, model_type, voice_choice)
                            VALUES (%s, %s, %s, %s, %s)''',
                         (chat_id, role, message, model_type, voice_choice))
        conn.commit()
    except Error as e:
        st.error(f"保存语音聊天记录时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()

def load_voice_chat_history(chat_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT role, message, model_type, voice_choice, audio_data, audio_format 
                          FROM voice_chat_history 
                          WHERE chat_id = %s ORDER BY timestamp''', (chat_id,))
        chat_history = cursor.fetchall()
        return chat_history
    except Error as e:
        st.error(f"加载语音聊天记录时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()

def create_new_voice_chat(user_id):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO voice_chats (user_id) VALUES (%s)', (user_id,))
        conn.commit()
        chat_id = cursor.lastrowid
        return chat_id
    except Error as e:
        st.error(f"创建新语音对话时发生错误: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            conn.close()

def delete_voice_chat(chat_id):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM voice_chats WHERE id = %s', (chat_id,))
        cursor.execute('DELETE FROM voice_chat_history WHERE chat_id = %s', (chat_id,))
        conn.commit()
    except Error as e:
        st.error(f"删除语音对话时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()

def get_user_voice_chats(user_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(''' 
            SELECT c.id, 
                   DATE(c.timestamp) as chat_date,
                   TIME_FORMAT(c.timestamp, '%H:%i') as chat_time,
                   COALESCE((
                       SELECT SUBSTRING(message,1,30) 
                       FROM voice_chat_history 
                       WHERE chat_id = c.id AND role = 'user' 
                       ORDER BY timestamp ASC LIMIT 1
                   ), '新对话') as preview
            FROM voice_chats c
            WHERE c.user_id = %s
            ORDER BY c.timestamp DESC
        ''', (user_id,))
        chats = cursor.fetchall()
        return chats
    except Error as e:
        st.error(f"获取用户语音对话列表时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()

# 在侧边栏添加API密钥输入
st.sidebar.markdown("## API配置")
custom_api_key = st.sidebar.text_input("输入通义万相API密钥", type="password")

# 获取用户对话
chats = get_user_voice_chats(st.session_state.user_id)

# 显示对话选择器
def display_voice_chat_selector(chats):
    st.sidebar.markdown("## 历史对话")
    date_groups = {}
    for chat in chats:
        date = chat[1]
        if date not in date_groups:
            date_groups[date] = []
        date_groups[date].append(chat)

    for date in sorted(date_groups.keys(), reverse=True):
        with st.sidebar.expander(f"🗓️ {date}"):
            for chat in date_groups[date]:
                chat_id, _, time, preview = chat
                btn_text = f"{time[:5]} | {preview[:20]}..."
                if st.button(btn_text, key=f"voice_chat_{chat_id}"):
                    st.session_state.voice_chat_id = chat_id
                    st.session_state.show_voice_message = f"success|已加载对话 [{time[:5]}]"

display_voice_chat_selector(chats)

# 提示信息处理
if 'show_voice_message' in st.session_state:
    msg_type, message = st.session_state.show_voice_message.split("|")
    if msg_type == "success":
        st.success(message)
    elif msg_type == "info":
        st.info(message)
    del st.session_state.show_voice_message

# 新建对话按钮
if st.sidebar.button("✨ 新建语音对话"):
    chat_id = create_new_voice_chat(st.session_state.user_id)
    st.session_state.voice_chat_id = chat_id
    st.session_state.show_voice_message = "success|语音对话创建成功"
    st.session_state.is_new_voice_chat = True  # 标记为新对话
    st.rerun()

# 确保用户选择了对话
if 'voice_chat_id' not in st.session_state or st.session_state.voice_chat_id is None:
    st.warning("请先选择语音对话或新建语音对话")
    st.stop()

# 检查是否提供了API密钥
if not custom_api_key:
    st.warning("请先在侧边栏输入API密钥以使用语音模型")
    st.stop()

# 设置DashScope API Key
dashscope.api_key = custom_api_key

# 语音模型选择
MODELS = {
    "通义万相CosyVoice": "cosyvoice-v1",
    "通义万相Sambert": "sambert-zhichu-v1"
}

# 初始化会话状态
if 'model_choice' not in st.session_state:
    st.session_state.model_choice = "通义万相CosyVoice"
if 'voice_choice' not in st.session_state:
    st.session_state.voice_choice = "Stella"

# 语音模型选择 - 添加会话状态管理
new_model_choice = st.sidebar.selectbox("选择语音模型", list(MODELS.keys()),
                                      index=list(MODELS.keys()).index(st.session_state.model_choice))
if new_model_choice != st.session_state.model_choice:
    st.session_state.model_choice = new_model_choice
    st.session_state.voice_choice = "Stella" if new_model_choice == "通义万相CosyVoice" else "知琪"
    st.rerun()

# 根据选择的模型显示不同的音色选项
if st.session_state.model_choice == "通义万相CosyVoice":
    # CosyVoice的音色选项
    VOICES = {
        "Stella": "loongstella",
        "Bella": "loongbella",
        "龙小淳": "longxiaochun",
        "龙妙": "longmiao",
        "龙书": "longshu",
        "龙硕": "longshuo"
    }
    new_voice_choice = st.sidebar.selectbox("选择音色 (CosyVoice)", list(VOICES.keys()),
                                          index=list(VOICES.keys()).index(st.session_state.voice_choice))
else:
    # Sambert的音色选项
    MODELS_SAMBERT = {
        "知琪": "zhiqi",
        "知德": "zhide",
        "知厨": "zhichu",
        "知达": "zhida",
        "知茹": "zhiru",
        "知婧": "zhijing",
        "知晔": "zhiye"
    }
    new_voice_choice = st.sidebar.selectbox("选择音色 (Sambert)", list(MODELS_SAMBERT.keys()),
                                          index=list(MODELS_SAMBERT.keys()).index(st.session_state.voice_choice))

# 更新音色选择到会话状态
if new_voice_choice != st.session_state.voice_choice:
    st.session_state.voice_choice = new_voice_choice
    st.rerun()

# 加载并显示历史对话（修改为显示音色信息）
voice_chat_history = load_voice_chat_history(st.session_state.voice_chat_id)
for role, message, model_type, voice_choice, audio_data, audio_format in voice_chat_history:
    with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
        if role == "user":
            st.markdown(message)
        else:  # AI response (audio data)
            try:
                if audio_data is not None:
                    st.audio(BytesIO(audio_data), format=audio_format)
                else:
                    st.warning("此历史记录中没有保存音频数据")
            except Exception as e:
                st.error(f"加载历史音频时出错: {str(e)}")
        if role == "assistant" and model_type:
            st.caption(f"模型: {model_type} | 音色: {voice_choice}")  # 显示音色信息

def synthesize_speech_cosyvoice(text, voice):
    """使用CosyVoice模型生成语音"""
    try:
        speech_synthesizer = SpeechSynthesizerV2(model='cosyvoice-v1',
                                               voice=VOICES[voice],
                                               callback=None)
        audio = speech_synthesizer.call(text)
        return BytesIO(audio), "audio/mp3", "mp3"
    except Exception as e:
        st.error(f"语音合成失败: {str(e)}")
        return None, None, None

def synthesize_speech_sambert(text, voice):
    """使用Sambert模型生成语音"""
    try:
        result = SpeechSynthesizer.call(model=f'sambert-{MODELS_SAMBERT[voice]}-v1',
                                      text=text,
                                      sample_rate=48000,
                                      format='wav')
        if result.get_audio_data() is not None:
            return BytesIO(result.get_audio_data()), "audio/wav", "wav"
        else:
            st.error(f"语音合成失败: {result.get_response()}")
            return None, None, None
    except Exception as e:
        st.error(f"语音合成失败: {str(e)}")
        return None, None, None

# 输入文本处理部分
description = st.chat_input("请输入要转换为语音的文本")
if description:
    with st.spinner("正在生成语音..."):
        # 如果是新对话且未保存过消息，则删除无效对话
        if 'is_new_voice_chat' in st.session_state and st.session_state.is_new_voice_chat:
            delete_voice_chat(st.session_state.voice_chat_id)
            chat_id = create_new_voice_chat(st.session_state.user_id)
            st.session_state.voice_chat_id = chat_id
            st.session_state.is_new_voice_chat = False

        # 保存用户提示（增加音色参数）
        save_voice_chat_history(st.session_state.voice_chat_id, "user", description,
                              st.session_state.model_choice, st.session_state.voice_choice)

        with st.chat_message("user", avatar="🧑"):
            st.markdown(description)

        # 根据选择的模型生成语音
        audio_data, audio_format, file_extension = None, None, None
        try:
            if st.session_state.model_choice == "通义万相CosyVoice":
                audio_data, audio_format, file_extension = synthesize_speech_cosyvoice(
                    description, st.session_state.voice_choice)
            else:  # Sambert模型
                audio_data, audio_format, file_extension = synthesize_speech_sambert(
                    description, st.session_state.voice_choice)

            if audio_data:
                # 显示生成的音频
                with st.chat_message("assistant", avatar="🤖"):
                    st.audio(audio_data, format=audio_format)
                    st.caption(f"模型: {st.session_state.model_choice} | 音色: {st.session_state.voice_choice}")

                # 保存AI响应（包含音色信息）
                save_voice_chat_history(
                    st.session_state.voice_chat_id,
                    "assistant",
                    description,
                    st.session_state.model_choice,
                    st.session_state.voice_choice,
                    audio_data.getvalue(),
                    audio_format
                )

                st.success("语音生成完成!")
        except Exception as e:
            st.error(f"语音生成失败: {str(e)}")
            delete_voice_chat(st.session_state.voice_chat_id)  # 删除无效对话
            st.session_state.voice_chat_id = None
            st.rerun()