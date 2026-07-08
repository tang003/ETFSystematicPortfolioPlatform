# Backend

FastAPI 后端服务，负责 API、数据库访问、任务调度入口和后续投研模块编排。

## 本地开发

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

默认读取项目根目录或当前目录下的 `.env`。

