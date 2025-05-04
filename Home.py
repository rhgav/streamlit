import mysql.connector
from mysql.connector import Error
import streamlit as st
import pandas as pd


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


# ----------------- 数据库初始化（用户认证部分） -----------------
def init_db():
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()

        # 创建users表
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            username VARCHAR(255) UNIQUE,
                            password VARCHAR(255)
                        )''')

        # 创建user_app_access表（新增）
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_app_access (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT,
                            app_name VARCHAR(50),
                            access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')

        # 创建text_chats表（重命名）
        cursor.execute('''CREATE TABLE IF NOT EXISTS text_chats (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')

        # 创建text_chat_history表（重命名并增加model_type字段）
        cursor.execute('''CREATE TABLE IF NOT EXISTS text_chat_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            chat_id INT,
                            role TEXT,
                            message TEXT,
                            model_type VARCHAR(50),
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(chat_id) REFERENCES text_chats(id)
                        )''')

        # 创建picture_chats表（新增）
        cursor.execute('''CREATE TABLE IF NOT EXISTS picture_chats (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')

        # 创建picture_chat_history表（新增）
        cursor.execute('''CREATE TABLE IF NOT EXISTS picture_chat_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            chat_id INT,
                            role TEXT,
                            message TEXT,
                            model_type VARCHAR(50),
                            image_data LONGBLOB,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(chat_id) REFERENCES picture_chats(id)
                        )''')

        # 创建video_chats表（新增
        cursor.execute('''CREATE TABLE IF NOT EXISTS video_chats (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')

        # 创建video_chat_history表（新增）
        cursor.execute('''CREATE TABLE IF NOT EXISTS video_chat_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            chat_id INT,
                            role TEXT,
                            message TEXT,
                            model_type VARCHAR(50),
                            video_data LONGBLOB,  -- 可选：存储视频二进制数据
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(chat_id) REFERENCES video_chats(id)
                        )''')

        # 创建image_video_chats表（新增）
        cursor.execute('''CREATE TABLE IF NOT EXISTS image_video_chats (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')

        # 创建image_video_chat_history表（新增）
        cursor.execute('''CREATE TABLE IF NOT EXISTS image_video_chat_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            chat_id INT,
                            role TEXT,
                            message TEXT,
                            model_type VARCHAR(50),
                            image_data LONGBLOB,  -- 存储上传的图片二进制数据
                            video_data LONGBLOB,  -- 存储生成的视频二进制数据
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(chat_id) REFERENCES image_video_chats(id)
                        )''')

        # 创建voice_chats表
        cursor.execute('''CREATE TABLE IF NOT EXISTS voice_chats (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')

        # 创建voice_chat_history表
        cursor.execute('''CREATE TABLE IF NOT EXISTS voice_chat_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            chat_id INT,
                            role TEXT,
                            message TEXT,
                            model_type VARCHAR(50),
                            voice_choice VARCHAR(50),
                            audio_data LONGBLOB,  -- 存储音频二进制数据
                            audio_format VARCHAR(20),  -- 存储音频格式(mp3/wav等)
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(chat_id) REFERENCES voice_chats(id)
                        )''')

        # 创建music_chats表（记录对话基本信息）
        cursor.execute('''CREATE TABLE IF NOT EXISTS music_chats (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT,
                            model_type VARCHAR(20),  -- 'doubao' 或 'suno'
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')

        # 创建doubao_music_history表（记录豆包模型的历史记录）
        cursor.execute('''CREATE TABLE IF NOT EXISTS doubao_music_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            chat_id INT,
                            role TEXT,  -- 'user' 或 'assistant'
                            message TEXT,  -- 用户输入或AI输出的URL
                            generation_method VARCHAR(20),  -- 'prompt' 或 'lyrics'
                            gender VARCHAR(10),  -- 'Female' 或 'Male'
                            genre VARCHAR(50),  -- 音乐风格
                            mood VARCHAR(50),  -- 歌曲情绪
                            timbre VARCHAR(50),  -- 歌曲音色
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(chat_id) REFERENCES music_chats(id)
                        )''')

        # 创建suno_music_history表（记录Suno模型的历史记录）
        cursor.execute('''CREATE TABLE IF NOT EXISTS suno_music_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            chat_id INT,
                            role TEXT,  -- 'user' 或 'assistant'
                            message TEXT,  -- 用户输入或AI输出的描述
                            is_instrumental BOOLEAN,  -- 是否为纯音乐
                            music1_title TEXT,  -- 第一首音乐标题
                            music1_video LONGBLOB,  -- 第一首视频数据
                            music1_tags TEXT,  -- 第一首风格标签
                            music2_title TEXT,  -- 第二首音乐标题
                            music2_video LONGBLOB,  -- 第二首视频数据
                            music2_tags TEXT,  -- 第二首风格标签
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(chat_id) REFERENCES music_chats(id)
                        )''')

        # 创建video_dubbing_tasks表
        cursor.execute('''CREATE TABLE IF NOT EXISTS video_dubbing_tasks (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT,
                            original_video LONGBLOB,
                            original_video_name VARCHAR(255),
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(20) DEFAULT 'processing',
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')

        # 创建video_key_frames表
        cursor.execute('''CREATE TABLE IF NOT EXISTS video_key_frames (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            task_id INT,
                            frame_number INT,
                            frame_data LONGBLOB,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(task_id) REFERENCES video_dubbing_tasks(id)
                        )''')

        # 创建video_analysis_results表
        cursor.execute('''CREATE TABLE IF NOT EXISTS video_analysis_results (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            task_id INT,
                            analysis_text TEXT,
                            edited_text TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(task_id) REFERENCES video_dubbing_tasks(id)
                        )''')

        # 创建dubbing_audio表
        cursor.execute('''CREATE TABLE IF NOT EXISTS dubbing_audio (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            task_id INT,
                            audio_data LONGBLOB,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(task_id) REFERENCES video_dubbing_tasks(id)
                        )''')

        # 创建final_videos表
        cursor.execute('''CREATE TABLE IF NOT EXISTS final_videos (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            task_id INT,
                            final_video LONGBLOB,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(task_id) REFERENCES video_dubbing_tasks(id)
                        )''')



        # 检查admin用户是否存在
        cursor.execute('SELECT id FROM users WHERE username = "admin"')
        if not cursor.fetchone():
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', ('admin', 'admin'))

        conn.commit()
    except Error as e:
        st.error(f"初始化数据库时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


# ----------------- 记录用户应用访问（新增） -----------------
def record_app_access(user_id, app_name):
    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()

        # 查询用户最近一次访问的应用名称
        cursor.execute('''SELECT app_name FROM user_app_access 
                          WHERE user_id = %s 
                          ORDER BY access_time DESC 
                          LIMIT 1''', (user_id,))
        last_app = cursor.fetchone()

        # 如果最近一次访问的应用与当前应用不同，或者没有记录，则插入新记录
        if not last_app or last_app[0] != app_name:
            cursor.execute('''INSERT INTO user_app_access (user_id, app_name)
                            VALUES (%s, %s)''', (user_id, app_name))
            conn.commit()
    except Error as e:
        st.error(f"记录应用访问时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


# ----------------- 用户认证功能 -----------------
def register_user(username, password):
    if username.strip().lower() == 'admin':
        st.error("不能注册管理员账号")
        return

    conn = create_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, password))
        conn.commit()
        st.success("注册成功！")
    except mysql.connector.IntegrityError:
        st.error("用户名已存在，请选择其他用户名。")
    except Error as e:
        st.error(f"注册时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def login_user(username, password):
    conn = create_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()

        if user:
            if user[2] == password:  # 假设密码在第三列
                st.session_state.user_id = user[0]
                st.session_state.username = user[1]  # 保存用户名
                return user[0]
            else:
                st.error("密码错误，请重试。")
        else:
            st.error("用户名不存在，请检查或注册新用户。")
        return None
    except Error as e:
        st.error(f"登录时发生错误: {str(e)}")
    finally:
        if conn.is_connected():
            conn.close()


def get_all_users():
    conn = create_connection()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username FROM users')
        users = cursor.fetchall()
        return users
    except Error as e:
        st.error(f"获取用户列表时发生错误: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


def show_admin_interface():
    st.title("管理员界面")

    users = get_all_users()

    st.subheader("用户列表")
    if users:
        df_users = pd.DataFrame(users, columns=["ID", "用户名"])
        st.dataframe(df_users)
    else:
        st.write("暂无用户数据")

    if st.button("退出登录"):
        st.session_state.clear()
        st.rerun()


# ----------------- 主程序逻辑 -----------------
if __name__ == "__main__":
    # 页面配置
    st.set_page_config(page_title="用户管理系统", layout="wide")

    # 初始化数据库
    init_db()

    # 用户认证状态管理
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
        st.session_state.username = None

    # 用户未登录时显示认证界面
    if not st.session_state.user_id:
        st.title("用户认证")
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        action_type = st.radio("操作类型", ["登录", "注册"])

        if st.button("提交"):
            if action_type == "注册":
                register_user(username, password)
            else:
                user_id = login_user(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.rerun()
    else:
        # 记录用户访问应用（新增）
        record_app_access(st.session_state.user_id, "home")
        # 管理员界面逻辑
        if st.session_state.username == 'admin':
            show_admin_interface()
        else:
            st.title(f"欢迎, {st.session_state.username}!")
            if st.button("退出登录"):
                st.session_state.clear()
                st.rerun()