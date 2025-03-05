import io
import streamlit as st
from PIL import Image

# 设置page_title内容
st.set_page_config(page_title="问答机器人")

# 设置首行内容
st.title('🤖问答机器人😜')

# 设置左边的sidebar内容
with st.sidebar:
    # 设置输入openai_key和接口访问地址的两个输入框
    openai_key = st.text_input('OpenAI API Key', key='open_ai_key')
    openai_base_url = st.text_input('OpenAI BASE URL', 'https://api.openai.com', key='openai_base_url')

    # 设置一个可点击打开的展开区域
    with st.expander("🤓国内可访问的openai账号"):
        st.write("""
            1. 如果使用默认地址，可以使用openai官网账号（需科学上网🥵）.
            2. 如果你没有openai官网账号，可以联系博主免费试用国内openai节点账号🥳.
        """)

# 定义机器人功能
def generate_response(input_text, open_ai_key, openai_base_url, bot_type):
    """根据不同类型的机器人处理问题"""
    from langchain_openai import ChatOpenAI
    from langchain.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    # 构造一个聊天模型包装器,key和url从函数输入中获取
    llm = ChatOpenAI(
        temperature=0,
        openai_api_key=open_ai_key,
        base_url=openai_base_url
    )

    # 根据选择的机器人类型设置提示语
    if bot_type == "代码机器人":
        template = """
        你是一个智能的代码修改和调试机器人。
        你的任务是：如果用户提交的是代码片段，你应分析代码，提供修改建议，或者解释代码的功能和工作原理。
        例如，解释如何修复代码中的错误，或者如何优化代码性能。
        以下是用户的问题：{question}
        """
    elif bot_type == "旅游机器人":
        template = """
        你是一个智能的旅游助手。
        你的任务是：根据用户提供的旅游相关问题，提供旅游目的地、行程规划和相关建议。
        例如，提供推荐的旅游城市、最佳旅行时间、当地的美食、住宿建议等。
        以下是用户的问题：{question}
        """
    else:
        template = """
        你是一个智能聊天机器人。
        你的任务是：和用户进行自然流畅的对话，回答用户关于任何话题的问题，保持对话的相关性和趣味性。
        以下是用户的问题：{question}
        """

    # 设置Prompt模板
    prompt = PromptTemplate(template=template, input_variables=["question"])

    # 构造一个输出解析器和链
    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser

    response = chain.invoke({"question": input_text})
    st.info(response)

# 创建一个选择框来切换不同的机器人
bot_type = st.selectbox("选择机器人类型", ["代码机器人", "旅游机器人", "聊天机器人"])

# 构造一个用于输入问题的表单
with st.form('提交问题的表单'):
    text = st.text_area('请提一个您的问题', '请输入问题...')
    submitted = st.form_submit_button('提交')

    # 如果用户提交的key格式有误提醒用户
    if not st.session_state['open_ai_key'].startswith('sk-'):
        st.warning('您输入的openai秘钥格式有误')

    # 如果用户点击了提交按钮并且key格式无误则加载一个spinner加载状态
    if submitted and st.session_state['open_ai_key'].startswith('sk-'):
        with st.spinner("AI正在飞快加载中..."):
            # 加载状态进行中，调用我们之前构造的generate_response()方法，把用户的输入，key和url等参数传递给函数
            generate_response(text, st.session_state['open_ai_key'], st.session_state['openai_base_url'], bot_type)
        st.success("AI为您加载完成!")
