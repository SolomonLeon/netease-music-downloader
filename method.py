# coding: utf-8
import requests, threading, os, datetime, subprocess
import xml.dom.minidom

from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, PictureType

from api import safeName

def saveLog(name, content):
    filename = "log_" + str(name) + "_" + datetime.datetime.now().strftime("%y-%m-%d_%H-%M-%S") + ".json"
    print("[*] Log saved into:",filename)
    with open(filename,"w") as f:
        f.write(content)

class downloader():
    """
    参数：
        sem：最大线程数，可选，默认不设置
        basePath：文件下载位置
    使用方法：
        start：启动下载线程
            url：文件url
            filename：文件名
                return：无返回
        getErrors：返回失败列表
                return：[{"filename":文件名, "url":url}]
    """
    def __init__(self, basePath, sem=None):
        super(downloader, self).__init__()
        self.unsuccess = []
        if sem:
            self.sem = threading.Semaphore(sem)
        else:
            self.sem = None
        self.basePath = basePath
        self.threadLoop = []
        
    def start(self, url, filename):
        if self.sem:
            with self.sem:
                t = threading.Thread(target=self.download,args=(url,filename,))
                self.threadLoop.append(t)
                t.start()
        else:
            t = threading.Thread(target=self.download,args=(url,filename,))
            self.threadLoop.append(t)
            t.start()

    def download(self, url, filename):
        self.sem.acquire()
        try:
            # legal_Filename = "".join(x for x in filename if x.isalnum())
            legal_Filename = safeName(filename)
            fileContent = requests.get(url).content
            with open(os.path.join(self.basePath, legal_Filename), "wb") as f:
                f.write(fileContent)
        except Exception as e:
            self.unsuccess.append({"filename":legal_Filename, "url":url})
            print("[!] unsuccessful download ",filename,".")
        finally:
            self.sem.release()

    def getErrors(self):
        return self.unsuccess

    def wait(self):
        for t in self.threadLoop:
            t.join()
        self.threadLoop = []

def addInfoToMp3(filename, songInfo):
    filePath = os.path.join(songInfo["audioBasePath"],filename)
    audio = MP3(filePath, ID3=ID3)   

    with open(songInfo["imgPath"], "rb") as f:
        data = f.read() 
    audio["APIC"] = APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc=u'Cover',
            data=data
    )
    audio["TIT2"] = TIT2(
        encoding=3,
        text=songInfo["name"]
    )
    audio['TPE1'] = TPE1(
        encoding=3,
        text=songInfo['artist']
    )
    audio['TALB'] = TALB(
        encoding=3,
        text=songInfo['album']
    )
    audio.save()

def addInfoToFlac(filename, songInfo):
    filePath = os.path.join(songInfo["audioBasePath"],filename)
    audio = FLAC(filePath)   

    pic = Picture()
    with open(songInfo["imgPath"], "rb") as f:
        pic.data = f.read()
    pic.type = PictureType.COVER_FRONT
    pic.mime = u"image/jpeg"

    audio.add_picture(pic)
    audio["title"] = songInfo["name"]
    audio["artist"] = songInfo["artist"]
    audio["album"] = songInfo["album"]

    audio.save()

def flacToM4a(filename, basePath): # 转码后会删除源文件
    inputName = os.path.join(basePath, filename)
    outputName = os.path.join(basePath, os.path.splitext(filename)[0] + ".m4a")
    if not os.path.exists(outputName):
        ffmpegCmdList = [
            "ffmpeg",
            "-nostdin",
            "-i",
            inputName,
            "-c:a",
            "alac",
            "-c:v",
            "copy",
            outputName,
            "1>nul",
            "2>nul",
        ]
        r = subprocess.run(ffmpegCmdList, shell=True)
        if r.returncode > 0:
            return False
        else:
            os.remove(inputName)
            return True

def makeXmlPlaylist(songsInfo, playlistInfo, playlistFilename):
    def addKey(to, keycontent):
        tkey = doc.createElement("key")
        tkey.appendChild(doc.createTextNode(str(keycontent)))
        to.appendChild(tkey)
    def addTag(to, keycontent, type, content):
        addKey(to, keycontent)
        tcontent = doc.createElement(str(type))
        tcontent.appendChild(doc.createTextNode(str(content)))
        to.appendChild(tcontent)
    def addDict(to):
        tdict = doc.createElement("dict")
        to.appendChild(tdict)
        return tdict
    def addArray(to):
        tarray = doc.createElement("array")
        to.appendChild(tarray)
        tdict = addDict(tarray)
        return tdict

    doc = xml.dom.minidom.Document()
    plist = doc.createElement('plist')
    plist.setAttribute("version","1.0")
    doc.appendChild(plist)

    baseDict = addDict(plist)

    addKey(baseDict, "Tracks")
    trackDict = addDict(baseDict)
    count = 1
    for songInfo in songsInfo:
        addKey(trackDict, count)
        songDict = addDict(trackDict)
        addTag(songDict, "Track ID", "integer", count)
        addTag(songDict, "Name", "string", songInfo["name"])
        addTag(songDict, "Artist", "string", songInfo["artist"])
        addTag(songDict, "Album", "string", songInfo["album"])
        addTag(songDict, "Track Type", "string", "File")
        addTag(songDict, "Location", "string", songInfo["filePath"])
        count += 1

    addKey(baseDict, "Playlists")
    playlistInfoArray = addArray(baseDict)
    addTag(playlistInfoArray, "Name", "string", playlistInfo["name"])
    addTag(playlistInfoArray, "Description", "string", "")
    addKey(playlistInfoArray, "Playlist Items")
    playlistItems = doc.createElement("array")
    playlistInfoArray.appendChild(playlistItems)
    for tid in range(1,count):
        trackItemDict = addDict(playlistItems)
        addTag(trackItemDict, "Track ID", "integer", tid)

    with open(playlistFilename, "w", encoding='utf-8') as f:
        doc.writexml(f, indent='\t', addindent='\t', newl='\n', encoding="utf-8")