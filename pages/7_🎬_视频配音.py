import streamlit as st
import os
import cv2
from dashscope.audio.tts import SpeechSynthesizer
from http import HTTPStatus
import dashscope
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Tongyi
import mysql.connector
from mysql.connector import Error
from PIL import Image
from io import BytesIO
import base64
import tempfile
from Home import record_app_access  # 假设主代码文件名为 Home.py

# 设置环境变量IMAGEMAGICK_BINARY为ImageMagick的可执行文件路径
from moviepy.config import change_settings

change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

# 检查登录状态
if 'user_id' not in st.session_state or not st.session_state.user_id:
    st.warning("请先登录!")
    st.stop()

# 记录用户访问应用
record_app_access(st.session_state.user_id, "video_dubbing")

# 在侧边栏添加API密钥输入
st.sidebar.markdown("## API配置")
api_key = st.sidebar.text_input("输入通义API密钥", type="password")

# 只有输入API密钥后才能继续
if not api_key:
    st.warning("请先在侧边栏输入API密钥以继续")
    st.stop()

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
def create_new_dubbing_task(user_id, video_name=None, video_data=None):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        if video_data is not None:
            cursor.execute('''INSERT INTO video_dubbing_tasks (user_id, original_video_name, original_video)
                              VALUES (%s, %s, %s)''',
                           (user_id, video_name, video_data))
        else:
            cursor.execute('INSERT INTO video_dubbing_tasks (user_id) VALUES (%s)', (user_id,))
        conn.commit()
        task_id = cursor.lastrowid
        return task_id
    except Error as e:
        st.error(f"创建新配音任务时发生错误: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            conn.close()


def save_key_frames(task_id, frames):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        for frame_number, frame_data in enumerate(frames):
            cursor.execute('''INSERT INTO video_key_frames (task_id, frame_number, frame_data)
                              VALUES (%s, %s, %s)''',
                           (task_id, frame_number, frame_data))
        conn.commit()
    except Error as e:
        st.error(f"保存关键帧时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def save_analysis_result(task_id, analysis_text):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO video_analysis_results (task_id, analysis_text, edited_text)
                          VALUES (%s, %s, %s)''',
                       (task_id, analysis_text, analysis_text))
        conn.commit()
    except Error as e:
        st.error(f"保存分析结果时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def update_edited_text(task_id, edited_text):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''UPDATE video_analysis_results 
                          SET edited_text = %s 
                          WHERE task_id = %s''',
                       (edited_text, task_id))
        conn.commit()
    except Error as e:
        st.error(f"更新编辑文本时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def save_dubbing_audio(task_id, audio_data):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO dubbing_audio (task_id, audio_data)
                          VALUES (%s, %s)''',
                       (task_id, audio_data))
        conn.commit()
    except Error as e:
        st.error(f"保存配音音频时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def save_final_video(task_id, video_data):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO final_videos (task_id, final_video)
                          VALUES (%s, %s)''',
                       (task_id, video_data))
        conn.commit()
    except Error as e:
        st.error(f"保存最终视频时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def get_user_dubbing_tasks(user_id):
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(''' 
            SELECT t.id, 
                   t.original_video_name,
                   DATE(t.timestamp) as task_date,
                   TIME_FORMAT(t.timestamp, '%H:%i') as task_time,
                   t.status
            FROM video_dubbing_tasks t
            WHERE t.user_id = %s
            ORDER BY t.timestamp DESC
        ''', (user_id,))
        tasks = cursor.fetchall()
        return tasks
    except Error as e:
        st.error(f"获取用户配音任务列表时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


def get_task_data(task_id):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor(dictionary=True)

        # 获取任务基本信息
        cursor.execute('SELECT * FROM video_dubbing_tasks WHERE id = %s', (task_id,))
        task_info = cursor.fetchone()

        if not task_info:
            return None

        # 获取关键帧
        cursor.execute('SELECT frame_number, frame_data FROM video_key_frames WHERE task_id = %s ORDER BY frame_number',
                       (task_id,))
        frames = cursor.fetchall()

        # 获取分析结果
        cursor.execute('SELECT analysis_text, edited_text FROM video_analysis_results WHERE task_id = %s', (task_id,))
        analysis = cursor.fetchone()

        # 获取配音音频
        cursor.execute('SELECT audio_data FROM dubbing_audio WHERE task_id = %s', (task_id,))
        audio = cursor.fetchone()

        # 获取最终视频
        cursor.execute('SELECT final_video FROM final_videos WHERE task_id = %s', (task_id,))
        final_video = cursor.fetchone()

        return {
            'task_info': task_info,
            'frames': frames,
            'analysis': analysis,
            'audio': audio,
            'final_video': final_video
        }
    except Error as e:
        st.error(f"获取任务数据时发生错误: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            conn.close()


def delete_dubbing_task(task_id):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM video_dubbing_tasks WHERE id = %s', (task_id,))
        cursor.execute('DELETE FROM video_key_frames WHERE task_id = %s', (task_id,))
        cursor.execute('DELETE FROM video_analysis_results WHERE task_id = %s', (task_id,))
        cursor.execute('DELETE FROM dubbing_audio WHERE task_id = %s', (task_id,))
        cursor.execute('DELETE FROM final_videos WHERE task_id = %s', (task_id,))
        conn.commit()
    except Error as e:
        st.error(f"删除配音任务时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


# ----------------- 视频处理函数 -----------------
def get_video_length(video):
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    return duration


def calculate_summary_length(video_length_seconds, words_per_second=4):
    return int(video_length_seconds * words_per_second)


def process_video(task_id, video_bytes, api_key=None):
    try:
        if not api_key:
            st.error("请先输入API密钥")
            return "error"

        # 创建临时视频文件
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video.write(video_bytes)
            temp_video_path = temp_video.name

        # 使用OpenCV打开视频文件
        video = cv2.VideoCapture(temp_video_path)
        video_length = get_video_length(video)
        word_count = calculate_summary_length(video_length)

        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        # 确定关键帧位置
        frame_indices = [
            0,
            int(total_frames * 0.25),
            int(total_frames * 0.5),
            int(total_frames * 0.75),
            total_frames - 1
        ]

        frame_count = 0
        frames_data = []

        while video.isOpened():
            success, frame = video.read()
            if not success:
                break

            if frame_count in frame_indices:
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                frames_data.append(frame_bytes)

            frame_count += 1

        video.release()

        # 保存关键帧到数据库
        save_key_frames(task_id, frames_data)

        # 定义提示模板
        prompt = "你是一名内容创作者，帮我解释图片中的内容"

        # 准备多模态输入
        content_items = [{"image": f"data:image/jpeg;base64,{base64.b64encode(frame).decode('utf-8')}"}
                         for frame in frames_data]
        content_items.append({"text": prompt})

        messages = [{"role": "user", "content": content_items}]

        dashscope.api_key = api_key
        response = dashscope.MultiModalConversation.call(
            api_key=api_key,
            model='qwen-vl-max',
            messages=messages
        )

        if response.status_code == HTTPStatus.OK:
            picture_example = response.output.choices[0].message.content

            summry_prompt = PromptTemplate(
                template="""你作为一个文案编辑，通过参考文字生成摘要,
                1、不要在文稿中出现"图1"、"图2"这样的信息。
                2、文稿内容需要连贯，利于口播
                3、生成一段文字
                4、这段文字严格控制在{word_count}个字。
                下面是参考文字：{content}""",
                input_variables=["word_count", "content"]
            )

            llm = Tongyi(dashscope_api_key=api_key)
            llm_chain = summry_prompt | llm
            response = llm_chain.invoke({"word_count": word_count, "content": picture_example})

            # 保存分析结果到数据库
            save_analysis_result(task_id, response)

            return response
        else:
            return "error"

    except Exception as e:
        st.error(f"视频处理时发生错误: {str(e)}")
        return "error"
    finally:
        # 删除临时文件
        if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
            os.remove(temp_video_path)


def text_to_speech(task_id, text, api_key=None):
    try:
        if not api_key:
            st.error("请先输入API密钥")
            return None

        result = SpeechSynthesizer.call(
            api_key=api_key,
            model='sambert-zhiqi-v1',
            text=text,
            sample_rate=48000,
            format='wav'
        )

        if result.get_audio_data() is not None:
            audio_data = result.get_audio_data()
            save_dubbing_audio(task_id, audio_data)
            return audio_data
        else:
            st.error('生成语音失败。')
            return None
    except Exception as e:
        st.error(f"语音合成时发生错误: {str(e)}")
        return None


def split_text_by_time(text, duration):
    chars_per_segment = len(text) // 5
    segments = [text[i:i + chars_per_segment] for i in range(0, len(text), chars_per_segment)]

    if len(segments) > 5:
        segments = segments[:5]
    elif len(segments) < 5:
        segments.extend([''] * (5 - len(segments)))

    return segments


def merge_video_audio(task_id, video_bytes, audio_bytes, text):
    try:
        import tempfile
        import os

        # 创建临时视频文件
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video.write(video_bytes)
            temp_video_path = temp_video.name

        # 创建临时音频文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name

        # 初始化变量
        video_clip = None
        audio_clip = None
        final_clip = None

        try:
            # 加载视频文件，不带原音频
            video_clip = VideoFileClip(temp_video_path).without_audio()

            # 加载音频文件
            audio_clip = AudioFileClip(temp_audio_path)

            # 处理文本
            text = text.replace('"', '')

            # 将文本分成5段
            segments = split_text_by_time(text, video_clip.duration)

            # 计算每段字幕的显示时间
            segment_duration = video_clip.duration / 5

            # 为每个文本段创建字幕
            text_clips = []
            for i, segment_text in enumerate(segments):
                start_time = i * segment_duration
                end_time = (i + 1) * segment_duration
                txt_clip = TextClip(segment_text, fontsize=36, color='white',
                                    font='SimHei', align='center', method='label')
                txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(end_time - start_time).set_start(
                    start_time)
                text_clips.append(txt_clip)

            # 合并所有元素
            final_clip = CompositeVideoClip([video_clip] + text_clips)
            final_clip = final_clip.set_audio(audio_clip)

            # 创建临时输出文件
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
                output_path = temp_output.name

            # 写入最终视频文件
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac",
                                       threads=4, preset='ultrafast',
                                       ffmpeg_params=['-movflags', 'frag_keyframe+empty_moov'])

            # 读取输出视频数据
            with open(output_path, 'rb') as f:
                video_data = f.read()

            # 保存最终视频到数据库
            save_final_video(task_id, video_data)

            return video_data

        finally:
            # 显式关闭所有资源
            if final_clip is not None:
                final_clip.close()
            if audio_clip is not None:
                audio_clip.close()
            if video_clip is not None:
                video_clip.close()

            # 删除临时文件
            for file_path in [temp_video_path, temp_audio_path, output_path]:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass

    except Exception as e:
        st.error(f"合并视频和音频时发生错误: {e}")
        return None


# ----------------- 页面布局和交互 -----------------
def display_dubbing_task_selector(tasks):
    st.sidebar.markdown("## 历史任务")
    date_groups = {}
    for task in tasks:
        date = task[2]  # 任务日期
        if date not in date_groups:
            date_groups[date] = []
        date_groups[date].append(task)

    for date in sorted(date_groups.keys(), reverse=True):
        with st.sidebar.expander(f"🗓️ {date}"):
            for task in date_groups[date]:
                task_id, video_name, _, time, status = task
                btn_text = f"{time[:5]} | {video_name[:20] if video_name else '未命名'}"
                if st.button(btn_text, key=f"dub_task_{task_id}"):
                    st.session_state.current_task_id = task_id
                    st.session_state.show_task_message = f"success|已加载任务 [{time[:5]}]"


# 页面配置
st.set_page_config(page_title="视频配音应用", page_icon="🎬")
st.title('🎬 视频配音应用 🎙️')

# 获取用户任务列表
tasks = get_user_dubbing_tasks(st.session_state.user_id)

# 显示任务选择器
if tasks:
    display_dubbing_task_selector(tasks)

# 提示信息处理
if 'show_task_message' in st.session_state:
    msg_type, message = st.session_state.show_task_message.split("|")
    if msg_type == "success":
        st.success(message)
    elif msg_type == "info":
        st.info(message)
    del st.session_state.show_task_message

# 新建任务按钮
if st.sidebar.button("✨ 新建配音任务"):
    task_id = create_new_dubbing_task(st.session_state.user_id)
    st.session_state.current_task_id = task_id
    st.session_state.show_task_message = "success|新配音任务创建成功"
    st.rerun()

# 确保用户选择了任务
if 'current_task_id' not in st.session_state or st.session_state.current_task_id is None:
    st.warning("请先选择配音任务或新建任务")
    st.stop()

# 获取当前任务数据
task_data = get_task_data(st.session_state.current_task_id)

# 显示任务状态
if task_data and task_data['task_info']['status']:
    status = task_data['task_info']['status']
    if status == 'processing':
        st.warning("任务状态: 处理中")
    elif status == 'completed':
        st.success("任务状态: 已完成")
    elif status == 'failed':
        st.error("任务状态: 失败")

# 1. 上传视频
st.title('1、上传视频')
if task_data and task_data['task_info']['original_video']:
    # 显示已上传的视频
    video_bytes = task_data['task_info']['original_video']
    st.video(video_bytes)
    st.success(f"视频已上传: {task_data['task_info']['original_video_name']}")
else:
    uploaded_file = st.file_uploader("请选择一个视频文件", type=['mp4'])
    if uploaded_file is not None:
        # 保存视频到数据库
        task_id = st.session_state.current_task_id
        video_data = uploaded_file.getvalue()
        conn = create_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('''UPDATE video_dubbing_tasks 
                                SET original_video = %s, original_video_name = %s, status = 'processing'
                                WHERE id = %s''',
                               (video_data, uploaded_file.name, task_id))
                conn.commit()
                st.success("视频上传成功！")
                st.rerun()
            except Error as e:
                st.error(f"保存视频时发生错误: {str(e)}")
            finally:
                if conn.is_connected():
                    conn.close()

# 2. 解析视频
st.title('2、解析视频')
if task_data and task_data['task_info']['original_video']:
    if task_data.get('analysis'):
        # 显示已有的分析结果
        analysis_text = task_data['analysis']['edited_text']
        st.session_state['editable_text'] = analysis_text

        # 显示关键帧
        st.subheader("提取的关键帧:")
        cols = st.columns(5)
        for i, frame in enumerate(task_data['frames']):
            with cols[i]:
                st.image(Image.open(BytesIO(frame['frame_data'])), caption=f"帧 {i + 1}")

        # 显示可编辑的文本区域
        edited_text = st.text_area("视频解析结果",
                                   value=st.session_state.get('editable_text', analysis_text),
                                   height=150,
                                   key='editable_text_area')

        # 保存编辑后的文本
        if st.button("保存编辑"):
            update_edited_text(st.session_state.current_task_id, edited_text)
            st.session_state['editable_text'] = edited_text
            st.success("文本已保存！")
    else:
        if st.button("解析视频"):
            if not api_key:
                st.error("请先输入API密钥")
            else:
                with st.spinner("正在解析视频..."):
                    # 从数据库获取视频数据
                    video_data = task_data['task_info']['original_video']

                    # 调用解析函数
                    analysis_result = process_video(st.session_state.current_task_id, video_data, api_key)

                    if analysis_result != "error":
                        st.session_state['editable_text'] = analysis_result
                        st.rerun()
                    else:
                        st.error("视频解析失败")
else:
    st.warning("请先上传视频")

# 3. 生成语音
st.title('3、生成语音')
if task_data and task_data.get('analysis'):
    if task_data.get('audio'):
        # 显示已有的音频
        st.audio(task_data['audio']['audio_data'], format='audio/wav')
    else:
        if st.button("生成语音"):
            if not api_key:
                st.error("请先输入API密钥")
            else:
                with st.spinner("正在生成语音..."):
                    edited_text = task_data['analysis']['edited_text']
                    audio_data = text_to_speech(st.session_state.current_task_id, edited_text, api_key)
                    if audio_data:
                        st.audio(audio_data, format='audio/wav')
                        st.rerun()
else:
    st.warning("请先完成视频解析")

# 4. 合成视频
st.title('4、合成视频')
if task_data and task_data.get('audio'):
    if task_data.get('final_video'):
        # 显示最终视频
        st.video(task_data['final_video']['final_video'])
    else:
        if st.button("合成视频"):
            with st.spinner("正在合成视频..."):
                # 获取所有必要数据
                video_data = task_data['task_info']['original_video']
                audio_data = task_data['audio']['audio_data']
                edited_text = task_data['analysis']['edited_text']

                # 调用合成函数
                final_video = merge_video_audio(
                    st.session_state.current_task_id,
                    video_data,
                    audio_data,
                    edited_text
                )

                if final_video:
                    # 更新任务状态为已完成
                    conn = create_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute('''UPDATE video_dubbing_tasks 
                                            SET status = 'completed'
                                            WHERE id = %s''',
                                           (st.session_state.current_task_id,))
                            conn.commit()
                        except Error as e:
                            st.error(f"更新任务状态时发生错误: {str(e)}")
                        finally:
                            if conn.is_connected():
                                conn.close()

                    st.rerun()
                else:
                    st.error("视频合成失败")
else:
    st.warning("请先完成语音生成")