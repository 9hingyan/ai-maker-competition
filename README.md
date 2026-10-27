# CAMPUS·东大

东南大学 AI 校园中枢（Web APP）。解决大一新生信息分散、不懂「第 X 周」黑话、课表难导的问题。

## 功能

- **今日总览**：校历时间推演（自动算第几周/周几）+ 今日课表 + SRTP 申报倒计时
- **AI 行动简报**：千问（Qwen）过滤官网通知，并结合校历把「第 X 周截止」换算成具体日期
- **网站导航**：常用校园服务入口
- **课表截图导入**：上传课表截图，Qwen-VL 视觉解析，`st.data_editor` 核对后导入

## 技术栈

Python + Streamlit + OpenAI 兼容 API（千问 Qwen 文本 `qwen-plus` / 视觉 `qwen-vl-plus`）

## 运行

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

访问 http://localhost:8501

## 配置 API Key（三选一）

千问（阿里云百炼 DashScope）的 API Key，文本 + 视觉共用一个：

1. 启动后侧边栏「🔑 API 配置」直接填写（访客各自填）
2. 环境变量：`DASHSCOPE_API_KEY`
3. `.streamlit/secrets.toml`：

```toml
DASHSCOPE_API_KEY = "sk-..."
```

> 想换成豆包（火山方舟 Ark）或 DeepSeek：改 `app.py` 顶部 `QWEN_BASE_URL` / `QWEN_TEXT_MODEL` / `QWEN_VISION_MODEL` 三个常量即可，其余代码不用动（都是 OpenAI 兼容接口）。

## 部署到云端（Streamlit Community Cloud）

1. 注册 GitHub，新建一个**公开**仓库，把 `app.py`、`requirements.txt`、`README.md` 推上去
2. 打开 https://share.streamlit.io 用 GitHub 登录 → **New app** → 选仓库和主文件 `app.py` → **Deploy**
3. 在应用设置 **Secrets** 里加一行：`DASHSCOPE_API_KEY = "sk-..."`（这样访客打开就不用自己填 Key）
4. 得到固定网址 `https://你的应用名.streamlit.app`
