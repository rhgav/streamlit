import streamlit as st
from zhipuai import ZhipuAI
from http import HTTPStatus
from dashscope import VideoSynthesis
import time
from volcenginesdkarkruntime import Ark
import requests
import mysql.connector
from mysql.connector import Error
from Home import record_app_access
import io

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 记录用户访问应用
record_app_access(st.session_state.user_id, "videofromtext_generation")

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
def save_video_chat_history(chat_id, role, message, model_type=None, video_data=None):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        if video_data is not None:
            cursor.execute('''INSERT INTO video_chat_history (chat_id, role, message, model_type, video_data)
                              VALUES (%s, %s, %s, %s, %s)''',
                           (chat_id, role, message, model_type, video_data))
        else:
            cursor.execute('''INSERT INTO video_chat_history (chat_id, role, message, model_type)
                              VALUES (%s, %s, %s, %s)''',
                           (chat_id, role, message, model_type))
        conn.commit()
    except Error as e:
        st.error(f"保存视频聊天记录时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()

def load_video_chat_history(chat_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT role, message, model_type, video_data FROM video_chat_history 
                          WHERE chat_id = %s ORDER BY timestamp''', (chat_id,))
        chat_history = cursor.fetchall()
        return chat_history
    except Error as e:
        st.error(f"加载视频聊天记录时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()

def create_new_video_chat(user_id):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO video_chats (user_id) VALUES (%s)', (user_id,))
        conn.commit()
        chat_id = cursor.lastrowid
        return chat_id
    except Error as e:
        st.error(f"创建新视频对话时发生错误: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            conn.close()

def delete_video_chat(chat_id):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM video_chats WHERE id = %s', (chat_id,))
        cursor.execute('DELETE FROM video_chat_history WHERE chat_id = %s', (chat_id,))
        conn.commit()
    except Error as e:
        st.error(f"删除视频对话时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()

def get_user_video_chats(user_id):
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
                       FROM video_chat_history 
                       WHERE chat_id = c.id AND role = 'user' 
                       ORDER BY timestamp ASC LIMIT 1
                   ), '新对话') as preview
            FROM video_chats c
            WHERE c.user_id = %s
            ORDER BY c.timestamp DESC
        ''', (user_id,))
        chats = cursor.fetchall()
        return chats
    except Error as e:
        st.error(f"获取用户视频对话列表时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()

# 页面配置
st.set_page_config(page_title="文生视频应用", page_icon="🎥")
st.title('🎥 文生视频应用 🎬')

# 返回主界面按钮
st.sidebar.markdown("---")
if st.sidebar.button("🔙 返回主界面"):
    st.switch_page("Home.py")

# 获取用户对话
chats = get_user_video_chats(st.session_state.user_id)

# 显示对话选择器
def display_video_chat_selector(chats):
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
                if st.button(btn_text, key=f"vid_chat_{chat_id}"):
                    st.session_state.vid_chat_id = chat_id
                    st.session_state.show_vid_message = f"success|已加载对话 [{time[:5]}]"

display_video_chat_selector(chats)

# 提示信息处理
if 'show_vid_message' in st.session_state:
    msg_type, message = st.session_state.show_vid_message.split("|")
    if msg_type == "success":
        st.success(message)
    elif msg_type == "info":
        st.info(message)
    del st.session_state.show_vid_message

# 新建对话按钮
if st.sidebar.button("✨ 新建视频对话"):
    chat_id = create_new_video_chat(st.session_state.user_id)
    st.session_state.vid_chat_id = chat_id
    st.session_state.show_vid_message = "success|视频对话创建成功"
    st.session_state.is_new_vid_chat = True  # 标记为新对话
    st.rerun()

# 确保用户选择了对话
if 'vid_chat_id' not in st.session_state or st.session_state.vid_chat_id is None:
    st.warning("请先选择视频对话或新建视频对话")
    st.stop()

# 加载并显示历史对话
vid_chat_history = load_video_chat_history(st.session_state.vid_chat_id)
for role, message, model_type, video_data in vid_chat_history:
    with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
        if role == "user":
            st.markdown(message)
        else:  # AI response (video data)
            try:
                if video_data is not None:
                    st.video(io.BytesIO(video_data))
                else:
                    st.warning("此历史记录中没有保存视频数据")
            except Exception as e:
                st.error(f"加载历史视频时出错: {str(e)}")
        if role == "assistant" and model_type:
            st.caption(f"模型: {model_type}")

# 模型配置
MODELS = {
    "智谱清言": {
        "model_name": "cogvideox-2",
        "requires_endpoint": False
    },
    "通义万相": {
        "model_name": "wanx2.1-t2v-turbo",
        "requires_endpoint": False
    },
    "豆包": {
        "model_name": "ep-20250326152333-76db6",
        "requires_endpoint": True
    },
    "Luma": {
        "model_name": "luma-v1",
        "requires_endpoint": False
    }
}

# 模型选择器
selected_model = st.sidebar.selectbox("选择大模型", list(MODELS.keys()))

# 在侧边栏添加API密钥输入
st.sidebar.markdown("## API配置")
custom_api_key = st.sidebar.text_input(f"输入{selected_model}的API密钥", type="password")

# 如果是豆包模型，显示额外的接入点名称输入
if MODELS[selected_model]["requires_endpoint"]:
    endpoint_name = st.sidebar.text_input("输入接入点名称",
                                        value="ep-20250326152333-76db6" if selected_model == "豆" else "")
else:
    endpoint_name = None

# 检查是否提供了必要的凭证
if not custom_api_key:
    st.sidebar.warning("请先输入API密钥以使用模型")
    st.stop()

if MODELS[selected_model]["requires_endpoint"] and not endpoint_name:
    st.sidebar.warning("请为豆包模型输入接入点名称")
    st.stop()

def download_video_as_bytes(video_url):
    """下载视频并返回二进制数据"""
    try:
        response = requests.get(video_url, stream=True)
        if response.status_code == 200:
            return response.content
        else:
            st.warning(f"无法下载视频，状态码: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"下载视频时出错: {str(e)}")
        return None

# 视频生成函数（更新为使用用户输入的API密钥）
def generate_video_zhipu(prompt, api_key):
    """使用ZhipuAI模型生成视频并返回二进制数据"""
    try:
        client = ZhipuAI(api_key=api_key)
        response = client.videos.generations(
            model="cogvideox-2",
            prompt=prompt,
            quality="speed",
            with_audio=True,
            size="1920x1080",
            fps=30
        )
        task_id = response.id

        wait_time = 30
        max_attempts = 60 * 10

        for attempt in range(max_attempts):
            status_response = client.videos.retrieve_videos_result(id=task_id)
            if status_response.task_status == 'SUCCESS':
                video_url = status_response.video_result[0].url
                return download_video_as_bytes(video_url)
            elif status_response.task_status == 'FAIL':
                st.error("视频生成失败!")
                return None
            else:
                time.sleep(wait_time)

        st.error("视频生成超时!")
        return None
    except Exception as e:
        st.error(f"生成视频时出错: {str(e)}")
        return None

def generate_video_wanx(prompt, api_key):
    """使用阿里云Wanx模型生成视频并返回二进制数据"""
    try:
        rsp = VideoSynthesis.call(
            api_key=api_key,
            model='wanx2.1-t2v-turbo',
            prompt=prompt,
            size='1280*720'
        )

        if rsp.status_code == HTTPStatus.OK:
            video_url = rsp.output.video_url
            return download_video_as_bytes(video_url)
        else:
            st.error(f'生成失败, 状态码: {rsp.status_code}, 代码: {rsp.code}, 消息: {rsp.message}')
            return None
    except Exception as e:
        st.error(f"生成视频时出错: {str(e)}")
        return None

def wait_for_task_completion(task_id, client, interval=30, timeout=600):
    """等待任务完成的函数"""
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            return None

        try:
            task_result = client.content_generation.tasks.get(task_id=task_id)
            if task_result.status in ["succeeded", "failed", "cancelled"]:
                return task_result
        except Exception as e:
            pass

        time.sleep(interval)

def generate_video_doubao(prompt, api_key, endpoint_name):
    """使用豆包模型生成视频并返回二进制数据"""
    try:
        client = Ark(api_key=api_key)
        create_result = client.content_generation.tasks.create(
            model=endpoint_name,
            content=[
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        )

        final_result = wait_for_task_completion(create_result.id, client)

        if final_result and final_result.status == "succeeded" and final_result.content and final_result.content.video_url:
            video_url = final_result.content.video_url
            return download_video_as_bytes(video_url)
        else:
            st.error("视频生成失败!")
            return None
    except Exception as e:
        st.error(f"生成视频时出错: {str(e)}")
        return None

def generate_video_luma(prompt, api_key):
    """使用Luma模型生成视频并返回二进制数据"""
    try:
        endpoint = "https://api.ttapi.io/luma/v1/generations"
        headers = {
            "Content-Type": "application/json",
            "TT-API-KEY": api_key
        }
        data = {
            "userPrompt": prompt,
            "useMode": "fast",
        }

        response = requests.post(endpoint, headers=headers, json=data)
        if response.status_code != 200:
            st.error(f"提交任务失败，状态码: {response.status_code}")
            return None

        job_id = response.json().get('data', {}).get('jobId')
        if not job_id:
            st.error("无法获取任务ID")
            return None

        for attempt in range(20):
            time.sleep(30)

            endpoint = "https://api.ttapi.io/luma/v1/fetch"
            query = {
                "jobId": job_id,
            }
            response = requests.post(endpoint, headers=headers, json=query)

            if response.status_code != 200:
                st.warning(f"查询任务失败，状态码: {response.status_code}")
                continue

            result = response.json()
            status = result.get('status')

            if status == 'SUCCESS':
                video_url = result.get('data', {}).get('videoUrl')
                if video_url:
                    return download_video_as_bytes(video_url)
                else:
                    st.error("视频生成成功，但未获取到URL")
                    return None
            elif status in ['FAILED', 'CANCELLED']:
                st.error(f"任务失败或取消: {result.get('message')}")
                return None

        st.error("视频生成超时!")
        return None
    except Exception as e:
        st.error(f"生成视频时出错: {str(e)}")
        return None

description = st.chat_input("请输入视频描述")
if description:
    with st.spinner("正在生成视频..."):
        # 如果是新对话且未保存过消息，则删除无效对话
        if 'is_new_vid_chat' in st.session_state and st.session_state.is_new_vid_chat:
            delete_video_chat(st.session_state.vid_chat_id)
            chat_id = create_new_video_chat(st.session_state.user_id)
            st.session_state.vid_chat_id = chat_id
            st.session_state.is_new_vid_chat = False

        # 保存用户提示
        save_video_chat_history(st.session_state.vid_chat_id, "user", description)

        with st.chat_message("user", avatar="🧑"):
            st.markdown(description)

        # 根据选择的模型生成视频
        video_data = None
        try:
            if selected_model == "智谱清言":
                video_data = generate_video_zhipu(description, custom_api_key)
            elif selected_model == "通义万相":
                video_data = generate_video_wanx(description, custom_api_key)
            elif selected_model == "豆包":
                video_data = generate_video_doubao(description, custom_api_key, endpoint_name)
            else:  # Luma模型
                video_data = generate_video_luma(description, custom_api_key)

            if video_data:
                # 显示生成的视频
                with st.chat_message("assistant", avatar="🤖"):
                    st.video(io.BytesIO(video_data))
                    st.caption(f"模型: {selected_model}")

                # 保存AI响应（视频二进制数据）
                save_video_chat_history(
                    st.session_state.vid_chat_id,
                    "assistant",
                    description,
                    selected_model,
                    video_data
                )

                st.success("视频生成完成!")
        except Exception as e:
            st.error(f"视频生成失败: {str(e)}")
            delete_video_chat(st.session_state.vid_chat_id)  # 删除无效对话
            st.session_state.vid_chat_id = None
            st.rerun()