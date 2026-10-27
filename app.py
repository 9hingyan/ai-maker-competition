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
from datetime import date

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
    {"name": "高等数学 A（一）", "time": "08:00 - 09:40", "location": "教一 205", "tag": "周一 · 第 1-2 节"},
    {"name": "工科导论",       "time": "14:00 - 15:40", "location": "教三 402", "tag": "周三 · 第 6-7 节"},
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
- tag：节次/周次说明（如 周一·第1-2节）

严格只输出一个 JSON 数组，不要输出任何解释文字、不要用 markdown 代码块。示例：
[
  {"name": "高等数学A", "time": "08:00 - 09:40", "location": "教一 205", "tag": "周一·第1-2节"}
]
识别不到某项就填空字符串 ""。不要遗漏任何课程。"""

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
        --bg: #F7F7F5;
        --card: #FFFFFF;
        --text: #37352F;
        --muted: #787774;
        --border: #E9E9E7;
        --accent: #37352F;
        --red: #D93025;
        --red-bg: #FBECEC;
        --yellow: #9A6700;
        --yellow-bg: #FBF1D9;
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

    section[data-testid="stSidebar"] {
        background-color: #FBFBFA;
        border-right: 1px solid var(--border);
    }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1100px; }

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

    .week-list { display: flex; flex-direction: column; gap: 2px; }
    .week-row  { display: flex; justify-content: space-between; align-items: center; padding: 5px 8px; border-radius: 6px; font-size: 0.8rem; }
    .week-row.active { background: #ECECEA; }
    .week-row.active .week-num { font-weight: 700; }
    .week-date { color: var(--muted); font-size: 0.74rem; }

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

    .muted-note { color: var(--muted); font-size: 0.85rem; }
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

    courses = []
    for item in data:
        courses.append({
            "name": str(item.get("name", "") or "").strip(),
            "time": str(item.get("time", "") or "").strip(),
            "location": str(item.get("location", "") or "").strip(),
            "tag": str(item.get("tag", "") or "").strip(),
        })
    return courses


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


def _calendar_list(current_week) -> str:
    rows = []
    for week, (start, end) in CALENDAR.items():
        s, e = date.fromisoformat(start), date.fromisoformat(end)
        active = " active" if week == current_week else ""
        rows.append(
            f'<div class="week-row{active}">'
            f'<span class="week-num">第 {week} 周</span>'
            f'<span class="week-date">{s.month}/{s.day} - {e.month}/{e.day}</span>'
            f'</div>'
        )
    return '<div class="week-list">' + "".join(rows) + "</div>"


def _course_card(c) -> str:
    return f"""
    <div class="course-card">
        <div class="course-left">
            <div class="course-name">{c['name']}</div>
            <div class="course-meta">
                <span>🕐 {c['time']}</span>
                <span>📍 {c['location']}</span>
            </div>
        </div>
        <div class="course-tag">{c['tag']}</div>
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
def render_today_overview(uploaded_file, qwen_key: str):
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
            df = pd.DataFrame(st.session_state["parsed_courses"])
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            b1, b2, _ = st.columns([1, 1, 4])
            with b1:
                if st.button("✅ 确认导入"):
                    st.session_state["courses"] = [
                        {"name": _clean(r.get("name")), "time": _clean(r.get("time")),
                         "location": _clean(r.get("location")), "tag": _clean(r.get("tag"))}
                        for r in edited.to_dict("records")
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

    st.markdown(_countdown_card(today, week, weekday), unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 8], gap="medium")

    with col_left:
        st.markdown('<div class="section-title">校历时间推演</div>', unsafe_allow_html=True)
        progress = (week / TOTAL_WEEKS) if week else 0.0
        st.markdown(
            f"""
            <div style="font-size:0.85rem; color: var(--muted);">学期进度：{week if week else '-'} / {TOTAL_WEEKS} 周</div>
            <div class="progress-track"><div class="progress-fill" style="width:{int(progress * 100)}%"></div></div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(_calendar_list(week), unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-title">今日课表</div>', unsafe_allow_html=True)
        courses = st.session_state["courses"]
        for c in courses:
            st.markdown(_course_card(c), unsafe_allow_html=True)
        st.markdown(
            f'<div class="muted-note">💡 今日共 {len(courses)} 节课 · '
            f'{"来自 AI 解析导入" if courses != COURSES else "默认示例数据，可在左侧上传课表截图导入"}</div>',
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
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🎓 CAMPUS·东大</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">东南大学 · AI 校园中枢</div>', unsafe_allow_html=True)
    st.divider()

    with st.expander("🔑 API 配置", expanded=False):
        qwen_input = st.text_input(
            "千问 API Key", type="password", key="qwen_key_input",
            help="阿里云百炼 DashScope 的 API Key，文本 + 视觉共用一个",
        )
        st.caption("也可通过环境变量或 .streamlit/secrets.toml 配置（键名 DASHSCOPE_API_KEY）")

    st.divider()
    uploaded_file = st.file_uploader(
        "📤 上传课表截图", type=["png", "jpg", "jpeg", "webp"],
        key="schedule_uploader", help="上传后到「今日总览」页点击解析",
    )

    st.markdown('<div class="sidebar-foot">v0.3 · 千问 AI 解析</div>', unsafe_allow_html=True)

qwen_key = _resolve_key(qwen_input, "DASHSCOPE_API_KEY")

# ============================ 主界面：顶部 Tab 导航 ============================
tab_overview, tab_briefing, tab_links = st.tabs(["今日总览", "AI行动简报", "网站导航"])

with tab_overview:
    render_today_overview(uploaded_file, qwen_key)

with tab_briefing:
    render_ai_briefing(qwen_key)

with tab_links:
    render_links()
