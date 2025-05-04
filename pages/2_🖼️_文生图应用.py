import streamlit as st
from http import HTTPStatus
import requests
from dashscope import ImageSynthesis
import base64
from volcengine.visual.VisualService import VisualService
from PIL import Image
from io import BytesIO
import mysql.connector
from mysql.connector import Error
from Home import record_app_access  # 假设主代码文件名为 Home.py

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 记录用户访问应用（新增）
record_app_access(st.session_state.user_id, "picture_generation")


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
def save_picture_chat_history(chat_id, role, message, model_type=None, image_data=None):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        if image_data is not None:
            # 保存图片数据到数据库
            cursor.execute('''INSERT INTO picture_chat_history (chat_id, role, message, model_type, image_data)
                              VALUES (%s, %s, %s, %s, %s)''',
                           (chat_id, role, message, model_type, image_data))
        else:
            cursor.execute('''INSERT INTO picture_chat_history (chat_id, role, message, model_type)
                              VALUES (%s, %s, %s, %s)''',
                           (chat_id, role, message, model_type))
        conn.commit()
    except Error as e:
        st.error(f"保存图片聊天记录时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def load_picture_chat_history(chat_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT role, message, model_type, image_data FROM picture_chat_history 
                          WHERE chat_id = %s ORDER BY timestamp''', (chat_id,))
        chat_history = cursor.fetchall()
        return chat_history
    except Error as e:
        st.error(f"加载图片聊天记录时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


def create_new_picture_chat(user_id):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO picture_chats (user_id) VALUES (%s)', (user_id,))
        conn.commit()
        chat_id = cursor.lastrowid
        return chat_id
    except Error as e:
        st.error(f"创建新图片对话时发生错误: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            conn.close()


def delete_picture_chat(chat_id):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM picture_chats WHERE id = %s', (chat_id,))
        cursor.execute('DELETE FROM picture_chat_history WHERE chat_id = %s', (chat_id,))
        conn.commit()
    except Error as e:
        st.error(f"删除图片对话时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def get_user_picture_chats(user_id):
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
                       FROM picture_chat_history 
                       WHERE chat_id = c.id AND role = 'user' 
                       ORDER BY timestamp ASC LIMIT 1
                   ), '新对话') as preview
            FROM picture_chats c
            WHERE c.user_id = %s
            ORDER BY c.timestamp DESC
        ''', (user_id,))
        chats = cursor.fetchall()
        return chats
    except Error as e:
        st.error(f"获取用户图片对话列表时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


# 图片生成函数（修改为使用用户输入的API密钥）
def generate_image_dashscope(prompt, model_name="wanx2.1-t2i-turbo", api_key=None):
    """
    使用 DashScope 模型生成图像。
    """
    if not api_key:
        st.error("请先输入通义万相的API密钥")
        return None, None

    rsp = ImageSynthesis.call(api_key=api_key,
                              model=model_name,
                              prompt=prompt,
                              n=1,
                              size='1024*1024')

    if rsp.status_code == HTTPStatus.OK:
        image_url = rsp.output.results[0].url
        response = requests.get(image_url)
        if response.status_code == 200:
            return response.content, image_url  # 返回二进制数据和URL
    return None, None


def generate_image_volcengine(desc, ak=None, sk=None):
    """
    使用 VolcEngine 模型生成图像。
    """
    if not ak or not sk:
        st.error("请先输入豆包模型的AK和SK")
        return None, None

    visual_service = VisualService()
    visual_service.set_ak(ak)
    visual_service.set_sk(sk)

    form = {
        "req_key": "high_aes_general_v20_L",
        "prompt": desc.strip(),
    }

    resp = visual_service.cv_process(form)
    image_data = base64.b64decode(resp['data']['binary_data_base64'][0])
    return image_data, None  # 豆包模型不返回URL


def generate_image_dell_e3(prompt, api_key=None):
    """
    使用 DELL·E 3 模型生成图像。
    """
    if not api_key:
        st.error("请先输入DELL·E 3的API密钥")
        return None, None

    endpoint = "https://api.ttapi.io/openai/v1/images/generations"
    headers = {
        "TT-API-KEY": api_key
    }
    data = {
        "prompt": prompt,
        "size": "1024x1024",
    }

    response = requests.post(endpoint, headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        if response_json.get("status") == "SUCCESS":
            image_url = response_json["data"]["data"][0]["url"]
            response = requests.get(image_url)
            if response.status_code == 200:
                return response.content, image_url
    return None, None


# 页面配置
st.set_page_config(page_title="文生图应用", page_icon="🎨")
st.title('🎨 文生图应用 🖼️')

# 获取用户对话
chats = get_user_picture_chats(st.session_state.user_id)


# 显示对话选择器
def display_picture_chat_selector(chats):
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
                if st.button(btn_text, key=f"pic_chat_{chat_id}"):
                    st.session_state.pic_chat_id = chat_id
                    st.session_state.show_pic_message = f"success|已加载对话 [{time[:5]}]"


display_picture_chat_selector(chats)

# 提示信息处理
if 'show_pic_message' in st.session_state:
    msg_type, message = st.session_state.show_pic_message.split("|")
    if msg_type == "success":
        st.success(message)
    elif msg_type == "info":
        st.info(message)
    del st.session_state.show_pic_message

# 新建对话按钮
if st.sidebar.button("✨ 新建图片对话"):
    chat_id = create_new_picture_chat(st.session_state.user_id)
    st.session_state.pic_chat_id = chat_id
    st.session_state.show_pic_message = "success|图片对话创建成功"
    st.session_state.is_new_pic_chat = True  # 标记为新对话
    st.rerun()

# 确保用户选择了对话
if 'pic_chat_id' not in st.session_state or st.session_state.pic_chat_id is None:
    st.warning("请先选择图片对话或新建图片对话")
    st.stop()

# 加载并显示历史对话
pic_chat_history = load_picture_chat_history(st.session_state.pic_chat_id)
for role, message, model_type, image_data in pic_chat_history:
    with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
        if role == "user":
            st.markdown(message)
        if role == "assistant":
            try:
                if image_data is not None:
                    image = Image.open(BytesIO(image_data))
                    st.image(image, caption="生成的图像")
                else:
                    st.warning("此历史记录中没有保存图片数据")
            except Exception as e:
                st.error(f"加载历史图片时出错: {str(e)}")
        if role == "assistant" and model_type:
            st.caption(f"模型: {model_type}")

# 模型配置
MODELS = {
    "通义万相极速版": {
        "model_name": "wanx2.1-t2i-turbo",
        "requires_ak_sk": False
    },
    "通义万相专业版": {
        "model_name": "wanx2.1-t2i-plus",
        "requires_ak_sk": False
    },
    "豆包": {
        "model_name": "high_aes",
        "requires_ak_sk": True
    },
    "DELL·E 3": {
        "model_name": "dall-e-3",
        "requires_ak_sk": False
    }
}

# 模型选择器
selected_model = st.sidebar.selectbox("选择大模型", list(MODELS.keys()))

# 在侧边栏添加API密钥输入
st.sidebar.markdown("## API配置")

if MODELS[selected_model]["requires_ak_sk"]:
    # 豆包模型需要AK和SK
    ak = st.sidebar.text_input("输入Access Key (AK)", type="password")
    sk = st.sidebar.text_input("输入Secret Key (SK)", type="password")
    api_key = None
else:
    # 其他模型只需要API密钥
    api_key = st.sidebar.text_input(f"输入{selected_model}的API密钥", type="password")
    ak = None
    sk = None

# 检查是否提供了必要的凭证
if MODELS[selected_model]["requires_ak_sk"]:
    if not ak or not sk:
        st.sidebar.warning("请先输入AK和SK以使用豆包模型")
        st.stop()
else:
    if not api_key:
        st.sidebar.warning(f"请先输入{selected_model}的API密钥")
        st.stop()

prompt = st.chat_input("请输入图片描述")

if prompt:
    with st.spinner("正在生成图像..."):
        # 如果是新对话且未保存过消息，则删除无效对话
        if 'is_new_pic_chat' in st.session_state and st.session_state.is_new_pic_chat:
            delete_picture_chat(st.session_state.pic_chat_id)
            chat_id = create_new_picture_chat(st.session_state.user_id)
            st.session_state.pic_chat_id = chat_id
            st.session_state.is_new_pic_chat = False

        # 保存用户提示
        save_picture_chat_history(st.session_state.pic_chat_id, "user", prompt)

        # 显示用户输入
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        # 根据选择的模型生成图片
        image_data, image_url = None, None
        try:
            if selected_model in ["通义万相极速版", "通义万相专业版"]:
                image_data, image_url = generate_image_dashscope(
                    prompt,
                    MODELS[selected_model]["model_name"],
                    api_key
                )
            elif selected_model == "豆包":
                image_data, image_url = generate_image_volcengine(
                    prompt,
                    ak,
                    sk
                )
            elif selected_model == "DELL·E 3":
                image_data, image_url = generate_image_dell_e3(
                    prompt,
                    api_key
                )

            if image_data:
                image = Image.open(BytesIO(image_data))
                with st.chat_message("assistant", avatar="🤖"):
                    st.image(image, caption='生成的图像')
                    st.caption(f"模型: {selected_model}")
                save_picture_chat_history(
                    st.session_state.pic_chat_id,
                    "assistant",
                    image_url if image_url else "图片已生成（无URL）",
                    selected_model,
                    image_data
                )
            else:
                st.error("图像生成失败，请检查API密钥是否正确")
        except Exception as e:
            st.error(f"图像生成失败: {str(e)}")