<h1 align="center">ChunithmUtil</h1>

<h4 align="center">集成了多项Chunithm实用功能的LangBot插件🧩</h4>

<div align="center">

<img src="./images/icon_border_radius.png" style="width:90%">

</div>

## 介绍🤔

《CHUNITHM》是一款由SEGA开发的街机音乐游戏。其主要玩法为配合音乐节奏，通过触碰键盘或抬手以进行相应操作。CHUNITHM于2015年7月16日在日本开始运营。游戏内置多首乐曲并配有不同难度的谱面供玩家游玩。

> 引自萌娘百科，阅读更多：[https://zh.moegirl.org.cn/CHUNITHM](https://zh.moegirl.org.cn/CHUNITHM)

本插件旨在降低游玩Chunithm的门槛，为玩家提供多项Chunithm相关的实用功能，以更好地提升自身游玩技术。

## 特性✨

- ✅：已实现
- 🚧：开发中

|功能|描述|实现|
|---|---|---|
|模糊搜索|根据别名匹配曲目|✅|
|精准搜索|根据cid匹配曲目|✅|
|添加别名|为曲目添加别名|✅|
|容错计算|计算曲目达成鸟/鸟加的容错|✅|
|谱面查询|获取曲目预览谱面|✅|
|随机歌曲|随机获取一首曲目|✅|
|定数列表|获取指定定数的所有曲目|✅|
|曲师查询|获取指定曲师的所有曲目|✅|
|猜歌游戏|根据截取曲绘猜测曲目|✅|
|B30查询|查询B30曲目列表|✅|
|段位曲目|获取指定段位的曲目列表|🚧|

## 插件安装🛠️

配置完成 [LangBot](https://github.com/RockChinQ/QChatGPT) 主程序后使用管理员账号向机器人发送命令即可安装：

```
!plugin get https://github.com/AmethystTim/ChunithmUtil.git
```
或查看详细的[插件安装说明](https://github.com/RockChinQ/QChatGPT/wiki/5-%E6%8F%92%E4%BB%B6%E4%BD%BF%E7%94%A8)

## 使用说明📖

### 网络配置

访问**消息平台**配置`HTTP`服务器

以`NapCat`为例，访问`127.0.0.1:6099`，配置信息如下：

<div align="center">

<img src="./images/napcat_config.png" style="width:60%">

</div>

### 获取数据

插件安装完成后，需要获取歌曲**元数据**和谱面ID-歌曲的**映射表**

- **方式1**（**推荐**）：在群聊中使用`chu update`指令获取数据

- 方式2：运行以下脚本以获取数据

```python
src/utils/songmeta.py    # 获取歌曲元数据
src/utils/mapping.py     # 获取谱面ID-歌曲的映射表
```

> `Chunithm`版本更新后，可再次运行以更新数据

## 指令🤖

> 其中`[]` 表示必选参数，`<>` 表示可选参数，`<>`中`:`右侧表示默认值

### 查歌部分

|指令|描述|参数|示例|
|---|---|---|---|
|[`别名`]是什么歌|模糊搜索歌曲|`别名`|特大是什么歌；<br>c1145是什么歌|
|chuset [`cid`] [`别名1,别名2,…`]|为曲目添加别名|`cid`, <br>`别名1, 别名2, …`|chuset c165 16bit；<br>chuset c165 16bit,16比特战争<br>chuset c165 16bit，16比特战争|
|别名[`cid/别名`]|查询歌曲别名|`cid/别名`|别名c165；<br>别名特大|
|chu lv [`定数`]|获取指定定数的所有曲目|`定数`|chu lv 14.5|

### 查谱部分

|指令|描述|参数|示例|
|---|---|---|---|
|chuchart [`cid/别名`] <`难度: mas`>|获取指定曲目谱面预览|`cid/别名`,<br> `难度`(可选exp/mas/ult)|chuchart 特大；<br>chuchart aleph-0 ult|
|wechart [`cid/别名`] <`类型`>|获取指定曲目谱面预览|`cid/别名`, <br>`类型`(可选`狂`、`招`……，不指定则返回该曲目所有类型WE谱)|wechart 特大 割；<br>wechart 神威 招；<br>wechart 这么可爱真是抱歉|

### 查分部分

|指令|描述|参数|示例|
|---|---|---|---|
|chubind [`服务器`] [`TOKEN`]|绑定服务器身份信息|`服务器`（可选`lx`，`rin`）<br> `TOKEN`（`lx`为[个人API](https://maimai.lxns.net/user/profile?tab=thirdparty)，`rin`为20位卡号）|chubind lx chunithm-114-CHUNITHMCHUNITHM_chunithm=；<br>chubind rin 11451419198106166160|
|chucopy [`服务器`]|从指定服务器迁移游玩记录|`服务器`（可选`lx`，`rin`）|chucopy lx；<br>chucopy rin|
|b30 <`分表类型: None`>|查询B30|`分表类型`（可选`simple`仅返回文本B30，不指定返回默认B30图表）|b30<br>b30 simple|

### 猜歌部分

|指令|描述|参数|示例|
|---|----|----|----|
|chuguess|开始猜歌游戏|-|-|
|chuhint|查看提示|-|-|
|guess [`cid/别名`]|提交答案|-|guess c114；<br>guess 特大|
|chuguess end|结束猜歌游戏|-|chuguess end；<br>chuguessend；<br>cge|

### 其他部分

|指令|描述|参数|示例|
|---|---|---|---|
|chu容错 [`cid/别名`] <`难度: mas`>|计算指定曲目达成鸟/鸟加的容错|`cid/别名`, <br>`难度`(可选exp/mas/ult)|churc 特大；<br>chu容错 yurushite|
|chu曲师 [`曲师名`]|获取指定曲师的所有曲目|`曲师名`|chu曲师 void；<br>chuqs void|
|chu update|更新曲目、谱面信息|-|chu update；<br>chuupdate|

## 数据源

- 歌曲元数据：[data.json](https://reiwa.f5.si/chunithm_record.json)
- Chunithm谱面保管室：[https://sdvx.in/chunithm.html](https://sdvx.in/chunithm.html)

## 致谢🙏

- 感谢[@Hitagisugoi](https://github.com/Hitagisugoi)提出的的谱师/曲师查询功能建议