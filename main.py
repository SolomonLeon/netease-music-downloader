# coding: utf-8
import threading, os, hashlib, random, json, time, argparse
from urllib.parse import quote

import requests

from model import Session
from model import song as songDB
from model import album as albumDB
from model import playlist as playlistDB
from model import downloadLog as downloadLogDB
from api import getPlaylist, getSongsDetial, getSongFileUrl
from method import downloader, saveLog, addInfoToMp3, addInfoToFlac, flacToM4a, makeXmlPlaylist
import config

def addPlaylist(playlistNid, name=None):
    """
    参数：
        playlistNid：歌单id，必填, 为int
        name：歌单名字，可选，默认自动获取
    """
    session = Session() #线程不安全，所以采用同步。

    playlistResq = getPlaylist(playlistNid)
    songsList = playlistResq["playlist"]["trackIds"]
    if name:
        playlistName = str(name)
    else:
        playlistName = playlistResq["playlist"]["name"]
    print("-"*10, "Add playlist", "-"*10)
    print("[*] Playlist name:", playlistName)

    checkPlaylistName = session.query(playlistDB).filter(playlistDB.name == playlistName) # 防止重名
    if not checkPlaylistName.count():
        session.add(playlistDB(name=playlistName, nid=playlistNid))
        session.commit()
    elif name != None:
        playlistInfo = checkPlaylistName.first().to_dict()
        if playlistInfo["nid"] != playlistNid:
            print("[!] Conflict: A playlist which nid is {} has the same name as the playlist you want to add.".format(playlistInfo["nid"]))
            print("              You should choise a different name for your playlist. (This has been added to our ToDo list.)")
            print("") # 好看
            return False

    print("[*] Length:", len(songsList))

    idList = [i["id"] for i in songsList]

    record = addNewSongs(playlistName, idList)

    print("[*] Total {} songs, {} new songs added, {} songs modified.".format(
        len(idList), record["add"], record["modify"]))

    if len(record["downloadErrors"]) != 0:
        saveLog("albumCoverErrors",json.dumps(record["downloadErrors"]))
    print("") # 好看

def addNewSongs(playlistName, idList): # 需要传入id列表
    session = Session()

    albumCoverPath = os.path.join(config.basePath,"images","album") # 保存专辑封面的文件夹
    if not os.path.exists(albumCoverPath):
        os.makedirs(albumCoverPath)
    albumImgDownloader = downloader(albumCoverPath, config.maxThread)

    offset = 0
    limit = 200 # 一次获取200首歌曲的信息，原因请看getSongsDetial的注释。
    requestTimes = len(idList) // limit + 1
    requestTime = 1

    record = {} # 记录
    record["add"] = 0
    record["modify"] = 0

    print(" |  Number of requests:", requestTimes) # 请求次数
    while offset < len(idList):
        print(" |  ", requestTime, "/", requestTimes)
        songsDetial = getSongsDetial(str(idList[offset:offset+limit])) # 分片获取歌曲信息

        for i in songsDetial["songs"]:
            name = i["name"]
            artist = ""
            for artistDict in i["artists"]:
                if artist != "":
                    artist += "; "
                artist += artistDict["name"]
            nid = i["id"]
            album = i["album"]["name"]
            albumArtists = ""
            for artistDict in i["album"]["artists"]:
                albumArtists += artistDict["name"] + "; "

            albumImgSrc = i["album"]["picUrl"]
            albumNid = i["album"]["id"]

            checkAlbum = session.query(albumDB).filter(albumDB.nid == albumNid) #查重
            if not checkAlbum.count():
                session.add(albumDB(name=album, artist=albumArtists, imgSrc=albumImgSrc, nid=albumNid))
                
            md5 = hashlib.md5() # 防止碰到文件名一样的图片
            md5.update(albumImgSrc.encode("utf-8"))
            albumImgSrcHex = md5.hexdigest()
            filename = albumImgSrcHex+".jpg"
            if not os.path.exists(os.path.join(albumCoverPath, filename)):
                albumImgDownloader.start(albumImgSrc+"?param={size}y{size}".format(size=config.coverSize), filename)

            checkSong = session.query(songDB).filter(songDB.nid == nid)
            if not checkSong.count():
                songPlaylists = ""
                songPlaylists += playlistName
                session.add(songDB(name=name, artist=artist, album=album, playlist=songPlaylists, nid=nid))
                record["add"] += 1
            else:
                songInfo = checkSong.first()
                songPlaylists = songInfo.playlist
                if playlistName not in songPlaylists:
                    if songPlaylists != "": # 存在播放列表
                        songPlaylists += "; "
                    songPlaylists += playlistName
                    songInfo.playlist = songPlaylists
                    record["modify"] += 1

        offset += limit
        requestTime += 1
        session.commit()
        time.sleep(random.uniform(1,5))
    albumImgDownloader.wait()
    record["downloadErrors"] = albumImgDownloader.getErrors()
    return record

def removePlaylistByName(playlistName): # 删除指定名字的播放列表
    session = Session()
    playlist = session.query(songDB).filter(songDB.playlist.contains(playlistName)).all()
    print("-"*10, "Remove playlist", "-"*10)
    print("[*] Playlist name:", playlistName)
    print("[*] Length of playlist:", len(playlist))

    playlistInfo = session.query(playlistDB).filter(playlistDB.name == playlistName).delete()
    session.commit()

    if not playlist:
        print("[*] Nothing to do.")
        print("") # 好看
        return
    removePlaylistInSongDB(playlistName, playlist)
    print("[*] Done.")
    print("") # 好看

def removePlaylistInSongDB(playlistName, dataList): # 从歌曲信息中移除播放列表；需要传入数据库条目dataList，区别于addNewSongs
    session = Session()
    for song in dataList:
        songPlaylist = song.playlist.split("; ")
        songPlaylist.remove(playlistName)
        newPlaylist = ""
        if len(songPlaylist) != 0:
            for i in songPlaylist:
                if newPlaylist != "":
                    newPlaylist += "; "
                newPlaylist += i
        song.playlist = newPlaylist
    session.commit()
def downloadAllSongs(transcode=True):
    print("-"*10, "Download all songs", "-"*10)
    if not transcode:
        print("[!] No transcode.")
    session = Session()

    songList = session.query(songDB).all()
    print("[*] Number of songs:",len(songList))

    downloadPath = os.path.join(config.basePath,"songs")
    if not os.path.exists(downloadPath):
        os.makedirs(downloadPath)
    songDownloader = downloader(downloadPath, config.maxThread)
    fileList = os.listdir(downloadPath)

    failedListRaw = session.query(downloadLogDB).filter(downloadLogDB.status == 0).all() # url获取失败的条目
    failedList = []
    for i in failedListRaw:
        failedList.append(i.nid)

    record = 1
    downloaded = 0
    failList = []
    songsDict = {}

    for songInfoRaw in songList:
        songInfo = songInfoRaw.to_dict()
        if songInfo["nid"] not in failedList:
            urlDict = getSongFileUrl(songInfo=songInfo)
            if urlDict:
                print(" |  ", record,"/",len(songList))
                filename = config.getSongFileName(songInfo) + "." + urlDict["type"]
                if filename not in fileList:
                    songDownloader.start(urlDict["url"], filename)
                    downloaded += 1
                    songsDict[songInfo["nid"]] = [filename, urlDict["type"]]
            else:
                failList.append(songInfo["nid"])
                print(" !  ",record, "/", len(songList), songInfo["name"],"failed.")
                session.add(downloadLogDB(nid=songInfo["nid"], name=songInfo["name"], status=0))
        else:
            print(" !  ",record, "/", len(songList), songInfo["name"],"skipped.")
        record += 1

    songDownloader.wait()
    session.commit()

    print("[*] Adding information to songs.")
    addInfoToSongs(songsDict, transcode) # 给音频文件添加信息，顺便转码

    if len(failList) != 0:
        print("[*] Failed to get url:", failList)
        print("    All failed songs have been added to database.")
    if len(songDownloader.getErrors()) != 0:
        saveLog("downloadErrors",json.dumps(songDownloader.getErrors()))
    print("[*] Done.")
    print("") # 好看
          

def addInfoToSongs(fileDict, isflacTranscode):# {123233:"123-12323.mp3"}
    session = Session()
    imgPath = os.path.join(config.basePath,"images","album")
    audioBasePath = os.path.join(config.basePath,"songs")
    flacTranscodeError = []

    threadLoop = []
    sem = threading.Semaphore(20)

    for nid in fileDict: # fileDict[nid][0]: 文件名字；fileDict[nid][1]: 文件类型
        songInfo = session.query(songDB).filter(songDB.nid == nid).first().to_dict()
        albumInfo = session.query(albumDB).filter(albumDB.name == songInfo["album"]).first().to_dict()
        md5 = hashlib.md5()
        md5.update(albumInfo["imgSrc"].encode("utf-8"))
        albumImgSrcHex = md5.hexdigest()
        filename = albumImgSrcHex+".jpg"

        songInfo["imgPath"] = os.path.join(imgPath, filename)
        songInfo["audioBasePath"] = audioBasePath
        if fileDict[nid][1] == "mp3":
            with sem:
                t = threading.Thread(target=addInfoToMp3,args=(fileDict[nid][0], songInfo, ))
                t.start()
                threadLoop.append(t)
        elif fileDict[nid][1] == "flac":
            with sem:
                t = threading.Thread(target=addInfoToFlac,args=(fileDict[nid][0], songInfo, ))
                t.start()
                threadLoop.append(t)
            if isflacTranscode:
                with sem:
                    t = threading.Thread(target=flacToM4a,args=(fileDict[nid][0], audioBasePath, ))
                    t.start()
                    threadLoop.append(t)
        else:
            pass
    for t in threadLoop:
        t.join()
    del threadLoop
    # if len(flacTranscodeError) != 0: # 暂时不考虑转码错误
    #     saveLog("flacTranscodeError",json.dumps(flacTranscodeError))

def exportXmlPlaylistByName(playlistName): # 从名字导出播放列表
    session = Session()
    print("-"*10, "Export playlist to xml", "-"*10)

    playlist = session.query(songDB).filter(songDB.playlist.contains(playlistName)).all()
    if not playlist:
        print("[!] Can not find playlist:", playlistName)
        print("") # 好看
        return

    print("[*] Playlist name:", playlistName)
    exten = {} # 因为没有储存下载信息，所以通过此方法获取扩展名。如有更好方法请告知，thanks！
    for name in os.listdir(os.path.join(config.basePath,"songs")):
        if os.path.isfile(os.path.join(config.basePath,"songs",name)):
            exten[os.path.splitext(name)[0]] = os.path.splitext(name)[1]
    failedListRaw = session.query(downloadLogDB).filter(downloadLogDB.status == 0).all() # url获取失败的条目
    failedList = []
    for i in failedListRaw:
        failedList.append(i.nid)

    songsInfo = []
    for songInfoRaw in playlist:
        songInfo = songInfoRaw.to_dict()
        if songInfo["nid"] not in failedList:
            filename = quote(config.getSongFileName(songInfo) + exten[config.getSongFileName(songInfo)])
            filePath = "file://localhost/" + os.path.join(config.basePath,"songs",filename).replace("\\", "/") # iTunes文件路径格式
            songInfo["filePath"] = filePath
            songsInfo.append(songInfo)
        else:
            print(" !  Can not add",songInfo["name"],": No song file downloaded.")

    playlistInfo = session.query(playlistDB).filter(playlistDB.name == playlistName).first().to_dict()
    playlistFilename = os.path.join(config.basePath, playlistInfo["name"] + ".xml")
    makeXmlPlaylist(songsInfo, playlistInfo, playlistFilename)
    print("[*] iTunes xml playlist saved into:", playlistFilename)

    print("") # 好看

def updateAllPlaylist():
    print("-"*10, "Updating all playlists", "-"*10)
    session = Session()
    playlists = session.query(playlistDB).all()
    for playlist in playlists:
        print("[*] Playlist name:", playlist.name)

        songsList = getPlaylist(playlist.nid)["playlist"]["trackIds"]      
        idList = [i["id"] for i in songsList]

        DBsongsList = session.query(songDB.nid).filter(songDB.playlist.contains(playlist.name)).all()
        DBidList = [i[0] for i in DBsongsList]

        addIdList = list(set(idList)- set(DBidList))
        delIdList = list(set(DBidList) - set(idList))
        delDataList = session.query(songDB).filter(songDB.nid.in_(delIdList)).all()

        if addIdList:
            print(" |  Adding new songs...")
            record = addNewSongs(playlist.name, addIdList)
            print(" |  Total {} songs, {} new songs added, {} songs modified.".format(
                len(idList), record["add"], record["modify"]))
        if delIdList:
            print(" |  Removing deleted songs...")
            removePlaylistInSongDB(delDataList)
        if not addIdList or delIdList:
            print(" |  Nothing to do.")
    print("[*] All done.")

    print("") # 好看

def showAllPlaylist():
    session = Session()
    print("-"*10, "Show all playlists.", "-"*10)
    playlists = session.query(playlistDB).all()
    print("{}\t{}".format("名字", "网易云id"))
    for playlist in playlists:
        print("{}\t{}".format(playlist.name, playlist.nid))
    print("") # 好看

def showAllSongs():
    session = Session()
    print("-"*10, "Show all songs.", "-"*10)
    print("{}\t{}\t{}".format("序号", "名字", "艺人", "专辑", "播放列表", "网易云id"))
    for song in songs:
        print(song.to_dict())
        print("{}\t{}\t{}\t{}\t{}\t{}".format(song.id, song.name, song.artist, song.album, song.playlist, song.nid))
    print("") # 好看

if __name__ == "__main__":
    __version__ = "v1.0"
    __author__ = "LeonZou"
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
    ********************* Playlist downloader {} **********************
    [*] A tool for downloading playlists from 163 music, written by Leon.
    [*] 使用步骤：
        1、先添加歌单： -a 歌单id 歌单名（可不填）
        2、查看所有歌单： -p
        3、下载所有歌曲： -da
        4、移除歌单： -rn 歌单名
        更多参数请看下面。
    *********************************************************************
    """.format(__version__),
        epilog="""\
    *********************************************************************
    [1] 所有参数可共存。
    [2] 有问题或建议欢迎提交issue。

    [*] 主页：github.com/SolomonLeon/netease-music-downloader
    [*] Enjoy YOUR netease music~
    *********************************************************************
    """,
        )
    parser.add_argument('-a', '--addPlaylist', nargs="+", help="添加播放列表：第一个参数是必选参数，为播放列表id，自动查重；第二个参数是可选参数，以自定义播放列表的名字。") # 默认返回None，所以不加default="False"
    parser.add_argument('-s', "--songs", action="store_true", help='列出所有歌曲')
    parser.add_argument('-p', "--playlists", action="store_true", help='列出所有的播放列表。')
    parser.add_argument('-da', "--downloadAllSongs", action="store_true", help='下载所有的歌曲。')
    parser.add_argument("--noTranscode", action="store_true", help='flac不自动转为m4a')
    parser.add_argument('-u','--update', action="store_true", help="同步所有的播放列表。注意事项见项目主页。")
    parser.add_argument('-rn', "--removePlaylistByName", nargs=1, help='通过名字移除播放列表。注意：若已自定义名字，请填写自定义后的名字。')
    parser.add_argument('-en', "--exportXmlPlaylistByName", nargs=1, help='通过名字导出iTunes的xml播放列表。注意：若已自定义名字，请填写自定义后的名字。')


    args = parser.parse_args()
    try:
        if args.addPlaylist:
            if len(args.addPlaylist) > 1:
                addPlaylist(args.addPlaylist[0],args.addPlaylist[1])
            else:
                addPlaylist(args.addPlaylist[0])
        if args.update:
            updateAllPlaylist()
        if args.removePlaylistByName:
            removePlaylistByName(args.removePlaylistByName[0])
        if args.playlists:
            showAllPlaylist()
        if args.songs:
            showAllSongs()
        if args.exportXmlPlaylistByName:
            exportXmlPlaylistByName(args.exportXmlPlaylistByName[0])
        if args.downloadAllSongs:
            if args.noTranscode:
                downloadAllSongs(False) # 不转码
            else:
                downloadAllSongs()
    except KeyboardInterrupt:
        print("[!] The main thread has stopped, waiting for the child thread to complete.")