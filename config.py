# coding: utf-8
import os
from api import safeName

def getSongFileName(songInfo): # 在这里修改歌曲文件名的格式
    return safeName(songInfo["name"] + "-" + songInfo["artist"])

basePath = os.getcwd() # 下载目录