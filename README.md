<h1 align="center">ChunithmUtil</h1>

<h4 align="center">集成了多项Chunithm实用功能的LangBot插件🧩</h4>

![ChunithmUtil](./images/icon.png)

## 特性✨

- ✅：已实现
- 🚧：开发中
- ❌：未实现

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
|谱师查询|获取指定谱师的所有曲目|✅|
|自动更新|自动获取新版本曲目信息|🚧|
|段位曲目|获取指定段位的曲目列表|❌|

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

插件安装完成后，需要获取歌曲**元数据**和谱面ID-歌曲的**映射表**，所有指令需要在`ChunithmUtil`插件目录下执行

```python
python utils/songmeta.py    # 获取歌曲元数据
python utils/mapping.py     # 获取谱面ID-歌曲的映射表
```

> 新版本更新后，重新运行指令以获取新曲数据

## 数据源

- 歌曲元数据：[data.json](https://dp4p6x0xfi5o9.cloudfront.net/chunithm/data.json)
- Chunithm谱面保管室：[https://sdvx.in](https://sdvx.in)

## 鸣谢

- 感谢[@Hitagisugoi](https://github.com/Hitagisugoi)提出的的谱师/曲师查询功能建议