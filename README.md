# CAMPUS·东大

东南大学 AI 校园中枢（Web APP）。解决大一新生信息分散、不懂「第 X 周」黑话、课表难导的问题。

## 功能

- **今日总览**：校历时间推演（自动算第几周/周几）+ 今日课表
- **AI 行动简报**：DeepSeek 过滤官网通知，并结合校历把「第 X 周截止」换算成具体日期
- **网站导航**：常用校园服务入口
- **课表截图导入**：上传课表截图，智谱 GLM-4V 视觉解析，`st.data_editor` 核对后导入

## 技术栈

Python + Streamlit + OpenAI 兼容 API（DeepSeek 文本 / 智谱 GLM-4V 视觉）

## 运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

访问 http://localhost:8501

## 配置 API Key（三选一）

1. 启动后侧边栏「🔑 API 配置」直接填写
2. 环境变量：`DEEPSEEK_API_KEY` / `ZHIPU_API_KEY`
3. `.streamlit/secrets.toml`：

```toml
DEEPSEEK_API_KEY = "sk-..."
ZHIPU_API_KEY = "..."
```

> 视觉解析默认用智谱 GLM-4V（DeepSeek 官方 API 目前为文本模型）；换视觉模型改 `app.py` 顶部 `ZHIPU_BASE_URL` / `ZHIPU_VISION_MODEL` 两个常量。
