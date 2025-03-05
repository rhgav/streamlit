import streamlit as st
from zhipuai import ZhipuAI
from PIL import Image
from io import BytesIO
import requests

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 设置page_title内容
st.set_page_config(page_title="文生图应用")

# 设置首行内容
st.title('🎨文生图应用🖼️')

# 初始化ZhipuAI客户端
client = ZhipuAI(api_key="6a4d6968b5fe4152b549331990dec041.HEmtGz10FoJ91P1H")  # 请替换为你的实际API_KEY

def generate_image(prompt):
    """
    根据用户输入的文本描述生成图像。
    
    :param prompt: 用户输入的文本描述，类型为str
    :return: 生成的图像数据，类型为BytesIO对象
    """
    response = client.images.generations(
        model="cogView-4",  # 填写需要调用的模型编码
        prompt=prompt,
        size="1440x720"
    )
    image_url = response.data[0].url
    
    # 下载图像数据
    response = requests.get(image_url)
    image_data = BytesIO(response.content)
    
    return image_data

# 构造一个用于输入描述的表单
with st.form('生成图像的表单'):
    description = st.text_area('请输入一段描述性的文本：', '例如：在干燥的沙漠环境中，一棵孤独的仙人掌在夕阳的余晖中显得格外醒目。')
    submitted = st.form_submit_button('生成图像')

    # 如果用户点击了提交按钮
    if submitted:
        with st.spinner("正在生成图像..."):
            # 调用generate_image()方法生成图像
            image_data = generate_image(description)
            
            # 使用PIL库打开图像数据，并在Streamlit中显示
            image = Image.open(image_data)
            st.image(image, caption='生成的图像')
        st.success("图像生成完成!")