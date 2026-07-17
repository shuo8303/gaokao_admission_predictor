# 浙江省高考录取预测系统

基于 Flask 的浙江省普通类平行投档录取预测网站。系统提供快速预测、精准预测、成绩位次防呆校验等功能。

## 本地运行

```powershell
pip install -r requirements.txt
python app.py
```

访问：

```text
http://127.0.0.1:5000/
```

## 数据文件

官方投档线数据放入：

```text
data/
```

分数位次校验表放入：

```text
data/score_rank/
```

## Render 部署

Render Web Service 配置：

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

可选环境变量：

```text
SECRET_KEY=请换成一串足够长的随机字符串
```
