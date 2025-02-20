from sqlalchemy import Column, Integer, String, Date, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from datetime import datetime



Base = declarative_base()

class RaceData(Base):
    __tablename__ = 'race_data'
    id = Column(Integer, primary_key=True)
    cid = Column(Integer)
    date = Column(Date)
    event_title = Column(String)
    race_title = Column(String)
    heat = Column(Integer)
    mode = Column(Integer)
    driver_name = Column(String)
    driver_club = Column(String)
    pair_id = Column(Integer)
    run = Column(Integer)
    status = Column(Integer)
    finishtime = Column(Float)
    inter_1 = Column(Float)
    inter_2 = Column(Float)
    penalty = Column(Float)
    speed = Column(Float)
    vehicle = Column(String)
    enabled = Column(Boolean, default=True)
    race_class = Column(String, default="None")


    def __repr__(self):
        return f"<RaceData(id={self.id}, event_title='{self.event_title}', driver_name='{self.driver_name}')>"
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class RaceClasses(Base):
    __tablename__ = 'race_classes'
    id = Column(Integer, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return f"<RealTimeData(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
class RealTimeData(Base):
    __tablename__ = 'real_time_data'
    id = Column(Integer, primary_key=True)
    cid = Column(Integer)
    race_title = Column(String)
    heat = Column(Integer)
    mode = Column(Integer)
    driver_name = Column(String)
    driver_club = Column(String)
    status = Column(Integer)
    finishtime = Column(Float)
    inter_1 = Column(Float)
    inter_2 = Column(Float)
    penalty = Column(Float)
    speed = Column(Float)
    vehicle = Column(String)
    
    def __repr__(self):
        return f"<RealTimeData(id={self.id}, race_title='{self.race_title}', driver_name='{self.driver_name}')>"
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class RealTimeKvaliData(Base):
    __tablename__ = 'real_time_kvali_data'
    id = Column(Integer, primary_key=True)
    kvali_num = Column(Integer)
    race_title = Column(String)
    
    def __repr__(self):
        return f"<RealTimeKvaliData(id={self.id}, kvali_num='{self.kvali_num}', race_title='{self.race_title}')>"
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class RealTimeState(Base):
    __tablename__ = 'real_time_state'
    id = Column(Integer, primary_key=True)
    active_driver_1 = Column(Integer, default=0)
    active_driver_2 = Column(Integer, default=0)
    active_event = Column(String, default="None")
    active_race = Column(String, default="None")
    active_heat = Column(Integer, default="None")
    active_mode = Column(Integer, default="None")
    active_race_state = Column(Integer, default=False)
    display_quali = Column(Boolean, default=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class live_event_liste(Base):
    __tablename__ = 'live_event_liste'
    id = Column(Integer, primary_key=True)
    event_navn = Column(String)
    heat = Column(Integer)
    mode = Column(Integer)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class PDFS(Base):
    __tablename__ = 'pdfs'
    
    id = Column(Integer, primary_key=True)
    file_name = Column(String(80), unique=True, nullable=False)
    file_title = Column(String(80), nullable=False)


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class ManualEntries(Base):
    __tablename__ = 'manual_entries'
    
    id = Column(Integer, primary_key=True)
    event_title = Column(String, unique=True)
    races = Column(JSON)
    event_date = Column(Date)

    def to_dict(self):
        races = self.races if self.races else []
        return {
            'id': self.id,
            'event_title': self.event_title,
            'races': races,
            'event_date': self.event_date.isoformat(),
            'race_title': races[0]['race_title'] if races else '',
            'mode': races[0]['mode'] if races else 1,
            'driver_places': races[0]['driver_places'] if races else [],
            'pdf_filename': races[0].get('pdf_filename') if races else None
        }