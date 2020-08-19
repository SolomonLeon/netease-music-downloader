# coding: utf-8
import os
from api import safeName
import configparser

def getSongFileName(songInfo): # 在这里修改歌曲文件名的格式
    formattedStr = namestr.format(
        name=str(songInfo["name"]),
        artist=str(songInfo["artist"]),
        album=str(songInfo["album"]),
        playlist=str(songInfo["playlist"]),
        nid=str(songInfo["nid"])
    )
    return safeName(formattedStr)

# 读取配置
if not os.path.exists("config.ini"):
    cf = configparser.ConfigParser()
    cf.add_section("config")
    cf.set("config", "down_path", "Current_dir")
    cf.set("config", "max_thread", "30")
    cf.set("config", "songfile_name", "{name} - {artist}")
    with open("config.ini", "w", encoding="utf-8") as f:
        cf.write(f)
    del cf
cf = configparser.ConfigParser()
cf.read("config.ini", encoding="utf-8")

if cf.get("config", "down_path") == "Current_dir":
    basePath = os.getcwd()
else:
    basePath = cf.get("config", "down_path") # 自定义目录
maxThread = int(cf.get("config", "max_thread"))
namestr = cf.get("config", "songfile_name")