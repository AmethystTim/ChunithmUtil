# CHUNITHM Utils

查歌、查谱、成绩查询与版本牌子进度。**仅支持群聊。**

## 成绩与牌子进度

| 指令 | 说明 |
| --- | --- |
| `chubind [服务器] [TOKEN]` | 绑定账号；再次绑定会覆盖原绑定。 |
| `chucopy [服务器]` | 同步对应服务器的成绩和 FC/AJ 状态。 |
| `upd [分数] [歌名/cid] [难度可选]` | 手动更新成绩；难度支持 exp、mas、ult，默认 mas。 |
| `chuconst [等级] [服务器可选]` | 查看已有成绩的等级分数表，等级支持 9、9+…15、15+。 |
| `chuprog [版本] [牌子可选] [服务器可选]` | 查看所选版本的 MASTER 牌子进度；未玩谱面计零分。 |
| `b30` / `b30 simple` | 默认返回 B30 图片；加 simple 返回文字分表。 |
| `chudrop` | 清除自己的全部游玩记录，保留账号绑定。 |

> 服务器只支持 **lx、rin、shiro**。省略查询服务器时，逐谱面取所有来源（含手动成绩和旧记录）中的**最高分**。

**示例：** `chuconst 15 rin` · `chuprog sun aj shiro` · `chuprog sun rin`

牌子参数：**s、sss、sss+、aj、ajc**，默认 sss（将牌）。FC/AJ 采用所选来源已达成的状态；旧记录和手动成绩没有确认标记时，不推测达成。巫牌需要对应来源的 AJ 标记和 1,010,000 分。

lx 的 TOKEN 是落雪个人 API 密钥；rin、shiro 的 TOKEN 是 20 位卡号。修改绑定直接重新执行 `chubind`。**unbind 已停用。**

## 查歌与查谱

| 指令 | 说明 |
| --- | --- |
| `[歌名/别名/cid]是什么歌` | 查找歌曲与谱面信息。 |
| `chu随机一曲` | 随机推荐一首歌。 |
| `chuset [歌曲cid] [别名1，别名2，…]` | 为歌曲添加别名。 |
| `别名 [歌曲cid]` | 查看歌曲的所有别名。 |
| `chu lv [定数]` | 查看指定定数或等级范围内的歌曲。 |
| `chuver [版本]` | 查看指定版本的歌曲列表。 |
| `chu容错 [歌名/cid] [难度可选]` | 查询谱面容错；支持 exp、mas、ult。 |
| `chuchart [歌名/cid] [难度可选]` | 查看普通谱面；支持 exp、mas、ult。 |
| `wechart [歌名/cid] [类别可选]` | 查看 WORLD'S END 谱面。 |
| `chu曲师 [曲师名]` | 查看曲师作品。 |
| `chu update` | 更新曲目和谱面信息。 |

## 猜歌游戏

| 指令 | 说明 |
| --- | --- |
| `chu guess [难度可选]` | 创建猜歌游戏；支持 bas、adv、exp、mas、ult。 |
| `guess [歌名]` | 提交猜测。 |
| `chu hint` | 请求提示。 |
| `chu guess end` / `cge` | 结束当前猜歌游戏。 |
| `chu guess range` | 查看本群猜歌定数范围。 |
| `chu guess range [最低]` | 设置最低定数，不限制上限。 |
| `chu guess range [最低] [最高]` | 设置定数上下限。 |
| `chu guess range clear` | 清除本群猜歌定数范围。 |

---

**查看帮助：** `chuhelp` · `chu help`

原 ChuProg 功能已合并到 ChunithmUtil；旧入口 `chuprg help` 会提示使用 `chuhelp`。
