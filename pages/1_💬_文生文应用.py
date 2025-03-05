import sqlite3
import streamlit as st
import time
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()


# 数据库操作函数
def save_chat_history(chat_id, role, message):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO chat_history (chat_id, role, message)
                      VALUES (?, ?, ?)''', (chat_id, role, message))
    conn.commit()
    conn.close()


def load_chat_history(chat_id):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT role, message FROM chat_history WHERE chat_id = ? ORDER BY timestamp''', (chat_id,))
    chat_history = cursor.fetchall()
    conn.close()
    return chat_history


def create_new_chat(user_id):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO chats (user_id) VALUES (?)', (user_id,))
    conn.commit()
    chat_id = cursor.lastrowid
    conn.close()
    return chat_id


def delete_chat(chat_id):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
    cursor.execute('DELETE FROM chat_history WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()


def get_user_chats(user_id):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute(''' 
        SELECT c.id, 
               DATE(c.timestamp) as chat_date,
               TIME(c.timestamp) as chat_time,
               COALESCE((
                   SELECT SUBSTR(message,1,30) 
                   FROM chat_history 
                   WHERE chat_id = c.id AND role = 'user' 
                   ORDER BY timestamp ASC LIMIT 1
               ), '新对话') as preview
        FROM chats c
        WHERE c.user_id = ?
        ORDER BY c.timestamp DESC
    ''', (user_id,))
    chats = cursor.fetchall()
    conn.close()
    return chats


# 页面配置
st.set_page_config(page_title="AI对话界面", page_icon="🤖")
st.title("🤖 智能对话机器人")

# 返回主界面按钮
st.sidebar.markdown("---")
if st.sidebar.button("🔙 返回主界面"):
    st.switch_page("Home.py")

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
                btn_text = f"{time[:5]} | {preview[:20]}..."
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
for role, message in chat_history:
    with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
        st.markdown(message)


# AI响应生成
def generate_response(prompt):
    llm = ChatOpenAI(
        temperature=0.95,
        model="glm-4-plus",
        openai_api_key="3e28ff391d064016b4e95f3e3b792d82.IGQKeHaJqo7Lxw2E",
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
    )

    template = """你是一个智能的代码专家和聊天助手，请根据以下要求处理输入：
    1. 如果是代码相关的问题，提供详细解释和优化建议
    2. 如果是通用问题，给出专业且友好的回答
    3. 保持回答的条理清晰和格式美观

    当前对话上下文：{chat_history}
    用户输入：{question}"""

    prompt_template = PromptTemplate.from_template(template)
    chain = prompt_template | llm | StrOutputParser()

    return chain.invoke({
        "question": prompt,
        "chat_history": st.session_state.memory.load_memory_variables({})["chat_history"]
    })


# 用户输入处理
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

        # 生成并显示AI回复
        with st.spinner("思考中..."):
            try:
                response = generate_response(prompt)
                save_chat_history(st.session_state.chat_id, "assistant", response)
                st.session_state.memory.chat_memory.add_ai_message(response)

                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(response)
            except Exception as e:
                st.error(f"AI响应失败: {str(e)}")
                delete_chat(st.session_state.chat_id)  # 删除无效对话
                st.session_state.chat_id = None
                st.rerun()