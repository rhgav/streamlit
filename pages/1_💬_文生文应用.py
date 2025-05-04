import streamlit as st
import time
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import mysql.connector
from mysql.connector import Error
from Home import record_app_access  # 假设主代码文件名为 Home.py

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 记录用户访问应用（新增）
record_app_access(st.session_state.user_id, "text_generation")

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

# ----------------- 数据库操作函数 (修改为使用新表名和新增model_type字段) -----------------
def save_chat_history(chat_id, role, message, model_type=None):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO text_chat_history (chat_id, role, message, model_type)
                          VALUES (%s, %s, %s, %s)''', (chat_id, role, message, model_type))
        conn.commit()
    except Error as e:
        st.error(f"保存聊天记录时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def load_chat_history(chat_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('''SELECT role, message, model_type FROM text_chat_history 
                          WHERE chat_id = %s ORDER BY timestamp''', (chat_id,))
        chat_history = cursor.fetchall()
        return chat_history
    except Error as e:
        st.error(f"加载聊天记录时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


def create_new_chat(user_id):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO text_chats (user_id) VALUES (%s)', (user_id,))
        conn.commit()
        chat_id = cursor.lastrowid
        return chat_id
    except Error as e:
        st.error(f"创建新对话时发生错误: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            conn.close()


def delete_chat(chat_id):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM text_chats WHERE id = %s', (chat_id,))
        cursor.execute('DELETE FROM text_chat_history WHERE chat_id = %s', (chat_id,))
        conn.commit()
    except Error as e:
        st.error(f"删除对话时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def get_user_chats(user_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(''' 
            SELECT c.id, 
                   DATE(c.timestamp) as chat_date,
                   TIME_FORMAT(c.timestamp, '%H:%i') as chat_time,  -- 格式化为 HH:MM
                   COALESCE((
                       SELECT SUBSTRING(message,1,30) 
                       FROM text_chat_history 
                       WHERE chat_id = c.id AND role = 'user' 
                       ORDER BY timestamp ASC LIMIT 1
                   ), '新对话') as preview
            FROM text_chats c
            WHERE c.user_id = %s
            ORDER BY c.timestamp DESC
        ''', (user_id,))
        chats = cursor.fetchall()
        return chats
    except Error as e:
        st.error(f"获取用户对话列表时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


# 页面配置
st.set_page_config(page_title="文生文应用", page_icon="💬")
st.title("💬 文生文应用")

# 获取用户对话
chats = get_user_chats(st.session_state.user_id)


# 显示对话选择器
def display_chat_selector(chats):
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
                btn_text = f"{time[:5]} | {preview[:20]}..."  # time 已经是字符串，可以切片
                if st.button(btn_text, key=f"chat_{chat_id}"):
                    st.session_state.chat_id = chat_id
                    st.session_state.show_message = f"success|已加载对话 [{time[:5]}]"


display_chat_selector(chats)

# 提示信息处理
if 'show_message' in st.session_state:
    msg_type, message = st.session_state.show_message.split("|")
    if msg_type == "success":
        st.success(message)
    elif msg_type == "info":
        st.info(message)
    del st.session_state.show_message

# 新建对话按钮
if st.sidebar.button("✨ 新建对话"):
    chat_id = create_new_chat(st.session_state.user_id)
    st.session_state.chat_id = chat_id
    st.session_state.show_message = "success|对话创建成功"
    st.session_state.is_new_chat = True  # 标记为新对话
    st.rerun()  # 刷新页面以显示提示

# 确保用户选择了对话
if 'chat_id' not in st.session_state or st.session_state.chat_id is None:
    st.warning("请先选择对话或新建对话")
    st.stop()

# 初始化对话记忆
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(memory_key="chat_history")

# 加载并显示历史对话
chat_history = load_chat_history(st.session_state.chat_id)
for role, message, model_type in chat_history:
    with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
        st.markdown(message)
        if role == "assistant" and model_type:
            st.caption(f"模型: {model_type}")

# 模型配置
MODELS = {
    "deepseek-chat": {
        "display_name": "DeepSeek-V3",
        "api_base": "https://api.deepseek.com",
        "requires_endpoint": False  # 添加标记是否需要接入点名称
    },
    "qwen-plus": {
        "display_name": "通义千问",
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "requires_endpoint": False
    },
    "ep-20250311224722-74cfs": {
        "display_name": "豆包",
        "api_base": "https://ark.cn-beijing.volces.com/api/v3",
        "requires_endpoint": True  # 豆包需要接入点名称
    },
    "gpt-4o": {
        "display_name": "GPT-4o",
        "api_base": "https://api.laozhang.ai/v1",
        "requires_endpoint": False
    }
}

# 模型选择器
model_options = {model_id: model["display_name"] for model_id, model in MODELS.items()}
selected_model = st.sidebar.selectbox("选择模型", list(model_options.keys()), format_func=lambda x: model_options[x])

# 在侧边栏添加API密钥输入
st.sidebar.markdown("## API配置")
custom_api_key = st.sidebar.text_input(f"输入{model_options[selected_model]}的API密钥", type="password")

# 如果是豆包模型，显示额外的接入点名称输入
if MODELS[selected_model].get("requires_endpoint", False):
    endpoint_name = st.sidebar.text_input("输入接入点名称",
                                          value="ep-20250311224722-74cfs" if selected_model == "ep-20250311224722-74cf" else "")
else:
    endpoint_name = None

# 检查是否提供了必要的凭证
if not custom_api_key:
    st.sidebar.warning("请先输入API密钥以使用模型")
    st.stop()

if MODELS[selected_model].get("requires_endpoint", False) and not endpoint_name:
    st.sidebar.warning("请为豆包模型输入接入点名称")
    st.stop()


# AI响应生成（修改为流式输出）
def generate_response(prompt, model_name):
    model_config = MODELS[model_name]

    # 如果是豆包模型，使用用户提供的接入点名称
    if model_name == "ep-20250311224722-74cfs" and endpoint_name:
        model_name = endpoint_name  # 使用用户提供的接入点名称替换模型名称

    llm = ChatOpenAI(
        temperature=0.95,
        model=model_name,
        openai_api_key=custom_api_key,  # 使用用户输入的API密钥
        openai_api_base=model_config["api_base"],
        streaming=True  # 启用流式输出
    )

    template = """你是一个智能的代码专家和聊天助手，请根据以下要求处理输入：
    1. 如果是代码相关的问题，提供详细解释和优化建议,如果让你修改代码，尽量给出完整的修改后代码
    2. 如果是通用问题，给出专业且友好的回答
    3. 保持回答的条理清晰和格式美观

    当前对话上下文：{chat_history}
    用户输入：{question}"""

    prompt_template = PromptTemplate.from_template(template)
    chain = prompt_template | llm | StrOutputParser()

    # 创建一个容器来收集流式输出的内容
    full_response = []

    # 流式输出
    for chunk in chain.stream({
        "question": prompt,
        "chat_history": st.session_state.memory.load_memory_variables({})["chat_history"]
    }):
        full_response.append(chunk)
        yield chunk  # 使用yield实现流式输出

    # 将完整响应保存到内存和数据库
    complete_response = "".join(full_response)
    st.session_state.memory.chat_memory.add_ai_message(complete_response)
    save_chat_history(st.session_state.chat_id, "assistant", complete_response, model_options[selected_model])


# 用户输入处理部分修改（只显示修改的部分）
if prompt := st.chat_input("请输入您的问题..."):
    if len(prompt) > 50000:
        st.warning("消息长度不能超过50000字符")
    else:
        # 如果是新对话且未保存过消息，则删除无效对话
        if 'is_new_chat' in st.session_state and st.session_state.is_new_chat:
            delete_chat(st.session_state.chat_id)
            chat_id = create_new_chat(st.session_state.user_id)
            st.session_state.chat_id = chat_id
            st.session_state.is_new_chat = False

        # 保存并显示用户消息
        save_chat_history(st.session_state.chat_id, "user", prompt)
        st.session_state.memory.chat_memory.add_user_message(prompt)

        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        # 生成并显示AI回复（修改为流式输出）
        with st.chat_message("assistant", avatar="🤖"):
            try:
                # 使用st.write_stream显示流式输出
                response = st.write_stream(generate_response(prompt, selected_model))
                st.caption(f"模型: {model_options[selected_model]}")
            except Exception as e:
                st.error(f"AI响应失败: {str(e)}")
                delete_chat(st.session_state.chat_id)  # 删除无效对话
                st.session_state.chat_id = None
                st.rerun()