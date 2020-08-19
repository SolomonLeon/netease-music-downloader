<div align=center><img src="https://s1.ax1x.com/2020/08/19/dQrkRS.png" alt="Logo" border="0" /></div>

# 网易云 音乐下载器

Download playlist and songs from netease muisc. 从网易云音乐上下载歌单和歌曲。



## 这是什么？

这是一个易于使用的工具，可以从网易云音乐上下载歌单和歌曲。

它可以做到：

- 一键添加播放列表

  ```bash
  main -a 播放列表id # 自动添加名字
  main -a 播放列表id 自定义名字 # 自定义名字
  ```

- 全自动更新播放列表

  ```bash
  main -u # 自动更新所有播放列表
  main -u -da # 你可以把这行命令添加到定时任务中，它会自动更新播放列表并下载新歌曲。
  ```
  
- 一键下载歌曲（有可能下载到高音质的flac文件，详见[这里](https://github.com/SolomonLeon/netease-music-downloader/blob/master/api.py#L25)），flac自动转码为m4a

  ```bash
  main -da
  ```

- 自动添加音频文件的歌曲信息

  ![自动添加文件信息](https://s1.ax1x.com/2020/08/18/dMR5dJ.md.png)

- 一键导出为iTunes的xml播放列表

  ```bash
  main -en 播放列表名字
  ```

- 简单地删除已储存的播放列表

  ```bash
  mian -rn 播放列表名字
  ```
  

**更多功能，请移步至[这里](#参数及配置文件解释)。**

***

此外，它还易于扩展，详情请移步至[这里](#添加新的解析方法)，欢迎提交PR。

代码已包含注释。



## 开始使用

#### 你可以下载已打包好的程序。

点击前往“[发布页面](https://github.com/SolomonLeon/netease-music-downloader/releases/latest)”

开发者手头上暂时没有mbp和Linux设备。如果你愿意帮忙打包，请联系本人。

下载并解压后，使用以下命令查看帮助。

```bash
main -h
```



## 获取源码

#### 直接下载zip源码：

[点击此处下载zip压缩文件](https://github.com/SolomonLeon/netease-music-downloader/archive/master.zip)

#### 使用git克隆：

```bash
git clone https://github.com/SolomonLeon/netease-music-downloader.git
```
#### 安装依赖：

```bash
pip install -r requirements.txt
```



## 参数及配置文件解释

### 参数

```bash
-a / --addPlaylist id name:
	添加播放列表：
		第一个参数是必选参数，为播放列表id，自动查重；
		第二个参数是可选参数，以自定义播放列表的名字。
		
-s / --songs:
	列出所有歌曲
	
-p / --playlists:
	列出所有的播放列表。
	
-da / --downloadAllSongs:
	下载所有的歌曲。
	--noTranscode:
		flac不转为m4a
		
-u / --update:
	从网易云音乐同步所有的播放列表。
	注意，此选项会也会同步删除操作。若想增量更新，请使用 -a 参数。
	
-rn / --removePlaylistByName name:
	通过名字移除播放列表。注意：若已自定义名字，请填写自定义后的名字。已储存的名字可通过 -p 获取。
	
-en / --exportXmlPlaylistByName name:
	通过名字导出iTunes的xml播放列表。注意：若已自定义名字，请填写自定义后的名字。
```

### 配置文件

```ini
#down_path: 下载路径，"Current_dir" 为当前路径
#max_thread: 最大线程数
#songfile_name: 歌曲文件命名，提供标签：{name}、{artist}、{album}、{playlist}、{nid}
#cover_size: 歌曲封面的长宽

[config]
down_path = Current_dir
max_thread = 30
songfile_name = {name} - {artist}
cover_size = 450
```



## 开发及贡献
### 开发

所有数据储存在 `sqlite.db` 内，数据库模型请移步到[这里](https://github.com/SolomonLeon/netease-music-downloader/blob/master/model.py#L17)。

使用驼峰命名法，首字母小写。exp: `getSongsInfo`

记得添加注释。



### 贡献

**欢迎提交PR，我会把你的名字添加到“贡献者”栏目里。**

你可以：

- #### 添加新的解析方法

  请在[这个函数](https://github.com/SolomonLeon/netease-music-downloader/blob/master/api.py#L25)中添加解析方法，别忘了在这里[注册方法](https://github.com/SolomonLeon/netease-music-downloader/blob/master/api.py#L57)。

  欢迎你把新方法分享给大家。



- #### 修复漏洞、增加新功能



- #### 提供新的网易云API

  请在[这里](https://github.com/SolomonLeon/netease-music-downloader/labels/netease%20API)提交你发现的API。我会把你的名字添加到“贡献者”栏目里。



## 贡献者
