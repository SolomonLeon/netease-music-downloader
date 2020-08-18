# coding: utf-8
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import Column, Integer, String, ForeignKey

from sqlalchemy.orm import scoped_session, sessionmaker, relationship

#连接数据库
engine = create_engine('sqlite:///sqlite.db')
Base = declarative_base()
def to_dict(self):
    return {c.name: getattr(self, c.name, None)
    for c in self.__table__.columns}
Base.to_dict = to_dict

class song(Base):
    __tablename__ = "songs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30))
    artist = Column(String(50))
    album = Column(String(30))
    playlist = Column(String) #列表
    nid = Column(Integer) # netease id

class album(Base):
    __tablename__ = "albums"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30))
    # songs = relationship("song", backref="nid", lazy='dynamic')
    artist = Column(String(100))
    imgSrc = Column(String(150)) # ?param=200y200 修改大小
    nid = Column(Integer) # netease id

class playlist(Base):
    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30))
    nid = Column(Integer) # todo：让这里的nid可储存多个，像"nid1; nid2; nid3"这样

class downloadLog(Base):
    __tablename__ = "download_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nid = Column(Integer, ForeignKey("songs.nid"))
    name = Column(String(30))
    status = Column(Integer) # 0: 找不到歌曲下载信息

Base.metadata.create_all(engine)

#线程安全的session
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)