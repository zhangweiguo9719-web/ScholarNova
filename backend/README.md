# ScholarNova Backend

ScholarNova 学术智能体后端服务。完整安装、API Key 和部署说明见仓库根目录 `README.md`。

## 快速开始

```bash
pip install -e .
cp .env.example .env
uvicorn app.main:app --reload
```

## 运行测试

```bash
pytest
```
