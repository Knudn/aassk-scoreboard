from sqlalchemy import Column, Integer, String, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

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
    status = Column(Integer)
    

    def __repr__(self):
        return f"<RaceData(id={self.id}, event_title='{self.event_title}', driver_name='{self.driver_name}')>"
    
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

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
        return f"<RealTimeData(id={self.id}, event_title='{self.race_title}', driver_name='{self.driver_name}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'cid': self.cid,
            'race_title': self.race_title,
            'heat': self.heat,
            'mode': self.mode,
            'driver_name': self.driver_name,
            'driver_club': self.driver_club,
            'status': self.status,
            'finishtime': self.finishtime,
            'inter_1': self.inter_1,
            'inter_2': self.inter_2,
            'penalty': self.penalty,
            'speed': self.speed,
            'vehicle': self.vehicle
        }
    
class RealTimeKvaliData(Base):
    __tablename__ = 'real_time_kvali_data'
    id = Column(Integer, primary_key=True)
    kvali_num = Column(Integer)
    race_title = Column(String)
    
    def __repr__(self):
        return f"<RealTimeKvaliData(id={self.id}, kvali_num='{self.kvali_num}', race_title='{self.race_title}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'kvali_num': self.kvali_num,
            'race_title': self.race_title
        }

class RealTimeState(Base):
    __tablename__ = 'real_time_state'
    id = Column(Integer, primary_key=True)
    active_driver_1 = Column(Integer)
    active_driver_2 = Column(Integer)
    active_race = Column(String)
    active_heat = Column(Integer)
    active_mode = Column(Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'active_driver_1': self.active_driver_1,
            'active_driver_2': self.active_driver_2,
            'active_race': self.active_race,
            'active_heat': self.active_heat,
            'active_mode': self.active_mode
        }