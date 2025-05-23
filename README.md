# [更新日志](./UpdateLog.md)

# 说明

接口文档(完善中...)：[https://apifox.com/apidoc/shared-5ee9b9dd-7f2c-48aa-b0d6-3a81cff66329](https://apifox.com/apidoc/shared-5ee9b9dd-7f2c-48aa-b0d6-3a81cff66329)

所有的接口都是基于飞牛TV官方的接口，没有做其他的操作

原理只是用nginx做了转发，前端页面自己写，多了一套python写的获取弹幕的接口

弹幕获取接口是实时获取的，每次开始播放都会获取最新弹幕，如果上了多个平台，会把所有平台的弹幕都展示

~~弹幕获取基于飞牛TV刮削到的豆瓣链接，目前有一个已知问题，需要等飞牛官方修复~~(可以直接传递剧集名称和第几集、第几季，由程序自动匹配)

```
多季的电视每一季的豆瓣链接都是第一季
```


## 项目链接

前端：[https://github.com/thshu/fnos-tv-web/](https://github.com/thshu/fnos-tv-web/)

后端：[https://github.com/thshu/fnos-tv](https://github.com/thshu/fnos-tv)

麻烦各位大佬帮忙点点Star

# 效果展示

播放页面

![1744105546727.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104232783_9fc9df586fed3.png)

首页

![1744105570033.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104304591_30e6c8ae3b064.png)

剧集详情页

![1744105674705.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104343917_e6d9ec43949bd.png)

电影详情页

![1744105687079.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104396989_93588e238fef3.png)

# 部署教程

### 1、拉取镜像

打开飞牛官方docker，搜索镜像：fntv

![1744105700312.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104749942_af943697b22f9.png)

选择latest标签，点击确定等待拉取

![1744105715039.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104799300_1f167946e8c9b.png)

### 2、部署镜像

点击 本地镜像 找到刚才下载的fntv，点击运行按钮

![1744105741763.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104865562_bcbfd36108a6c.png)

容器名称、资源限制等按照自己的需求填写，建议勾选上开机自启动

![1744105759347.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104924287_9aba932a89bac.png)

左侧端口号选择没有被占用的即可

![1744105773116.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104948015_bbad954b337a8.png)

点击存储位置，选择映射的路径

![1747992702717.png](https://pic2.ziyuan.wang/user/2513002960/2025/05/1747992702717_66ca7c38aed3d.png)

点击环境变量，找到FNOS_URL，配置飞牛系统的地址，这个地址就是你进入飞牛桌面页面后的地址，有端口号需要加上端口号；
RUN_AND_UPDATE_WEB默认为false，如果你需要重启容器时更新前端可以设置为true

![1744105786589.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744104998201_d1e15f193fd57.png)

点击下一步、创建，等待启动即可

![1744105802599.png](https://pic2.ziyuan.wang/user/2513002960/2025/04/1744105085231_3dd04baf9a3ae.png)


# 注意
1. 在映射到本地的路径下有log文件夹、config.ini、data.db
2. log文件夹下保存的有项目的日志，如果发生错误可以带上log日志反馈(注意log日志内有飞牛的地址，记得脱敏)
3. config.ini内可以配置飞牛系统的账号密码，用于302播放时获取直连(当前仅支持alist)
4. data.db是数据库文件，跳过时长、剧集对应的平台地址、播放记录都在这个文件内(播放记录是准备后期启动计算跳过时长使用的)
# 访问方式

在电脑地址栏输入IP+端口号访问即可

注意！！登录的账号密码是飞牛影视的账号密码，不是飞牛系统的！！！！
