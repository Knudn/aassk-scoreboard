from sqlalchemy import Column, Integer, String, Date, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash

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

    def __repr__(self):
        return f"<RaceData(id={self.id}, event_title='{self.event_title}', driver_name='{self.driver_name}')>"

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
    active_driver_1 = Column(Integer)
    active_driver_2 = Column(Integer)
    active_race = Column(String)
    active_heat = Column(Integer)
    active_mode = Column(Integer)
    active_race_state = Column(Boolean, default=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}