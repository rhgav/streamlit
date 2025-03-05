import io
import streamlit as st
from PIL import Image
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 设置page_title内容
st.set_page_config(page_title="问答机器人")

# 设置首行内容
st.title('🤖问答机器人😜')

# 初始化聊天记录和记忆
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.memory = ConversationBufferMemory(memory_key='chat_history')

# 展示聊天记录
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message(message["role"], avatar='☺️'):
            st.markdown(message["content"])
    else:
        with st.chat_message(message["role"], avatar='🤖'):
            st.markdown(message["content"])

def generate_response(input_text):
    """
    :param input_text:  用户输入的查询问题，类型为str
    :return: 返回langchain查询openai获得的结果，类型为str
    """
    llm = ChatOpenAI(
        temperature=0.95,
        model="glm-4-plus",
        openai_api_key="3e28ff391d064016b4e95f3e3b792d82.IGQKeHaJqo7Lxw2E",
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
    )

    template = """
    你是一个智能的代码修改和聊天机器人。
    你的任务是：
    1. 如果用户提交的是代码片段，你应分析代码，提供修改建议（如果必要），或解释代码的功能和工作原理。
    2. 如果用户提交的是非代码文本，你应与之进行对话，保持对话的自然流畅。

    注意：
    - 在提供代码修改建议时，请确保你的建议是可操作的，并且尽量使用简洁明了的语言。
    - 对于非代码文本，尽量保持对话的相关性和有趣性。
    - 如果无法提供有用的信息或无法处理用户的问题，可以回复：“抱歉，我无法理解或处理这个问题。”

    以下是用户的问题：
    {question}
    """
    prompt = PromptTemplate(template=template, input_variables=["question"])

    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser

    # 将对话历史传递给模型
    response = chain.invoke({"question": input_text, "chat_history": st.session_state.memory.load_memory_variables({})})
    st.session_state.memory.save_context({"input": input_text}, {"output": response})
    return response

# 用于用户输入
if prompt := st.chat_input('我们来聊一点代码相关的事儿吧'):
    with st.chat_message('user', avatar='☺️'):
        st.markdown(prompt)

    st.session_state.messages.append({'role': 'user', 'content': prompt})

    with st.spinner("AI正在飞快加载中..."):
        response = generate_response(prompt)

    with st.chat_message('assistant', avatar='🤖'):
        st.markdown(response)
    st.session_state.messages.append({'role': 'assistant', 'content': response})