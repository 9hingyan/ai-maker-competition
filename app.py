# -*- coding: utf-8 -*-
"""
CAMPUS·东大 v0.3 —— AI 校园中枢（Web APP）
技术栈：Python + Streamlit + OpenAI 兼容 API（千问 Qwen 文本 + 视觉）
运行：streamlit run app.py
"""

import os
import json
import re
import base64
from datetime import date, datetime

import streamlit as st
import pandas as pd

# ============================ 页面基础配置 ============================
st.set_page_config(
    page_title="CAMPUS·东大",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================ 数据：2026-2027 学年第一学期校历 ============================
# 第 1 ~ 16 周（周一 ~ 周日）
CALENDAR = {
    1:  ("2026-09-07", "2026-09-13"),
    2:  ("2026-09-14", "2026-09-20"),
    3:  ("2026-09-21", "2026-09-27"),
    4:  ("2026-09-28", "2026-10-04"),
    5:  ("2026-10-05", "2026-10-11"),
    6:  ("2026-10-12", "2026-10-18"),
    7:  ("2026-10-19", "2026-10-25"),
    8:  ("2026-10-26", "2026-11-01"),
    9:  ("2026-11-02", "2026-11-08"),
    10: ("2026-11-09", "2026-11-15"),
    11: ("2026-11-16", "2026-11-22"),
    12: ("2026-11-23", "2026-11-29"),
    13: ("2026-11-30", "2026-12-06"),
    14: ("2026-12-07", "2026-12-13"),
    15: ("2026-12-14", "2026-12-20"),
    16: ("2026-12-21", "2026-12-27"),
}

TOTAL_WEEKS = len(CALENDAR)
WEEKDAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 关键时间节点
SRTP_DEADLINE = date(2026, 11, 1)   # 第 8 周周日：SRTP 申报截止

# ============================ 数据：默认课表（未导入前的兜底） ============================
COURSES = [
    {
        "name": "高等数学 A（一）", "time": "08:00 - 09:40", "location": "教一 205",
        "tag": "周一 · 第 1-2 节", "weekday": "周一", "start_week": 1, "end_week": 16,
        "week_type": "每周", "periods": "1-2",
    },
    {
        "name": "工科导论", "time": "14:00 - 15:40", "location": "教三 402",
        "tag": "周三 · 第 6-7 节", "weekday": "周三", "start_week": 1, "end_week": 16,
        "week_type": "每周", "periods": "6-7",
    },
]

# ============================ 数据：模拟官网通知（第一版先跑通接口，不写爬虫） ============================
MOCK_NOTICES = [
    {
        "id": 1,
        "title": "关于2026年SRTP大学生科研训练计划项目申报的通知",
        "url": "https://jwc.seu.edu.cn/srtp-2026",
        "text": "2026-2027学年SRTP项目申报工作正式启动。请有意向的同学于第8周前登录教务系统完成网上申报，并提交纸质版申请书一式两份至院系教学办公室。逾期不再受理。",
    },
    {
        "id": 2,
        "title": "关于全国大学英语四六级考试报名的通知",
        "url": "https://jwc.seu.edu.cn/cet-2026",
        "text": "2026年12月全国大学英语四六级考试（CET）报名已开始，报名截止时间为第9周周五，请同学们在规定时间内登录报名系统完成信息核对与缴费。",
    },
    {
        "id": 3,
        "title": "关于开展期中教学检查的通知",
        "url": "https://jwc.seu.edu.cn/midterm-check",
        "text": "学校定于第10周开展期中教学检查，届时将随机抽查课堂出勤与作业批改情况，请同学们做好准备。",
    },
    {
        "id": 4,
        "title": "关于举办研究生学术讲座的通知",
        "url": "https://smse.seu.edu.cn/lecture",
        "text": "材料科学与工程学院将于本周五下午举办面向研究生的学术讲座《纳米材料前沿进展》，欢迎研究生同学参加。",
    },
    {
        "id": 5,
        "title": "关于教职工趣味运动会的通知",
        "url": "https://gh.seu.edu.cn/sports-meeting",
        "text": "校工会定于11月中旬举办教职工趣味运动会，欢迎各位教职工踊跃报名参加。",
    },
    {
        "id": 6,
        "title": "关于校园歌手大赛海选的通知",
        "url": "https://tw.seu.edu.cn/singer",
        "text": "校团委将于第11周举办校园歌手大赛海选，欢迎热爱音乐的同学报名展示才华。",
    },
]

# ============================ 数据：网站导航 ============================
LINKS = [
    {"name": "教务处",       "desc": "选课、成绩、SRTP 申报",      "url": "https://jwc.seu.edu.cn"},
    {"name": "网上办事大厅", "desc": "课表查询、考试安排、请假",  "url": "https://ehall.seu.edu.cn"},
    {"name": "图书馆",       "desc": "馆藏检索、座位预约、数据库", "url": "https://lib.seu.edu.cn"},
    {"name": "网络与信息中心", "desc": "校园网、正版软件、VPN",     "url": "https://nic.seu.edu.cn"},
    {"name": "一卡通服务",   "desc": "充值、消费记录、挂失",       "url": "https://card.seu.edu.cn"},
    {"name": "学校邮箱",     "desc": "邮件收发、日程",            "url": "https://mail.seu.edu.cn"},
]

# ============================ API 配置（可按需修改） ============================
# 千问（Qwen）· 阿里云百炼 DashScope：OpenAI 兼容，一个 Key 同时用于文本 + 视觉
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_TEXT_MODEL = "qwen-plus"        # 文本：通知过滤
QWEN_VISION_MODEL = "qwen-vl-plus"   # 视觉：课表截图识别

# ============================ Prompt 模板 ============================
SCHEDULE_VISION_PROMPT = """请识别这张课表截图，提取里面所有课程。对每门课提取：
- name：课程名
- time：上课时间（如 08:00 - 09:40）
- location：上课地点（如 教一 205）
- weekday：星期，只能是「周一」到「周日」之一
- periods：节次（如 1-2、3-4、6-7）
- start_week：开始周，整数
- end_week：结束周，整数
- week_type：周次类型，只能是「每周」「单周」「双周」之一

严格只输出一个 JSON 数组，不要输出任何解释文字、不要用 markdown 代码块。示例：
[
  {"name": "高等数学A", "time": "08:00 - 09:40", "location": "教一 205", "weekday": "周一", "periods": "1-2", "start_week": 1, "end_week": 16, "week_type": "每周"}
]
无法判断周次时，start_week 填 1、end_week 填 16、week_type 填「每周」。识别不到其他某项就填 ""。不要遗漏任何课程。"""

NOTICE_SYSTEM_PROMPT = """你是「CAMPUS·东大」的通知过滤助手。请阅读给定的官网通知列表，完成两件事：

1. 过滤：判断每条通知是否与「东南大学大一本科生」直接相关（选课、考试报名、SRTP/竞赛申报、缴费、奖学金、评奖评优、期中/期末安排等）。与大一新生无关的（研究生讲座、教职工活动、其他院系专属活动等）标记为不相关。

2. 计算日期：如果通知正文出现「第X周」「第X周前/截止」「第X周周X」等表述，必须结合下面提供的校历，把它换算成具体日期（格式 YYYY-MM-DD）。例如「第8周截止」= 第8周周日 = 2026-11-01。

严格只输出 JSON，不要输出任何解释文字、不要用 markdown 代码块。格式：
{
  "notices": [
    {
      "id": 原通知的 id,
      "relevant": true 或 false,
      "action": "一句话行动项（不相关时留空字符串）",
      "deadline": "具体截止日期 YYYY-MM-DD，没有则空字符串",
      "summary": "一句话摘要"
    }
  ]
}"""

# ============================ 会话状态初始化 ============================
if "courses" not in st.session_state:
    st.session_state["courses"] = COURSES

# ============================ 全局样式（Notion 风格极简） ============================
st.markdown(
    """
    <style>
    :root {
        --bg: #F3F5F9;
        --card: #FFFFFF;
        --text: #23293A;
        --muted: #7B849B;
        --border: #E6EAF2;
        --accent: #4D68D8;
        --red: #D64A58;
        --red-bg: #FFF0F1;
        --yellow: #9A6A13;
        --yellow-bg: #FFF6DF;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background-color: var(--bg);
    }
    html, body, .stApp, .stMarkdown {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                     "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
        color: var(--text);
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
    [data-testid="stHeader"] { background: transparent; }

    section[data-testid="stSidebar"] {
        background-color: #F8FAFD;
        border-right: 1px solid var(--border);
        width: 248px !important;
        min-width: 248px !important;
        max-width: 248px !important;
    }
    section[data-testid="stSidebar"] > div { padding-top: 1.25rem; }
    .block-container { padding: 1.9rem 2.25rem 2.5rem; max-width: 1180px; }

    /* 顶部 Tab 导航 */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid var(--border);
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-size: 0.95rem; font-weight: 500; color: var(--muted); padding: 8px 4px;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        color: var(--text); font-weight: 600;
    }

    /* 侧边栏标题 */
    .sidebar-logo { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; padding: 0.2rem 0; }
    .sidebar-sub  { font-size: 0.8rem; color: var(--muted); margin-bottom: 0.6rem; }
    .sidebar-foot { font-size: 0.75rem; color: var(--muted); margin-top: 0.5rem; }

    .section-title {
        font-size: 0.78rem; font-weight: 600; color: var(--muted);
        letter-spacing: 0.05em; margin: 4px 0 10px 0;
    }

    .countdown-card {
        display: flex; align-items: center; gap: 24px;
        background: var(--card); border: 1px solid var(--border);
        border-radius: 10px; padding: 20px 24px; margin-bottom: 18px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .cc-item   { display: flex; align-items: center; gap: 12px; }
    .cc-emoji  { font-size: 1.6rem; }
    .cc-label  { font-size: 0.78rem; color: var(--muted); }
    .cc-value  { font-size: 1.05rem; font-weight: 600; }
    .cc-divider { width: 1px; height: 40px; background: var(--border); }

    .progress-track { width: 100%; height: 6px; background: #EFEFEC; border-radius: 999px; overflow: hidden; margin: 8px 0 12px 0; }
    .progress-fill  { height: 100%; background: var(--accent); border-radius: 999px; }

    .st-key-week_picker button {
        min-height: 2rem; padding: 0.25rem 0.55rem; border-radius: 6px;
        font-size: 0.78rem; justify-content: flex-start;
    }
    .st-key-week_picker button p { width: 100%; text-align: left; }

    .dashboard-brand {
        display: flex; align-items: center; gap: 10px; padding: 0 4px 18px;
    }
    .brand-mark {
        width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
        color: white; font-size: 1rem; font-weight: 800;
        background: linear-gradient(135deg, #8264E8 0%, #4169D8 100%);
        box-shadow: 0 7px 16px rgba(77, 104, 216, 0.22);
    }
    .brand-name { font-size: 1.02rem; font-weight: 750; color: var(--text); }
    .brand-sub { font-size: 0.7rem; color: var(--muted); margin-top: 2px; }

    .st-key-nav_menu button {
        justify-content: flex-start; text-align: left; min-height: 2.55rem;
        border: 0; border-radius: 9px; background: transparent;
        color: #5C667C; font-size: 0.88rem; padding: 0.45rem 0.75rem;
        box-shadow: none;
    }
    .st-key-nav_menu button p { text-align: left; }
    .st-key-nav_menu button:hover {
        background: #EEF2F9; color: var(--text); border: 0;
    }
    .st-key-nav_menu button[kind="primary"] {
        background: #E9EEFF; color: #365BCB; font-weight: 650;
        box-shadow: inset 3px 0 0 #4D68D8;
    }

    .main-kicker { color: var(--muted); font-size: 0.83rem; margin-bottom: 4px; }
    .dashboard-hero {
        display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 18px;
        align-items: stretch; margin-bottom: 18px;
    }
    .hero-copy {
        background: var(--card); border: 1px solid var(--border); border-radius: 14px;
        padding: 22px 24px; box-shadow: 0 3px 16px rgba(41, 52, 84, 0.045);
    }
    .hero-greeting { color: #737D93; font-size: 0.86rem; }
    .hero-date { color: var(--text); font-size: 1.75rem; line-height: 1.25; font-weight: 760; margin: 5px 0 8px; }
    .hero-meta { color: var(--muted); font-size: 0.8rem; }
    .hero-meta strong { color: #4D68D8; font-weight: 650; }
    .next-class {
        background: linear-gradient(135deg, #F7F9FF 0%, #EFF3FF 100%);
        border: 1px solid #E0E6FA; border-radius: 14px; padding: 18px 20px;
        box-shadow: 0 3px 16px rgba(41, 52, 84, 0.04);
    }
    .next-label { color: #7B85A0; font-size: 0.74rem; margin-bottom: 10px; }
    .next-name { color: #2F3A57; font-size: 1rem; font-weight: 700; }
    .next-meta { color: #7D87A1; font-size: 0.75rem; margin-top: 6px; line-height: 1.5; }

    .st-key-quick_schedule button, .st-key-quick_ai button, .st-key-quick_links button {
        min-height: 4.6rem; justify-content: flex-start; text-align: left;
        background: var(--card); border: 1px solid var(--border); border-radius: 11px;
        color: #47516A; padding: 0.7rem 0.9rem; box-shadow: 0 3px 14px rgba(41, 52, 84, 0.035);
    }
    .st-key-quick_schedule button:hover, .st-key-quick_ai button:hover, .st-key-quick_links button:hover {
        border-color: #C8D2F6; background: #FAFBFF;
    }
    .st-key-quick_schedule button p, .st-key-quick_ai button p, .st-key-quick_links button p {
        text-align: left; white-space: pre-line; line-height: 1.5;
    }

    .panel {
        background: var(--card); border: 1px solid var(--border); border-radius: 14px;
        padding: 18px 20px; box-shadow: 0 3px 16px rgba(41, 52, 84, 0.04);
        margin-bottom: 16px;
    }
    .panel-head {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 10px;
    }
    .panel-title { color: var(--text); font-size: 0.95rem; font-weight: 700; }
    .panel-meta { color: var(--muted); font-size: 0.75rem; }
    .course-row {
        display: grid; grid-template-columns: 58px 3px minmax(0, 1fr) auto;
        gap: 14px; align-items: center; padding: 14px 4px;
        border-top: 1px solid #EFF2F7;
    }
    .course-row:first-of-type { border-top: 0; }
    .course-clock { text-align: right; color: #5F6980; line-height: 1.45; font-size: 0.76rem; }
    .course-clock strong { display: block; font-weight: 650; color: #3A4358; }
    .course-line { width: 3px; height: 34px; border-radius: 99px; background: #4D68D8; }
    .crow-name { color: #2C3448; font-size: 0.94rem; font-weight: 680; }
    .crow-meta { color: var(--muted); font-size: 0.75rem; margin-top: 4px; }
    .crow-day {
        color: #54617E; font-size: 0.73rem; background: #F2F5FB;
        border-radius: 999px; padding: 4px 9px; white-space: nowrap;
    }
    .empty-card {
        background: linear-gradient(180deg, #FBFCFE 0%, #F7F9FD 100%);
        border: 1px dashed #DCE2ED; border-radius: 14px; min-height: 150px;
        display: grid; place-items: center; text-align: center; padding: 24px;
        color: #7D879C; margin-bottom: 16px;
    }
    .empty-icon {
        width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center;
        background: #F0F3F9; margin: 0 auto 9px; color: #9BA4B7;
    }
    .empty-title { color: #59637A; font-size: 0.88rem; font-weight: 650; }
    .empty-copy { color: #98A0B1; font-size: 0.76rem; margin-top: 5px; }

    .course-card {
        display: flex; justify-content: space-between; align-items: center;
        background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; padding: 16px 18px; margin-bottom: 10px;
    }
    .course-left  { display: flex; flex-direction: column; gap: 4px; }
    .course-name  { font-size: 1rem; font-weight: 600; }
    .course-meta  { font-size: 0.85rem; color: var(--muted); display: flex; gap: 14px; }
    .course-tag   { font-size: 0.75rem; color: var(--muted); background: #F1F1EF; border-radius: 999px; padding: 3px 10px; white-space: nowrap; }

    .notif-card {
        background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; padding: 16px 18px; margin-bottom: 12px;
    }
    .notif-top { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .status-tag { display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 2px 9px; border-radius: 999px; white-space: nowrap; }
    .tag-red    { background: var(--red-bg); color: var(--red); }
    .tag-yellow { background: var(--yellow-bg); color: var(--yellow); }
    .notif-title   { font-size: 0.98rem; font-weight: 600; }
    .notif-summary { font-size: 0.88rem; color: #4B4B47; line-height: 1.6; margin-bottom: 6px; }
    .notif-deadline { font-size: 0.82rem; color: var(--muted); margin-bottom: 6px; }
    .notif-link    { font-size: 0.82rem; color: #3B82F6; text-decoration: none; }
    .notif-link:hover { text-decoration: underline; }

    .link-card {
        display: block; background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; text-decoration: none;
        transition: background 0.15s ease;
    }
    .link-card:hover { background: #FAFAF9; }
    .link-name { font-weight: 600; font-size: 0.95rem; color: var(--text); }
    .link-desc { font-size: 0.82rem; color: var(--muted); margin-top: 2px; }

    .day-label {
        font-size: 0.82rem; font-weight: 700; color: var(--muted);
        letter-spacing: 0.03em; margin: 14px 0 7px;
    }
    .muted-note { color: var(--muted); font-size: 0.85rem; }

    /* 简洁工作台：减少卡片、阴影和强调色 */
    :root {
        --bg: #F7F7F8;
        --card: #FFFFFF;
        --text: #1F2328;
        --muted: #6F7782;
        --border: #E6E8EB;
        --accent: #4B63D8;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background: var(--bg);
    }
    .block-container {
        max-width: 1080px;
        padding: 2rem 2.2rem 3rem;
    }
    section[data-testid="stSidebar"] {
        width: 228px !important;
        min-width: 228px !important;
        max-width: 228px !important;
        background: #FBFBFC;
        border-right: 1px solid #ECEDEF;
    }
    .dashboard-brand { padding: 0 2px 18px; gap: 9px; }
    .brand-mark {
        width: 28px; height: 28px; border-radius: 7px;
        background: #1F2328; box-shadow: none;
        font-size: 0.82rem; font-weight: 700;
    }
    .brand-name { font-size: 0.92rem; font-weight: 650; }
    .brand-sub { font-size: 0.67rem; }

    .st-key-nav_menu { gap: 2px; }
    .st-key-nav_menu button {
        min-height: 2.25rem;
        border: 0;
        border-radius: 7px;
        padding: 0.3rem 0.65rem;
        color: #59616C;
        font-size: 0.82rem;
        box-shadow: none;
    }
    .st-key-nav_menu button:hover { background: #F0F1F3; }
    .st-key-nav_menu button[kind="primary"] {
        background: #EFF1F4;
        color: #24282E;
        font-weight: 600;
        box-shadow: none;
    }
    .st-key-week_picker { gap: 1px; }
    .st-key-week_picker button {
        min-height: 1.95rem;
        padding: 0.15rem 0.5rem;
        border: 0;
        background: transparent;
        color: #737B86;
        font-size: 0.74rem;
        box-shadow: none;
    }
    .st-key-week_picker button:hover {
        background: #F1F2F4;
        color: #24282E;
    }
    .st-key-week_picker button[kind="primary"] {
        background: #ECEEF2;
        color: #24282E;
        font-weight: 600;
    }
    .section-title {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        color: #7A818A;
    }
    .sidebar-foot { color: #949AA2; font-size: 0.68rem; }

    .main-kicker {
        font-size: 0.79rem;
        color: #7A818A;
        margin-bottom: 5px;
    }
    .dashboard-hero {
        grid-template-columns: minmax(0, 1fr) 260px;
        gap: 34px;
        align-items: center;
        padding: 4px 0 22px;
        margin-bottom: 20px;
        border-bottom: 1px solid #E8E9EB;
    }
    .hero-copy {
        padding: 0;
        border: 0;
        border-radius: 0;
        background: transparent;
        box-shadow: none;
    }
    .hero-date {
        font-size: 1.58rem;
        font-weight: 650;
        letter-spacing: -0.025em;
        margin: 3px 0 7px;
    }
    .hero-meta { font-size: 0.78rem; }
    .hero-meta strong { color: #5E6670; font-weight: 600; }
    .next-class {
        padding: 1px 0 1px 22px;
        border: 0;
        border-left: 1px solid #E4E6E9;
        border-radius: 0;
        background: transparent;
        box-shadow: none;
    }
    .next-label { color: #8A9098; font-size: 0.69rem; margin-bottom: 0; }
    .next-name { color: #2B3036; font-size: 0.9rem; font-weight: 600; margin-top: 7px; }
    .next-meta { color: #7B828C; font-size: 0.7rem; margin-top: 5px; }

    .panel {
        padding: 18px 20px;
        border: 1px solid #E7E8EA;
        border-radius: 10px;
        background: #FFFFFF;
        box-shadow: none;
    }
    .panel-head { margin-bottom: 4px; }
    .panel-title { font-size: 0.9rem; font-weight: 600; }
    .panel-meta { font-size: 0.7rem; color: #8A9098; }
    .course-row {
        grid-template-columns: 52px 2px minmax(0, 1fr) auto;
        gap: 12px;
        padding: 13px 2px;
        border-top: 1px solid #F0F1F2;
    }
    .course-line { width: 2px; height: 28px; }
    .course-clock { font-size: 0.72rem; color: #7A818A; }
    .course-clock strong { font-size: 0.75rem; color: #3D434B; font-weight: 600; }
    .crow-name { font-size: 0.87rem; font-weight: 600; color: #2B3036; }
    .crow-meta { font-size: 0.7rem; color: #8A9098; }
    .crow-day { padding: 0; background: transparent; color: #8A9098; font-size: 0.7rem; }
    .empty-card {
        min-height: 120px;
        padding: 20px;
        border: 1px dashed #E4E6E9;
        border-radius: 9px;
        background: transparent;
    }
    .empty-icon { width: 28px; height: 28px; background: #F2F3F4; }
    .empty-title { font-size: 0.81rem; color: #666D75; }
    .empty-copy { font-size: 0.7rem; color: #979CA3; }

    .notif-card, .link-card {
        border: 1px solid #E7E8EA;
        border-radius: 9px;
        box-shadow: none;
        background: #FFFFFF;
    }
    .notif-title { font-weight: 600; }
    .link-card:hover { background: #FAFAFB; }
    .muted-note { font-size: 0.78rem; color: #7A818A; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================ 核心函数 ============================
def get_week_info(today: date):
    """返回 (第几周, 周几)；不在学期内时第几周为 None。"""
    for week, (start, end) in CALENDAR.items():
        s, e = date.fromisoformat(start), date.fromisoformat(end)
        if s <= today <= e:
            return week, WEEKDAYS_CN[today.weekday()]
    return None, WEEKDAYS_CN[today.weekday()]


def _calendar_text() -> str:
    """把校历转成文本，喂给 LLM 用于「第X周 → 具体日期」的换算。"""
    return "\n".join(f"第 {w} 周：{s} 至 {e}" for w, (s, e) in CALENDAR.items())


def _extract_json(text: str):
    """从模型输出中稳健地提取 JSON（自动剥离 markdown 代码围栏）。"""
    text = (text or "").strip()
    if not text:
        raise ValueError("模型返回为空")
    m = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    else:
        starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
        if starts:
            start = min(starts)
            end = max(text.rfind("}"), text.rfind("]"))
            if end > start:
                text = text[start:end + 1]
    return json.loads(text)


def _resolve_key(sidebar_val: str, key_name: str) -> str:
    """API Key 解析优先级：侧边栏输入 > st.secrets > 环境变量。"""
    if sidebar_val and sidebar_val.strip():
        return sidebar_val.strip()
    try:
        v = st.secrets.get(key_name, "")
        if v:
            return str(v).strip()
    except Exception:
        pass
    return os.environ.get(key_name, "").strip()


@st.cache_data(show_spinner=False)
def parse_schedule_image(image_bytes: bytes, mime_type: str, api_key: str) -> list:
    """功能1：调用视觉模型（Qwen-VL）识别课表截图，返回课程列表。"""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=QWEN_BASE_URL)
    b64 = base64.b64encode(image_bytes).decode()
    resp = client.chat.completions.create(
        model=QWEN_VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                {"type": "text", "text": SCHEDULE_VISION_PROMPT},
            ],
        }],
        temperature=0.1,
    )
    content = resp.choices[0].message.content
    data = _extract_json(content)
    if isinstance(data, dict):
        data = data.get("courses", data.get("schedule", data))
    if not isinstance(data, list):
        raise ValueError("模型未返回课表数组")

    return [_normalize_course(item) for item in data if isinstance(item, dict)]


@st.cache_data(show_spinner=False, ttl=3600)
def filter_notices(notices: list, api_key: str) -> list:
    """功能2：调用千问（Qwen）过滤通知，结合校历把「第X周」换算成具体日期。"""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=QWEN_BASE_URL)
    user_prompt = (
        "以下是本学年校历（周一为每周第一天）：\n"
        f"{_calendar_text()}\n\n"
        "以下是从学校官网抓取的原始通知（JSON 数组）：\n"
        f"{json.dumps(notices, ensure_ascii=False, indent=2)}\n\n"
        "请逐条分析并输出结果。"
    )
    resp = client.chat.completions.create(
        model=QWEN_TEXT_MODEL,
        messages=[
            {"role": "system", "content": NOTICE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    data = _extract_json(content)
    if isinstance(data, list):
        return data
    return data.get("notices", [])


def _clean(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v).strip()


def _to_int(value, default: int) -> int:
    """把模型或表格中的周次转成整数，无法识别时使用兜底值。"""
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    try:
        return int(float(value))
    except (TypeError, ValueError):
        match = re.search(r"\d+", str(value or ""))
        return int(match.group()) if match else default


def _normalize_weekday(value, tag: str = "") -> str:
    """兼容「周一」「星期一」「1」等写法，统一为 WEEKDAYS_CN。"""
    text = f"{_clean(value)} {_clean(tag)}"
    aliases = {
        "周一": ("周一", "星期一"), "周二": ("周二", "星期二"),
        "周三": ("周三", "星期三"), "周四": ("周四", "星期四"),
        "周五": ("周五", "星期五"), "周六": ("周六", "星期六"),
        "周日": ("周日", "周天", "星期日", "星期天"),
    }
    for weekday, names in aliases.items():
        if any(name in text for name in names):
            return weekday
    try:
        number = _to_int(value, 0)
        if 1 <= number <= 7:
            return WEEKDAYS_CN[number - 1]
    except (TypeError, ValueError):
        pass
    return ""


def _normalize_week_type(value) -> str:
    text = _clean(value)
    if "单" in text:
        return "单周"
    if "双" in text:
        return "双周"
    return "每周"


def _infer_periods(tag: str) -> str:
    match = re.search(r"第\s*(\d+)\s*[-~至到]\s*(\d+)\s*节", _clean(tag))
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r"第\s*(\d+)\s*节", _clean(tag))
    return match.group(1) if match else ""


def _normalize_course(item: dict) -> dict:
    """统一截图模型、表格编辑器和旧版默认课表的数据结构。"""
    tag = _clean(item.get("tag") or item.get("周次/节次") or "")
    weekday = _normalize_weekday(item.get("weekday") or item.get("星期"), tag)
    periods = _clean(item.get("periods") or item.get("节次")) or _infer_periods(tag)
    start_week = _to_int(
        item.get("start_week", item.get("起始周")), 1
    )
    end_week = _to_int(
        item.get("end_week", item.get("结束周")), TOTAL_WEEKS
    )
    start_week = min(max(start_week, 1), TOTAL_WEEKS)
    end_week = min(max(end_week, 1), TOTAL_WEEKS)
    if start_week > end_week:
        start_week, end_week = end_week, start_week

    if not tag and weekday:
        period_text = f" · 第 {periods} 节" if periods else ""
        tag = f"{weekday}{period_text}"
    return {
        "name": _clean(item.get("name") or item.get("课程名")),
        "time": _clean(item.get("time") or item.get("上课时间")),
        "location": _clean(item.get("location") or item.get("地点")),
        "tag": tag,
        "weekday": weekday,
        "start_week": start_week,
        "end_week": end_week,
        "week_type": _normalize_week_type(item.get("week_type") or item.get("周次类型")),
        "periods": periods,
    }


def _course_occurs_in_week(course: dict, week: int) -> bool:
    start_week = _to_int(course.get("start_week"), 1)
    end_week = _to_int(course.get("end_week"), TOTAL_WEEKS)
    if not start_week <= week <= end_week:
        return False
    week_type = _normalize_week_type(course.get("week_type"))
    if week_type == "单周":
        return week % 2 == 1
    if week_type == "双周":
        return week % 2 == 0
    return True


def _courses_for_week(courses: list, week: int) -> list:
    filtered = [
        _normalize_course(course)
        for course in courses
        if _course_occurs_in_week(course, week)
    ]

    def sort_key(course: dict):
        weekday = _normalize_weekday(course.get("weekday"), course.get("tag", ""))
        day_index = WEEKDAYS_CN.index(weekday) if weekday in WEEKDAYS_CN else 99
        period_match = re.search(r"\d+", _clean(course.get("periods")))
        period_index = int(period_match.group()) if period_match else 999
        return day_index, period_index, course.get("time", "")

    return sorted(filtered, key=sort_key)


def _greeting_text(now: datetime) -> str:
    if now.hour < 6:
        return "夜深了"
    if now.hour < 11:
        return "上午好"
    if now.hour < 14:
        return "中午好"
    if now.hour < 18:
        return "下午好"
    return "晚上好"


def _next_course(courses: list, selected_week: int, now: datetime):
    """优先返回今天尚未开始的课程，其次返回本周接下来的课程。"""
    if not courses:
        return None
    current_week, _ = get_week_info(now.date())
    if selected_week != current_week:
        return courses[0]

    today_name = WEEKDAYS_CN[now.weekday()]
    now_minutes = now.hour * 60 + now.minute

    def start_minutes(course):
        match = re.search(r"(\d{1,2}):(\d{2})", _clean(course.get("time")))
        return int(match.group(1)) * 60 + int(match.group(2)) if match else 24 * 60

    today_courses = [c for c in courses if c.get("weekday") == today_name]
    later_today = [c for c in today_courses if start_minutes(c) >= now_minutes]
    if later_today:
        return min(later_today, key=start_minutes)

    today_index = now.weekday()
    later_week = [
        c for c in courses
        if c.get("weekday") in WEEKDAYS_CN
        and WEEKDAYS_CN.index(c["weekday"]) > today_index
    ]
    return later_week[0] if later_week else None


def _course_time_parts(course: dict) -> tuple:
    times = re.findall(r"\d{1,2}:\d{2}", _clean(course.get("time")))
    if len(times) >= 2:
        return times[0], times[1]
    return (times[0], "") if times else ("--:--", "")


def _set_nav(view: str) -> None:
    st.session_state["nav_view"] = view


def _render_dashboard_header(today: date, week, weekday: str, selected_week: int) -> None:
    courses = _courses_for_week(st.session_state.get("courses", COURSES), selected_week)
    next_course = _next_course(courses, selected_week, datetime.now())
    week_text = f"第 {week} 教学周" if week else "假期中"
    next_html = """
        <div class="next-label">下一节课</div>
        <div class="next-name">暂无课程</div>
        <div class="next-meta">可以切换左侧周次查看其他安排</div>
    """
    if next_course:
        next_html = f"""
            <div class="next-label">下一节课 · 第 {selected_week} 周</div>
            <div class="next-name">{next_course.get('name', '')}</div>
            <div class="next-meta">{next_course.get('weekday', '')} · {next_course.get('time', '')}<br>{next_course.get('location', '')}</div>
        """
    st.markdown(
        f"""
        <div class="dashboard-hero">
            <div class="hero-copy">
                <div class="main-kicker">{_greeting_text(datetime.now())}，同学</div>
                <div class="hero-date">{today.year}年{today.month}月{today.day}日 · {weekday}</div>
                <div class="hero-meta">2026–2027 学年第一学期　<strong>{week_text} · 共 {TOTAL_WEEKS} 周</strong></div>
            </div>
            <div class="next-class">{next_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _map_notice(p: dict, original_by_id: dict) -> dict:
    """把 AI 解析结果映射成通知卡片的渲染结构，并按截止日期远近判断紧急程度。"""
    orig = original_by_id.get(p.get("id"), {})
    deadline = (p.get("deadline") or "").strip()
    level, emoji = "关注", "🟡"
    if deadline:
        try:
            days = (date.fromisoformat(deadline) - date.today()).days
            if 0 <= days <= 7:
                level, emoji = "紧急", "🔴"
        except ValueError:
            pass
    return {
        "level": level,
        "emoji": emoji,
        "title": (p.get("action") or p.get("summary") or orig.get("title") or "").strip(),
        "summary": (p.get("summary") or "").strip(),
        "deadline": deadline,
        "link": orig.get("url", "https://www.seu.edu.cn"),
    }


# ============================ 渲染函数 ============================
def _countdown_card(today: date, week, weekday: str) -> str:
    days_left = (SRTP_DEADLINE - today).days
    if days_left > 0:
        deadline_str = f"距第 8 周截止还有 {days_left} 天"
    elif days_left == 0:
        deadline_str = "今天就是 SRTP 申报截止日！"
    else:
        deadline_str = "SRTP 申报已截止"
    week_str = f"第 {week} 周 · {weekday}" if week else "假期中（不在教学周内）"
    return f"""
    <div class="countdown-card">
        <div class="cc-item">
            <div class="cc-emoji">🗓️</div>
            <div><div class="cc-label">今日时间</div><div class="cc-value">{week_str}</div></div>
        </div>
        <div class="cc-divider"></div>
        <div class="cc-item">
            <div class="cc-emoji">⏰</div>
            <div><div class="cc-label">SRTP 申报截止</div><div class="cc-value">{deadline_str}</div></div>
        </div>
    </div>
    """


def _set_selected_week(week: int) -> None:
    st.session_state["selected_week"] = week


def _render_week_picker(selected_week: int) -> None:
    """渲染可点击的周次列表，点击后直接切换右侧课表。"""
    with st.container(key="week_picker", gap="small"):
        for week, (start, end) in CALENDAR.items():
            s, e = date.fromisoformat(start), date.fromisoformat(end)
            label = f"第 {week} 周  ·  {s.month}/{s.day}–{e.month}/{e.day}"
            st.button(
                label,
                key=f"select_week_{week}",
                type="primary" if week == selected_week else "secondary",
                use_container_width=True,
                on_click=_set_selected_week,
                args=(week,),
            )


def _course_card(c, show_day: bool = True) -> str:
    start, end = _course_time_parts(c)
    day_colors = {
        "周一": "#4D68D8", "周二": "#4EA6D8", "周三": "#8B5FD3",
        "周四": "#D75F96", "周五": "#E07A3F", "周六": "#37A37A", "周日": "#73819E",
    }
    color = day_colors.get(c.get("weekday"), "#4D68D8")
    week_text = (
        f"{c.get('start_week', 1)}–{c.get('end_week', TOTAL_WEEKS)} 周"
        if c.get("week_type", "每周") == "每周"
        else f"{c.get('start_week', 1)}–{c.get('end_week', TOTAL_WEEKS)} 周 · {c.get('week_type')}"
    )
    day_html = f'<div class="crow-day">{c.get("weekday", "")}</div>' if show_day else ""
    return f"""
    <div class="course-row">
        <div class="course-clock"><strong>{start}</strong>{end}</div>
        <div class="course-line" style="background:{color}"></div>
        <div>
            <div class="crow-name">
                <span style="display:inline-block;width:7px;height:7px;border-radius:50%;
                             background:{color};margin-right:8px;vertical-align:middle;"></span>{c.get('name', '')}
            </div>
            <div class="crow-meta">{c.get('location', '地点待定')}　·　第 {c.get('periods', '?')} 节　·　{week_text}</div>
        </div>
        {day_html}
    </div>
    """


def _notification_card(n) -> str:
    tag_class = "tag-red" if n["level"] == "紧急" else "tag-yellow"
    deadline_html = f'<div class="notif-deadline">🗓️ 截止：{n["deadline"]}</div>' if n.get("deadline") else ""
    return f"""
    <div class="notif-card">
        <div class="notif-top">
            <span class="status-tag {tag_class}">{n['emoji']} {n['level']}</span>
            <span class="notif-title">{n['title']}</span>
        </div>
        <div class="notif-summary">{n['summary']}</div>
        {deadline_html}
        <a class="notif-link" href="{n['link']}" target="_blank">查看原文 →</a>
    </div>
    """


def _link_card(l) -> str:
    return f"""
    <a class="link-card" href="{l['url']}" target="_blank">
        <div class="link-name">{l['name']}</div>
        <div class="link-desc">{l['desc']}</div>
    </a>
    """


# ============================ 页面渲染 ============================
def render_today_overview(uploaded_file, qwen_key: str, view_mode: str = "today"):
    # ---- 课表截图导入流程（功能1） ----
    if uploaded_file is not None:
        st.markdown('<div class="section-title">课表截图导入</div>', unsafe_allow_html=True)
        c_img, c_act = st.columns([1, 2])
        with c_img:
            st.image(uploaded_file, width=240)
        with c_act:
            st.caption(f"已上传：{uploaded_file.name}")
            if st.button("🔍 解析课表截图", type="primary"):
                if not qwen_key:
                    st.warning("请先在侧边栏「🔑 API 配置」里填写千问 API Key")
                else:
                    with st.spinner("正在调用视觉模型识别课表…"):
                        try:
                            st.session_state["parsed_courses"] = parse_schedule_image(
                                uploaded_file.getvalue(), uploaded_file.type, qwen_key
                            )
                        except Exception as e:
                            st.error(f"课表识别失败，请检查千问 API Key: {e}")

        if st.session_state.get("parsed_courses"):
            st.markdown("**识别结果（可直接点击单元格编辑，确认后导入）：**")
            editor_rows = [
                {
                    "课程名": course.get("name", ""),
                    "星期": course.get("weekday", ""),
                    "上课时间": course.get("time", ""),
                    "地点": course.get("location", ""),
                    "节次": course.get("periods", ""),
                    "起始周": course.get("start_week", 1),
                    "结束周": course.get("end_week", TOTAL_WEEKS),
                    "周次类型": course.get("week_type", "每周"),
                }
                for course in st.session_state["parsed_courses"]
            ]
            df = pd.DataFrame(editor_rows)
            edited = st.data_editor(
                df,
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "星期": st.column_config.SelectboxColumn(
                        "星期", options=WEEKDAYS_CN, required=True
                    ),
                    "起始周": st.column_config.NumberColumn(
                        "起始周", min_value=1, max_value=TOTAL_WEEKS, step=1
                    ),
                    "结束周": st.column_config.NumberColumn(
                        "结束周", min_value=1, max_value=TOTAL_WEEKS, step=1
                    ),
                    "周次类型": st.column_config.SelectboxColumn(
                        "周次类型", options=["每周", "单周", "双周"], required=True
                    ),
                },
            )
            b1, b2, _ = st.columns([1, 1, 4])
            with b1:
                if st.button("✅ 确认导入"):
                    st.session_state["courses"] = [
                        _normalize_course(r)
                        for r in edited.to_dict("records")
                        if _clean(r.get("课程名"))
                    ]
                    st.session_state.pop("parsed_courses", None)
                    st.session_state.pop("schedule_uploader", None)
                    st.rerun()
            with b2:
                if st.button("🗑 放弃"):
                    st.session_state.pop("parsed_courses", None)
                    st.session_state.pop("schedule_uploader", None)
                    st.rerun()
        st.divider()

    today = date.today()
    week, weekday = get_week_info(today)

    all_courses = st.session_state["courses"]
    default_week = week or 1

    if view_mode == "today":
        selected_week = default_week
        courses = _courses_for_week(all_courses, selected_week)
        courses = [course for course in courses if course.get("weekday") == weekday]
        panel_title = f"今日课程 · {weekday}"
        source_note = "今日无课" if not courses else f"{len(courses)} 项安排"
    else:
        st.session_state.setdefault("selected_week", default_week)
        selected_week = int(st.session_state["selected_week"])
        if selected_week not in CALENDAR:
            selected_week = default_week
            st.session_state["selected_week"] = selected_week
        courses = _courses_for_week(all_courses, selected_week)
        panel_title = f"第 {selected_week} 周课程"
        source_note = "AI 解析导入" if all_courses != COURSES else "默认示例课表"

    _render_dashboard_header(today, week, weekday, selected_week)

    if courses:
        course_rows = "".join(
            _course_card(course, show_day=view_mode != "today") for course in courses
        )
    else:
        empty_title = "今天没有课程" if view_mode == "today" else "这一周没有课程"
        empty_copy = (
            "可以在“课程与课表”中查看整周安排"
            if view_mode == "today"
            else "切换左侧其他教学周查看安排"
        )
        course_rows = f"""
            <div class="empty-card" style="margin-top:8px;">
                <div><div class="empty-icon">✓</div>
                <div class="empty-title">{empty_title}</div>
                <div class="empty-copy">{empty_copy}</div></div>
            </div>
        """

    if view_mode == "schedule":
        week_rail, course_main = st.columns([2, 8], gap="medium")
        with week_rail:
            st.markdown(
                '<div class="section-title" style="margin:6px 0 8px;">教学周</div>',
                unsafe_allow_html=True,
            )
            _render_week_picker(selected_week)
        with course_main:
            st.markdown(
                f"""
                <div class="panel">
                    <div class="panel-head">
                        <div class="panel-title">{panel_title}　<span class="panel-meta">{len(courses)}</span></div>
                        <div class="panel-meta">{source_note}</div>
                    </div>
                    {course_rows}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-head">
                    <div class="panel-title">{panel_title}　<span class="panel-meta">{len(courses)}</span></div>
                    <div class="panel-meta">{source_note}</div>
                </div>
                {course_rows}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_ai_briefing(qwen_key: str):
    today = date.today()
    week, weekday = get_week_info(today)
    st.markdown(
        f"""
        <div style="font-size:1.4rem; font-weight:700; margin-bottom:2px;">AI 行动简报</div>
        <div class="muted-note" style="margin-bottom:16px;">AI 结合校历过滤官网通知，第 {week if week else '-'} 周 · {weekday}</div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🔄 运行通知过滤引擎"):
        if not qwen_key:
            st.warning("请先在侧边栏「🔑 API 配置」里填写千问 API Key")
        else:
            with st.spinner("AI 正在阅读通知并过滤…"):
                try:
                    st.session_state["parsed_notices"] = filter_notices(MOCK_NOTICES, qwen_key)
                except Exception as e:
                    st.error(f"AI 处理失败，请检查千问 API Key: {e}")

    parsed = st.session_state.get("parsed_notices")
    if parsed is None:
        st.info("👆 点击上方按钮，让 AI 结合校历过滤官网通知")
        with st.expander("查看原始通知（模拟数据，共 {} 条）".format(len(MOCK_NOTICES))):
            for n in MOCK_NOTICES:
                st.markdown(f"**{n['title']}**　{n['text']}")
        return

    relevant = [p for p in parsed if p.get("relevant")]
    ignored = [p for p in parsed if not p.get("relevant")]
    by_id = {n["id"]: n for n in MOCK_NOTICES}

    st.markdown(
        f'<div class="muted-note" style="margin-bottom:12px;">'
        f'共过滤 {len(MOCK_NOTICES)} 条 → 相关 {len(relevant)} 条 · 忽略 {len(ignored)} 条</div>',
        unsafe_allow_html=True,
    )
    for p in relevant:
        st.markdown(_notification_card(_map_notice(p, by_id)), unsafe_allow_html=True)

    if ignored:
        with st.expander(f"已忽略 {len(ignored)} 条无关通知"):
            for p in ignored:
                title = by_id.get(p.get("id"), {}).get("title", "")
                st.markdown(f"- ~~{title}~~")


def render_links():
    st.markdown(
        '<div style="font-size:1.4rem; font-weight:700; margin-bottom:2px;">网站导航</div>'
        '<div class="muted-note" style="margin-bottom:16px;">常用校园服务入口</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2, gap="medium")
    for i, l in enumerate(LINKS):
        with cols[i % 2]:
            st.markdown(_link_card(l), unsafe_allow_html=True)


# ============================ 侧边栏 ============================
today = date.today()
current_week, current_weekday = get_week_info(today)
default_week = current_week or 1
st.session_state.setdefault("selected_week", default_week)
selected_week = int(st.session_state["selected_week"])
if selected_week not in CALENDAR:
    selected_week = default_week
    st.session_state["selected_week"] = selected_week

st.session_state.setdefault("nav_view", "today")
nav_view = st.session_state["nav_view"]

with st.sidebar:
    st.markdown(
        """
        <div class="dashboard-brand">
            <div class="brand-mark">学</div>
            <div><div class="brand-name">CAMPUS</div><div class="brand-sub">东南大学 · 校园中枢</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="nav_menu", gap="small"):
        for icon, label, view in [
            ("⌂", "今日", "today"),
            ("▤", "课程与课表", "schedule"),
            ("◇", "AI 行动简报", "ai"),
            ("◎", "网站导航", "links"),
            ("⚙", "设置与导入", "settings"),
        ]:
            st.button(
                f"{icon}　{label}",
                key=f"nav_{view}",
                type="primary" if nav_view == view else "secondary",
                use_container_width=True,
                on_click=_set_nav,
                args=(view,),
            )

    st.divider()
    with st.expander("🔑 API 配置与课表导入", expanded=False):
        qwen_input = st.text_input(
            "千问 API Key", type="password", key="qwen_key_input",
            help="阿里云百炼 DashScope 的 API Key，文本 + 视觉共用一个",
        )
        st.caption("也可通过环境变量或 .streamlit/secrets.toml 配置（键名 DASHSCOPE_API_KEY）")
        uploaded_file = st.file_uploader(
            "📤 上传课表截图", type=["png", "jpg", "jpeg", "webp"],
            key="schedule_uploader", help="上传后到「今日」页点击解析",
        )

    st.markdown(
        '<div class="sidebar-foot">本地预览</div>',
        unsafe_allow_html=True,
    )

qwen_key = _resolve_key(qwen_input, "DASHSCOPE_API_KEY")

# ============================ 主界面 ============================
if nav_view == "today":
    render_today_overview(uploaded_file, qwen_key, view_mode="today")
elif nav_view == "schedule":
    render_today_overview(uploaded_file, qwen_key, view_mode="schedule")
elif nav_view == "ai":
    render_ai_briefing(qwen_key)
elif nav_view == "links":
    render_links()
else:
    st.markdown(
        """
        <div class="panel">
            <div class="panel-head"><div class="panel-title">设置与导入</div><div class="panel-meta">本地数据</div></div>
            <div class="muted-note">
                API Key 与课表截图上传位于左侧折叠面板。密钥只保存在当前 Streamlit 会话中；
                也可以通过环境变量或 .streamlit/secrets.toml 配置。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
