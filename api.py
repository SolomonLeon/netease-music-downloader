# coding: utf-8
import requests, random, json, threading, os

with open("user_agent_export.json", "r") as f:
    UAlist = json.loads(f.read())["UserAgents"]

def getRandomUA():
    return random.choice(UAlist)["ua_string"]

def safeName(filename): # 欢迎提供更好的方法XD
    return filename.replace("/","").replace("\\","").replace(":","").replace("*","").replace("?","").replace("\"","").replace("<","").replace(">","").replace("|","") # 格式化为合法字符串

def getPlaylist(_id): # 可支持一千首以上的歌单
    url = "https://api.mtnhao.com/playlist/detail?id={}".format(_id)
    headers = {'user-agent': getRandomUA()}
    response = requests.request("GET", url, headers=headers).json()
    return response

def getSongsDetial(idsStr): # 一次最多可以获取201首歌曲的信息
    url = "http://music.163.com/api/song/detail?ids={}".format(idsStr)
    headers = {'user-agent': getRandomUA()}
    response = requests.request("GET", url, headers=headers).json()
    return response

def getSongFileUrl(songInfo, br=9999999):
    """
    参数：
        songInfo：歌曲信息
        br：歌曲比特率（bps)，可选，默认最高
    返回：
        失败：False
        成功：{"url": 歌曲文件url, "bps": 比特率, "type":歌曲文件类型}
    拓展：
        思路：根据歌曲名在其他网站上查找高音质文件。
        可以参考 github.com/YongHaoWu/NeteaseCloudMusicFlac
        我就懒得写了，欢迎提交PR来完善此功能
    """
    nid = songInfo["nid"]
    def fromEnhance(): # 最好的API，可以获得高bps的flac，后缀名会随着bps的增加而改变
        headers = {'user-agent': getRandomUA()}
        url = "http://music.163.com/api/song/enhance/download/url?id={}&br={}".format(nid, br)
        response = requests.request("GET", url, headers=headers).json()
        if response["data"]["url"] == None:
            return False
        else:
            return {"url":response["data"]["url"], "bps":response["data"]["br"], "type":response["data"]["type"]}

    def fromMedia():# 范围最广的API，返回128kbs的mp3，一般来说只要在线能播放的，它就能获取播放地址
        headers = {'user-agent': getRandomUA()}
        url = "https://music.163.com/song/media/outer/url?id={}.mp3".format(nid)
        response = requests.request("GET", url, headers=headers)
        if "music.163.com/404" in response.url:
            return False
        else:
            return {"url":response.url, "bps":128000, "type":"mp3"}
    
    # 注册获取方法
    urlMethod = [
        fromEnhance,
        fromMedia,
    ]

    songUrlDict = None
    for func in urlMethod: # 按照列表顺序执行方法，直到成功获取url
        response = func()
        if response:
            songUrlDict = response
            break
    if songUrlDict:
        return songUrlDict
    else:
        return False