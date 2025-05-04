import streamlit as st
from zhipuai import ZhipuAI
from http import HTTPStatus
from dashscope import VideoSynthesis
import time
from volcenginesdkarkruntime import Ark
import requests
import base64
from io import BytesIO
import io
from PIL import Image
import mysql.connector
from mysql.connector import Error
from Home import record_app_access

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 记录用户访问应用
record_app_access(st.session_state.user_id, "videofrompicture_generation")

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
def save_image_video_chat_history(chat_id, role, message, model_type=None, image_data=None, video_data=None):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        if image_data is not None and video_data is not None:
            cursor.execute('''INSERT INTO image_video_chat_history 
                            (chat_id, role, message, model_type, image_data, video_data)
                            VALUES (%s, %s, %s, %s, %s, %s)''',
                           (chat_id, role, message, model_type, image_data, video_data))
        elif image_data is not None:
            cursor.execute('''INSERT INTO image_video_chat_history 
                            (chat_id, role, message, model_type, image_data)
                            VALUES (%s, %s, %s, %s, %s)''',
                           (chat_id, role, message, model_type, image_data))
        elif video_data is not None:
            cursor.execute('''INSERT INTO image_video_chat_history 
                            (chat_id, role, message, model_type, video_data)
                            VALUES (%s, %s, %s, %s, %s)''',
                           (chat_id, role, message, model_type, video_data))
        else:
            cursor.execute('''INSERT INTO image_video_chat_history 
                            (chat_id, role, message, model_type)
                            VALUES (%s, %s, %s, %s)''',
                           (chat_id, role, message, model_type))
        conn.commit()
    except Error as e:
        st.error(f"保存图片视频聊天记录时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()

def load_image_video_chat_history(chat_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT role, message, model_type, image_data, video_data 
                          FROM image_video_chat_history 
                          WHERE chat_id = %s ORDER BY timestamp''', (chat_id,))
        chat_history = cursor.fetchall()
        return chat_history
    except Error as e:
        st.error(f"加载图片视频聊天记录时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()

def create_new_image_video_chat(user_id):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO image_video_chats (user_id) VALUES (%s)', (user_id,))
        conn.commit()
        chat_id = cursor.lastrowid
        return chat_id
    except Error as e:
        st.error(f"创建新图片视频对话时发生错误: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            conn.close()

def delete_image_video_chat(chat_id):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM image_video_chats WHERE id = %s', (chat_id,))
        cursor.execute('DELETE FROM image_video_chat_history WHERE chat_id = %s', (chat_id,))
        conn.commit()
    except Error as e:
        st.error(f"删除图片视频对话时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()

def get_user_image_video_chats(user_id):
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
                       FROM image_video_chat_history 
                       WHERE chat_id = c.id AND role = 'user' 
                       ORDER BY timestamp ASC LIMIT 1
                   ), '新对话') as preview
            FROM image_video_chats c
            WHERE c.user_id = %s
            ORDER BY c.timestamp DESC
        ''', (user_id,))
        chats = cursor.fetchall()
        return chats
    except Error as e:
        st.error(f"获取用户图片视频对话列表时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()

# 页面配置
st.set_page_config(page_title="图生视频应用", page_icon="🎥")
st.title('🖼️ 图生视频应用 🎥')

# 返回主界面按钮
st.sidebar.markdown("---")
if st.sidebar.button("🔙 返回主界面"):
    st.switch_page("Home.py")

# 获取用户对话
chats = get_user_image_video_chats(st.session_state.user_id)

# 显示对话选择器
def display_image_video_chat_selector(chats):
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
                if st.button(btn_text, key=f"imgvid_chat_{chat_id}"):
                    st.session_state.imgvid_chat_id = chat_id
                    st.session_state.show_imgvid_message = f"success|已加载对话 [{time[:5]}]"

display_image_video_chat_selector(chats)

# 提示信息处理
if 'show_imgvid_message' in st.session_state:
    msg_type, message = st.session_state.show_imgvid_message.split("|")
    if msg_type == "success":
        st.success(message)
    elif msg_type == "info":
        st.info(message)
    del st.session_state.show_imgvid_message

# 新建对话按钮
if st.sidebar.button("✨ 新建图生视频对话"):
    chat_id = create_new_image_video_chat(st.session_state.user_id)
    st.session_state.imgvid_chat_id = chat_id
    st.session_state.show_imgvid_message = "success|图生视频对话创建成功"
    st.session_state.is_new_imgvid_chat = True  # 标记为新对话
    st.rerun()

# 确保用户选择了对话
if 'imgvid_chat_id' not in st.session_state or st.session_state.imgvid_chat_id is None:
    st.warning("请先选择图生视频对话或新建对话")
    st.stop()

# 加载并显示历史对话
imgvid_chat_history = load_image_video_chat_history(st.session_state.imgvid_chat_id)
for role, message, model_type, image_data, video_data in imgvid_chat_history:
    with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
        if role == "user":
            st.markdown(message)
            if image_data is not None:
                st.image(io.BytesIO(image_data), caption="上传的图片")
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
    #"通义万相": {
    #    "model_name": "wanx2.1-i2v-turbo",
    #    "requires_endpoint": False
    #},
    "豆包": {
        "model_name": "ep-20250326152333-76db6",
        "requires_endpoint": True
    },
    #"Luma": {
    #    "model_name": "luma-v1",
    #    "requires_endpoint": False
    #}
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

def image_to_base64(image_bytes):
    encoded_string = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:image/png;base64,{encoded_string}"

def generate_video_zhipu(image_base64, prompt, api_key):
    """使用ZhipuAI模型生成视频并返回二进制数据"""
    try:
        client = ZhipuAI(api_key=api_key)
        response = client.videos.generations(
            model="cogvideox-2",
            image_url=image_base64,
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
                return download_video_as_bytes(video_url), video_url
            elif status_response.task_status == 'FAIL':
                st.error("视频生成失败!")
                return None, None
            else:
                time.sleep(wait_time)

        st.error("视频生成超时!")
        return None, None
    except Exception as e:
        st.error(f"生成视频时出错: {str(e)}")
        return None, None

def generate_video_wanx(image_base64, prompt, api_key):
    """使用阿里云Wanx模型生成视频并返回二进制数据"""
    try:
        rsp = VideoSynthesis.call(
            api_key=api_key,
            model='wanx2.1-i2v-turbo',
            prompt=prompt,
            image_url=image_base64,
        )

        if rsp.status_code == HTTPStatus.OK:
            video_url = rsp.output.video_url
            return download_video_as_bytes(video_url), video_url
        else:
            st.error(f'生成失败, 状态码: {rsp.status_code}, 代码: {rsp.code}, 消息: {rsp.message}')
            return None, None
    except Exception as e:
        st.error(f"生成视频时出错: {str(e)}")
        return None, None

def generate_video_doubao(image_base64, prompt, api_key, endpoint_name):
    """使用豆包模型生成视频并返回二进制数据"""
    try:
        client = Ark(api_key=api_key)
        create_result = client.content_generation.tasks.create(
            model=endpoint_name,
            content=[
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64
                    },
                }
            ]
        )

        final_result = wait_for_task_completion(create_result.id, client)

        if final_result and final_result.status == "succeeded" and final_result.content and final_result.content.video_url:
            video_url = final_result.content.video_url
            return download_video_as_bytes(video_url), video_url
        else:
            st.error("视频生成失败!")
            return None, None
    except Exception as e:
        st.error(f"生成视频时出错: {str(e)}")
        return None, None

def generate_video_luma(image_base64, prompt, api_key):
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
            "imageUrl": image_base64,
        }

        response = requests.post(endpoint, headers=headers, json=data)
        if response.status_code != 200:
            st.error(f"提交任务失败，状态码: {response.status_code}")
            return None, None

        job_id = response.json().get('data', {}).get('jobId')
        if not job_id:
            st.error("无法获取任务ID")
            return None, None

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
                    return download_video_as_bytes(video_url), video_url
                else:
                    st.error("视频生成成功，但未获取到URL")
                    return None, None
            elif status in ['FAILED', 'CANCELLED']:
                st.error(f"任务失败或取消: {result.get('message')}")
                return None, None

        st.error("视频生成超时!")
        return None, None
    except Exception as e:
        st.error(f"生成视频时出错: {str(e)}")
        return None, None

# 构造一个用于上传图片和输入描述的表单
with st.form('生成视频的表单'):
    uploaded_file = st.file_uploader("请上传一张图片：", type=["png", "jpg", "jpeg"])
    description = st.text_area('请输入描述性的文本：',
                               '例如：微距镜头下，一片猪肉切片卷起巨大的海浪，一个小人物在这片"海浪"上勇敢冲浪，冲浪板激起细腻的浪花')
    submitted = st.form_submit_button('生成视频')

    # 如果用户点击了提交按钮
    if submitted:
        if uploaded_file is not None:
            # 读取图片数据
            image = Image.open(uploaded_file)
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()

            # 如果是新对话且未保存过消息，则删除无效对话
            if 'is_new_imgvid_chat' in st.session_state and st.session_state.is_new_imgvid_chat:
                delete_image_video_chat(st.session_state.imgvid_chat_id)
                chat_id = create_new_image_video_chat(st.session_state.user_id)
                st.session_state.imgvid_chat_id = chat_id
                st.session_state.is_new_imgvid_chat = False

            # 保存用户输入和图片
            save_image_video_chat_history(
                st.session_state.imgvid_chat_id,
                "user",
                description,
                None,
                img_bytes
            )

            with st.chat_message("user", avatar="🧑"):
                st.markdown(description)
                st.image(image, caption="上传的图片")

            # 转换为base64用于模型输入
            img_str = base64.b64encode(img_bytes).decode('utf-8')
            image_base64 = f"data:image/png;base64,{img_str}"

            with st.spinner("正在生成视频..."):
                video_data = None
                video_url = None
                try:
                    if selected_model == "智谱清言":
                        video_data, video_url = generate_video_zhipu(image_base64, description, custom_api_key)
                    elif selected_model == "通义万相":
                        video_data, video_url = generate_video_wanx(image_base64, description, custom_api_key)
                    elif selected_model == "豆包":
                        video_data, video_url = generate_video_doubao(image_base64, description, custom_api_key, endpoint_name)
                    else:  # Luma模型
                        video_data, video_url = generate_video_luma(image_base64, description, custom_api_key)

                    if video_data and video_url:
                        # 显示生成的视频
                        with st.chat_message("assistant", avatar="🤖"):
                            st.video(io.BytesIO(video_data))
                            st.caption(f"模型: {selected_model}")

                        # 保存AI响应（视频二进制数据和URL）
                        save_image_video_chat_history(
                            st.session_state.imgvid_chat_id,
                            "assistant",
                            video_url,
                            selected_model,
                            None,
                            video_data
                        )

                        st.success("视频生成完成!")
                except Exception as e:
                    st.error(f"视频生成失败: {str(e)}")
                    delete_image_video_chat(st.session_state.imgvid_chat_id)
                    st.session_state.imgvid_chat_id = None
                    st.rerun()
        else:
            st.error("请上传一张图片！")