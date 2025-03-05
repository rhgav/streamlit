import streamlit as st
from zhipuai import ZhipuAI
import time
from io import BytesIO
from PIL import Image
import requests

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 设置page_title内容
st.set_page_config(page_title="文生视频应用")

# 设置首行内容
st.title('🎥文生视频应用🎬')

# 初始化ZhipuAI客户端
client = ZhipuAI(api_key="6a4d6968b5fe4152b549331990dec041.HEmtGz10FoJ91P1H")  # 请替换为你的实际API_KEY


def generate_video(prompt):
    """
    根据用户输入的文本描述生成视频。

    :param prompt: 用户输入的文本描述，类型为str
    :return: 视频的URL，类型为str
    """
    response = client.videos.generations(
        model="cogvideox-2",
        prompt=prompt,
        quality="speed",  # 输出模式，"quality"为质量优先，"speed"为速度优先
        with_audio=True,
        size="1920x1080",  # 视频分辨率
        fps=30  # 帧率
    )
    task_id = response.id

    # 设定一个合理的等待时间和最大等待次数
    wait_time = 30  # 等待30秒后再检查
    max_attempts = 60 * 10  # 最大等待时间为10分钟（60秒 * 10 = 600秒）

    for attempt in range(max_attempts):
        status_response = client.videos.retrieve_videos_result(id=task_id)
        if status_response.task_status == 'SUCCESS':
            video_url = status_response.video_result[0].url
            return video_url
        elif status_response.task_status == 'FAIL':
            st.error("视频生成失败!")
            return None
        else:
            time.sleep(wait_time)

    st.error("视频生成超时!")
    return None


# 构造一个用于输入描述的表单
with st.form('生成视频的表单'):
    description = st.text_area('请输入一段描述性的文本：', '例如：比得兔开小汽车，游走在马路上，脸上的表情充满开心喜悦。')
    submitted = st.form_submit_button('生成视频')

    # 如果用户点击了提交按钮
    if submitted:
        with st.spinner("正在生成视频..."):
            # 调用generate_video()方法生成视频
            video_url = generate_video(description)

            if video_url:
                # 在Streamlit中显示视频
                st.video(video_url)
                st.success("视频生成完成!")

# 注意：这里的YOUR_API_KEY需要替换为你自己的API Key。