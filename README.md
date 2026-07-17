# 浙江省高考录取预测系统

基于 Flask 的浙江省普通类平行投档录取预测网站。系统提供快速预测、精准预测、手机号验证码登录、成绩位次防呆校验等功能。

## 本地运行

```powershell
pip install -r requirements.txt
python app.py
```

访问：

```text
http://127.0.0.1:5000/
```

默认短信模式为 `console`，验证码会打印在 Flask 控制台。

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

必须配置的环境变量：

```text
SECRET_KEY=请换成一串足够长的随机字符串
SMS_PROVIDER=console
```

如果使用阿里云短信：

```text
SMS_PROVIDER=aliyun
ALIYUN_SMS_SIGN_NAME=速通互联验证服务
ALIYUN_SMS_TEMPLATE_CODE=100001
ALIYUN_SMS_TEMPLATE_PARAM={"code":"##code##"}
ALIBABA_CLOUD_ACCESS_KEY_ID=你的 AccessKey ID
ALIBABA_CLOUD_ACCESS_KEY_SECRET=你的 AccessKey Secret
```

请不要把 AccessKey 写进代码或提交到 GitHub。
