# Docker 快速部署指南

## Linux/Mac/WSL/Git Bash

### 创建数据目录
```bash
mkdir -p ~/danmu-data
```

### 启动容器
```bash
docker run -d --name get-danmu -p 8080:80 -v ~/danmu-data:/app/data -e FNOS_URL=http://localhost:5666 --restart=unless-stopped songnidedubai/getdanmu:latest
```

## Windows CMD

### 创建数据目录
```cmd
mkdir %USERPROFILE%\danmu-data
```

### 启动容器
```cmd
docker run -d --name get-danmu -p 8080:80 -v %USERPROFILE%\danmu-data:/app/data -e FNOS_URL=http://localhost:5666 --restart=unless-stopped songnidedubai/getdanmu:latest
```

## Windows PowerShell

### 创建数据目录
```powershell
mkdir -Force $HOME\danmu-data
```

### 启动容器
```powershell
docker run -d --name get-danmu -p 8080:80 -v ${HOME}/danmu-data:/app/data -e FNOS_URL=http://localhost:5666 --restart=unless-stopped songnidedubai/getdanmu:latest
```

部署完成后，访问 `http://localhost:8080` 即可使用应用。

# 弹幕功能使用指南

## 1. 获取XML格式弹幕

通过以下API获取XML格式的弹幕数据：

```
GET /danmu/get?type=xml&url=
```

## 2. 下载XML文件到本地弹幕

获取可下载的XML格式弹幕：

```
GET /danmu/download?url=
```

## 3. 获取uz格式弹幕

此接口返回特定格式的JSON弹幕数据，用于uz：

```
GET /danmu/get_uz?url=
```

### 返回格式：
```json
{
  "code": 23,
  "name": "名字",
  "danum": 弹幕总数,
  "danmuku": [
    [时间(秒), "left", 颜色, "字体大小", "弹幕内容"],
    ...
  ]
}
```

# 免责声明

本项目为个人学习研究创作，仅限用于学习和技术研究目的。使用本项目所产生的一切法律责任由使用者自行承担，与开发者无关。

1. 本项目不存储、不提供任何内容，所有内容均需用户自行提供获取
2. 本项目不对任何数据的准确性、完整性、及时性做保证
3. 本项目不对使用者因使用本工具而导致的任何直接或间接损失负责
4. 使用本项目即表示您同意遵守相关法律法规，并尊重数据版权

# 侵权联系

如本项目涉及侵犯您的权益，请联系我，我将在收到通知后立即处理：

我尊重知识产权，将积极配合权利人依法保护其合法权益。