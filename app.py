from flask import Flask, render_template, request, jsonify, Response, current_app, redirect, session, url_for, flash
from sqlalchemy import create_engine, and_, text, func
from sqlalchemy.orm import sessionmaker, Session
from queries import *
from models import Base, RaceData
from utils.utils import fix_names, insert_into_database
#from flask_cors import CORS
from datetime import date
import jwt
from functools import wraps
from contextlib import contextmanager
from collections import defaultdict
from typing import Any, Dict, List, Union
from flask_socketio import SocketIO, emit, join_room


DATABASE_URL = "sqlite:///./site.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=20,
    max_overflow=0,
    pool_timeout=30
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = Flask(__name__)
#CORS(app)  # This applies CORS to all routes
app.config['SECRET_KEY'] = '123123'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
socketio = SocketIO(app)

use_auth = True

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


Base.metadata.create_all(bind=engine)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def is_user_logged_in():
    return 'user_id' in session

def reorder_heat_results(heat_data):
    items = list(heat_data.items())
    
    def sort_key(item):
        _, value = item
        pair_order = value['pair']
        time_order = value['finishtime'] if value['penalty'] == 0 else float('inf')
        return (pair_order, time_order)
    
    sorted_items = sorted(items, key=sort_key)
    
    return {str(i+1): value for i, (_, value) in enumerate(sorted_items)}

def process_table_data(table_data):
    
    for race_title in table_data:
        tmp_list = []
        for heat in table_data[race_title]:
            tmp_list.insert(0, reorder_heat_results(table_data[race_title][heat]))
        
        
        cid_list= []
        tmp_entries = []
        

        for k,b in enumerate(tmp_list):
            tmp_dict = {}
            k += 1
            for driver_inuq in b:
                if b[driver_inuq]["cid"] not in cid_list and "FILLER" not in b[driver_inuq]["name"]:
                    cid_list.append(b[driver_inuq]["cid"])
                    tmp_dict[driver_inuq] = b[driver_inuq]                 

            table_data[race_title][k] = tmp_dict
    return table_data   

def broadcast_to_room(room_name, event_name, data):
    socketio.emit(event_name, data, room=room_name, namespace='/websocket')

def get_kvali_data(year, event_name, event_type):

    with get_db() as db:
        event_data = db.query(RaceData).filter(RaceData.race_title.ilike(f'%{event_type}%'), RaceData.date.ilike(f'%{year}%'), RaceData.event_title == event_name).order_by(RaceData.event_title).all()
        
        if len(event_data) == 0:
            event_type = "Kval"
            event_data = db.query(RaceData).filter(RaceData.race_title.ilike(f'%{event_type}%'), RaceData.date.ilike(f'%{year}%'), RaceData.event_title == event_name).order_by(RaceData.event_title).all()
        
        data = {}
        event_date = ""

        for a in event_data:
            if event_date == "":
                event_date = a.date

            if a.race_title not in data.keys():
                data[a.race_title] = {}
            if a.heat not in data[a.race_title].keys():
                data[a.race_title][a.heat] = []
            
            data[a.race_title][a.heat].append({"name":a.driver_name, "club":a.driver_club, "snowmobile":a.vehicle , "penalty":int(a.penalty), "finishtime":a.finishtime})

        for category in data.values():
            for heat in category.values():
                heat.sort(key=lambda x: x['finishtime'], reverse=False)

        return None, data, str(event_date)

def get_ladder_data_live():
    from models import RealTimeData

    with get_db() as db:
        event_data = db.query(RealTimeData).filter(
            RealTimeData.race_title.ilike(f'%Stige%')).order_by(RealTimeData.race_title).all()

        data = {
            "Timedata": {},
            "event_data": []
        }

        event = ""
        event_lst = []
        table_data = {}
        table_nr = 1
        event_date = ""

        for entry in event_data:
            table_nr += 1
            if entry.race_title not in table_data:
                table_data[entry.race_title] = {}
            if entry.heat not in table_data[entry.race_title]:
                table_nr = 1
                table_data[entry.race_title][entry.heat] = {}

            table_data[entry.race_title][entry.heat][table_nr] = {
                "cid": entry.cid,
                "name": entry.driver_name,
                "club": entry.driver_club,
                "event_title": entry.race_title,
                "race_title": entry.race_title,
                "snowmobile": entry.vehicle,
                "run": None,  # This field is not present in RealTimeData
                "penalty": entry.penalty,
                "finishtime": entry.finishtime,
                "heat": entry.heat,
                "pair": None  # This field is not present in RealTimeData
            }

        for t in event_data:
            if event != t.race_title:
                if data["event_data"]:
                    event_lst.append(data)
                
                data = {
                    "Timedata": {},
                    "event_data": []
                }

                event = t.race_title

            if not data["event_data"]:
                data["event_data"].extend([t.race_title, 1])

            if t.heat not in data["Timedata"]:
                data["Timedata"][t.heat] = []

            data["Timedata"][t.heat].append([
                t.cid, t.driver_name, "", t.driver_club, t.vehicle,
                t.finishtime, t.penalty, t.inter_1
            ])

        # Append the last event data if it exists
        if data["event_data"]:
            event_lst.append(data)

        return event_lst, table_data, event_date

def get_ladder_data(year, event_name, event_type):
    
    with get_db() as db:

        event_data = db.query(RaceData).filter(RaceData.race_title.ilike(f'%{event_type}%'), RaceData.date.ilike(f'%{year}%'), RaceData.event_title == event_name).order_by(RaceData.event_title).all()

        data = {
            "Timedata": {},
            "event_data": []
        }

        event = ""
        event_lst = []
        count = 0

        table_data = {}
        table_nr = 1
        event_date = ""
        for k, entry in enumerate(event_data):
            table_nr += 1
            if entry.race_title not in table_data.keys():
                table_data[entry.race_title] = {}
            if entry.heat not in table_data[entry.race_title].keys():
                table_nr = 1
                table_data[entry.race_title][entry.heat] = {}
            if event_date == "":
                event_date = entry.date

            table_data[entry.race_title][entry.heat][table_nr] = {
                "cid": entry.cid,
                "name": entry.driver_name,
                "club": entry.driver_club,
                "event_title": entry.event_title,
                "race_title": entry.race_title,
                "snowmobile": entry.vehicle,
                "run": entry.run,
                "penalty": entry.penalty,
                "finishtime": entry.finishtime,
                "heat": entry.heat,
                "pair": entry.pair_id
            }

        reordered_table_data = process_table_data(table_data)


        for k, t in enumerate(event_data):
            if event != t.race_title:
                if data["event_data"] != []:
                    event_lst.append(data)
                
                data = {
                    "Timedata": {},
                    "event_data": []
                }

                event = t.race_title

            if data["event_data"] == []:
                data["event_data"].append(t.race_title)
                data["event_data"].append(1)

            if t.heat not in data["Timedata"]:
                data["Timedata"][t.heat] = []

            data["Timedata"][t.heat].append([t.cid, t.driver_name, "", t.driver_club, t.vehicle, t.finishtime, t.penalty, t.inter_1])

        return event_lst, reordered_table_data, event_date
    
def get_event_race_data():
    from models import RealTimeState

    with get_db() as db:
        event_data = db.query(
            RaceData.date,
            RaceData.event_title,
            RaceData.race_title
        ).order_by(RaceData.date).all()

        live_state = db.query(RealTimeState).first()

        if live_state.active_race_state == 0:
            live_state_name = "NONE"
        elif live_state.active_race_state == 1 and is_user_logged_in():
            live_state_name = live_state.active_event
        elif live_state.active_race_state == 2:
            live_state_name = live_state.active_event
        else:
            live_state_name = "NONE"
        
        result = defaultdict(lambda: defaultdict(list))

        for date, event_title, race_title in event_data:
            result[date.isoformat()][event_title].append(race_title)

        formatted_result = {}
        for date, events in result.items():
            formatted_result[date] = {
                event_title: list(set(race_titles))
                for event_title, race_titles in events.items()
            }
        
        return formatted_result, live_state_name

def check_creds(token):
    if token != app.config['SECRET_KEY']:
        return False
    else:
        return True

@app.route('/')
def home():
    from models import RaceData, RealTimeData, RealTimeState
    from sqlalchemy import distinct

    events, live_event_state = get_event_race_data()

    return render_template('index.html', events=events, live_event_state=live_event_state)

@app.route('/live')
def live():
    from models import RaceData, RealTimeData, RealTimeState
    from sqlalchemy import distinct

    json_RealTimeData = {}
    events, live_event_state = get_event_race_data()



    with get_db() as db:
        realtime_state = db.query(RealTimeState).first()
        
        if realtime_state is None:
            # Create a default RealTimeState if none exists
            default_state = RealTimeState(
                active_driver_1=None,
                active_driver_2=None,
                active_race="None",
                active_heat=1,
                active_mode=1,
                active_event = "None",
                active_race_state=0
            )
            db.add(default_state)
            db.commit()
            realtime_state = default_state
        

        realtime_state_dict = realtime_state.to_dict()

        active_event = realtime_state_dict["active_event"]
        event_state = realtime_state_dict["active_race_state"]
        if realtime_state_dict["active_race"] == None:
            return render_template('live_none.html', events=events, live_event_state=live_event_state)

        elif "stige" in realtime_state_dict["active_race"].lower():
            return render_template('live_stige.html', events=events, live_event_state=live_event_state)
        elif "kval" in realtime_state_dict["active_race"].lower():
            return render_template('live_kvali.html', events=events, live_event_state=live_event_state)
    
    return render_template('index.html', events=events, json_RealTimeData=json_RealTimeData, active_event=active_event, event_state=event_state, live_event_state=live_event_state)

@app.route('/heartbeat')
def heartbeat():
    return 'Alive'


@socketio.on('connect', namespace='/live_data')
def on_connect():
    join_room('live_data')

@socketio.on('message', namespace='/live_data')
def handle_message(message):
    emit('message', {'data': message}, room='live_data')

@socketio.on('device_connected', namespace='/live_data')
def handle_device_connected(data):
    from models import RealTimeState, RealTimeData, RealTimeKvaliData
    import json
    from utils.utils import get_kvali

    json_data = {}
    
    with get_db() as db:
        realtime_state = db.query(RealTimeState).first()
        if realtime_state is not None:
            realtime_state = realtime_state.to_dict()
            real_time_data_objects = db.query(RealTimeData).filter(RealTimeData.race_title==realtime_state["active_race"], RealTimeData.heat==realtime_state["active_heat"]).all()
            race_data = [rdata.to_dict() for rdata in real_time_data_objects]
            kvali_data = get_kvali(realtime_state["active_race"])
            kvali__crit_data = db.query(RealTimeKvaliData.kvali_num).filter(RealTimeKvaliData.race_title==realtime_state["active_race"]).first()

            json_data["state"] = realtime_state
            json_data["driver_data"] = race_data
            json_data["kvali_data"] = kvali_data

            try:
                json_data["kvali_crit"] = kvali__crit_data[0]
            except:
                json_data["kvali_crit"] = 99

            emit('server_response', {'data': json.dumps(json_data)}, room=request.sid)
        else:
            emit('server_response', {'data': {"Error": "No active session"}}, room=request.sid)

@app.route("/api/update_active_race_status", methods = ['POST'])
def active_race_status():

    request_data = request.json
    active_race = request_data["active_race"]

    app.config['race_active'] = active_race

    return {"race_active": str(app.config['race_active'])}

@app.route("/api/get_current_live_data", methods = ['GET'])
def get_current_live_data():
    from models import RealTimeData, RealTimeState

    

    json_data  = {}
    
    with get_db() as db:
        realtime_state = db.query(RealTimeState).first().to_dict()

        real_time_data_objects = db.query(RealTimeData).filter(RealTimeData.race_title==realtime_state["active_race"], RealTimeData.heat==realtime_state["active_heat"]).all()
        race_data = [rdata.to_dict() for rdata in real_time_data_objects]
    
    json_data["state"] = realtime_state
    json_data["driver_data"] = race_data


    return json_data


@app.route("/live/startlist", methods=['GET'])
def live_startlist():
    from models import RealTimeData
    from itertools import groupby
    from operator import attrgetter

    events, live_event_state = get_event_race_data()

    with get_db() as db:
        RealTimeData_entries = db.query(RealTimeData).order_by(RealTimeData.race_title, RealTimeData.heat).all()
    
        # Group the data by category, race_title, and heat
        grouped_data = {}
        for entry in RealTimeData_entries:
            category = entry.race_title.split(' - ')[-1].strip()
            race_title = ' - '.join(entry.race_title.split(' - ')[:-1]).strip()
            
            if category not in grouped_data:
                grouped_data[category] = {}
            if race_title not in grouped_data[category]:
                grouped_data[category][race_title] = {}
            if entry.heat not in grouped_data[category][race_title]:
                grouped_data[category][race_title][entry.heat] = []
            
            grouped_data[category][race_title][entry.heat].append(entry)

        return render_template('live_startlist.html', grouped_data=grouped_data, events=events,live_event_state=live_event_state)


@app.route("/live/resultatliste", methods=['GET'])
def live_resultatliste():
    from models import RealTimeData, RealTimeKvaliData
    from itertools import groupby
    from operator import attrgetter
    import json

    events, live_event_state = get_event_race_data()

    data_type = request.args.get('type')

    with get_db() as db:
        kvali_data_objects = db.query(RealTimeKvaliData).all()
        kvali_data_dicts = [kdata.to_dict() for kdata in kvali_data_objects]

        real_time_data_objects = db.query(RealTimeData).all()
        race_titles = [rdata.to_dict() for rdata in real_time_data_objects]




    categories = []


    for data in race_titles:
        title = data['race_title'].split(" ")
        title = title[-1]
        if title not in categories:
            categories.append(title)
    
    if categories == []:
         return render_template('live_resultatliste_none.html', events=events, categories=categories)
    
    if str(data_type).lower() == "stige":
        event_data, table_data, event_date = get_ladder_data_live()

        return render_template('live_resultatliste_stige.html', events=events, categories=categories, eventData=event_data, live_event_state=live_event_state)
    
    elif str(data_type).lower() == "kvalifisering":
        
        return render_template('live_resultatliste_kval.html', events=events, categories=categories, race_titles=race_titles, kvali_data=kvali_data_dicts, live_event_state=live_event_state)
    else:
        return render_template('live_resultatliste.html', events=events, categories=categories, live_event_state=live_event_state)


@app.route("/api/realtime_data", methods=['POST'])
def realtime_data_update():
    from models import RealTimeData, RealTimeState, RealTimeKvaliData
    import json
    

    data = request.json

    
    try:
        with get_db() as db:
            token = data["token"]

            if use_auth and not check_creds(token):
                return jsonify({"error": "Authentication Failed"}), 401

            race_data = data["data"]
            
            if data["single_event"]:
                from utils.utils import get_kvali
                

                race_config = race_data[0]["race_config"]
                race_title = race_config["TITLE_2"]
                mode = race_config["MODE"]
                heat = race_config["HEAT"]
                
                if "kvalifisering" in race_title.lower():
                    kvali_data = get_kvali(race_title)
                
                db.query(RealTimeData).filter(RealTimeData.race_title == race_title, RealTimeData.heat == heat).delete()
                
                active_driver_1 = None
                active_driver_2 = None
                json_data = {}

                for b in range(1, len(race_data)):
                    count = 0
                    for t in race_data[b]["drivers"]:
                        count += 1

                        if t["active"] == True:
                            if count == 1:
                                active_driver_1 = t["id"]
                            elif count == 2:
                                active_driver_2 = t["id"]

                        current_race_data = RealTimeData(
                            cid=t["id"],
                            race_title=race_title,
                            heat=heat,
                            mode=mode,
                            driver_name=f"{t['first_name']} {t['last_name']}",
                            driver_club=t["club"],
                            finishtime=float(t['time_info']['FINISHTIME']),
                            inter_1=float(t['time_info']['INTER_1']),
                            inter_2=float(t['time_info']['INTER_2']),
                            penalty=float(t['time_info']['PENELTY']),
                            speed=float(t['time_info']['SPEED']),
                            vehicle=t['vehicle'],
                            status=t['status'],
                        )
                        db.add(current_race_data)

                #Change active race
                active_race_stats = db.query(RealTimeState).first()
                active_race_stats.active_race = race_title
                active_race_stats.active_heat = heat

                if active_driver_1 is not None or active_driver_2 is not None:
                    active_race_stats.active_driver_1 = active_driver_1
                    active_race_stats.active_driver_2 = active_driver_2
                
                else:
                    active_race_stats.active_driver_1 = 0
                    active_race_stats.active_driver_2 = 0

                db.commit()
                

                realtime_state = db.query(RealTimeState).first().to_dict()
                real_time_data_objects = db.query(RealTimeData).filter(RealTimeData.race_title==realtime_state["active_race"], RealTimeData.heat==realtime_state["active_heat"]).all()
                race_data = [rdata.to_dict() for rdata in real_time_data_objects]
                kvali__crit_data = db.query(RealTimeKvaliData.kvali_num).filter(race_title==race_title).first()
                
                json_data["state"] = realtime_state
                json_data["driver_data"] = race_data
                json_data["kvali_data"] = kvali_data
                try:
                    json_data["kvali_crit"] = kvali__crit_data[0]
                except:
                    json_data["kvali_crit"] = 99
                
                socketio.emit('message', {'data': json.dumps(json_data)}, room='live_data', namespace='/live_data')

            else:
                db.query(RealTimeData).delete()
                kvali_nr_dict = json.loads(data["kvali_ranking"])
                db.query(RealTimeKvaliData).delete()
                for a in kvali_nr_dict:
                    db.add(RealTimeKvaliData(id=a["id"], kvali_num=a["kvalinr"], race_title=a["event"]))

                for race_data in data["data"]:
                    race_config = race_data[0]["race_config"]
                    race_title = race_config["TITLE_2"]
                    mode = race_config["MODE"]
                    heat = race_config["HEAT"]

                    db.query(RealTimeData).filter(RealTimeData.race_title == race_title, RealTimeData.heat == heat).delete()

                    for b in range(1, len(race_data)):
                        for t in race_data[b]["drivers"]:
                            status = t.get("status")
                            current_race_data = RealTimeData(
                                cid=t["id"],
                                race_title=race_title,
                                heat=heat,
                                mode=mode,
                                driver_name=f"{t['first_name']} {t['last_name']}",
                                driver_club=t["club"],
                                finishtime=float(t['time_info']['FINISHTIME']),
                                inter_1=float(t['time_info']['INTER_1']),
                                inter_2=float(t['time_info']['INTER_2']),
                                penalty=float(t['time_info']['PENELTY']),
                                speed=float(t['time_info']['SPEED']),
                                vehicle=t['vehicle'],
                                status=status,
                            )
                            db.add(current_race_data)
                
                db.commit()

        return jsonify({"message": "Data updated successfully"}), 200
    
    except Exception as e:
        print(f"Error in realtime_data_update: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/event/<year>/<event_name>/<race_type>')
def event_overview(year, event_name, race_type):
    if str(race_type).lower() == "kval":
        race_type = "kvalifisering"

    events, live_event_state = get_event_race_data()

    if str(race_type).lower() == "kvalifisering":
        event_data, table_data, event_date = get_kvali_data(year, event_name, race_type)
        return render_template('event_overview_kval.html', events=events, event_name=event_name, table_data=table_data, event_date=event_date, live_event_state=live_event_state)
    elif str(race_type).lower() == "stige":
        event_data, table_data, event_date = get_ladder_data(year, event_name, race_type)
        return render_template('event_overview_stige.html', events=events, event_name=event_name, event_data=event_data, table_data=table_data, event_date=event_date, live_event_state=live_event_state)

@app.route('/live/pdf')
def live_pdf():
    from models import PDFS
    
    PDF_PATH = "static/uploads/pdfs"
    pdfs = {}
    with get_db() as db:
        pdfs_db = db.query(PDFS).all()
    
        for a in pdfs_db:
            pdfs[a.file_title] = f"{PDF_PATH}/{a.file_name}"

    events, live_event_state = get_event_race_data()

    return render_template('live_pdf.html', pdfs=pdfs, events=events, live_event_state=live_event_state)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user_id'] = 1
            return redirect("/admin")
            
        flash('Invalid credentials')
        return redirect("/login")
        
    return render_template('login.html')

@app.route('/admin', methods=['GET'])
@login_required
def admin_page():
        
    return render_template('admin.html')

@app.route('/admin/admin_live_config', methods=['GET', 'POST'])
@login_required
def admin_live_config():
    from app import get_db
    from models import RealTimeData, RealTimeState, RealTimeKvaliData, PDFS
    import os
    from werkzeug.utils import secure_filename
    from datetime import datetime

    UPLOAD_FOLDER = 'static/uploads/pdfs'
    ALLOWED_EXTENSIONS = {'pdf'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    if request.method == 'POST':
        data = request.form
        event_name = data.get("eventName")
        visibility_state = data.get("visibilityState")
        clear_data = bool(data.get("remove_current_data"))

        if clear_data:
            with get_db() as db:
                db.query(RealTimeData).delete()
                db.query(RealTimeKvaliData).delete()
                db.query(RealTimeState).delete()
                db.commit()

        existing_pdfs = request.form.getlist('existing_pdfs[]')
        
        if existing_pdfs == []:
            with get_db() as db:
                realtime_state = db.query(PDFS).first()
                if realtime_state:
                    db.query(PDFS).delete()
                    db.commit()

        pdf_names = request.form.getlist('pdf_names[]')
        existing_pdf_data = dict(zip(existing_pdfs, pdf_names))

        new_files = request.files.getlist('pdf_files')
        new_pdf_names = request.form.getlist('new_pdf_names[]')

        with get_db() as db:
            realtime_state = db.query(RealTimeState).first()
            if not realtime_state:
                realtime_state = RealTimeState()
                db.add(realtime_state)

            realtime_state.active_event = event_name 
            realtime_state.active_race_state = int(visibility_state)

            for pdf_id, display_name in existing_pdf_data.items():
                pdf = db.query(PDFS).filter_by(id=int(pdf_id)).first()
                if pdf:
                    pdf.file_title = display_name

            for file, display_name in zip(new_files, new_pdf_names):
                if file and allowed_file(file.filename):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    original_filename = secure_filename(file.filename)
                    filename = f"{timestamp}_{original_filename}"
                    
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    
                    new_pdf = PDFS(
                        file_name=filename,
                        file_title=display_name
                    )
                    db.add(new_pdf)

            if existing_pdfs:
                existing_pdf_ids = [int(pdf_id) for pdf_id in existing_pdfs]
                pdfs_to_delete = db.query(PDFS).filter(
                    PDFS.id.notin_(existing_pdf_ids)
                ).all()
                
                for pdf in pdfs_to_delete:
                    file_path = os.path.join(UPLOAD_FOLDER, pdf.file_name)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                
                db.query(PDFS).filter(
                    PDFS.id.notin_(existing_pdf_ids)
                ).delete(synchronize_session=False)

            db.commit()

        return redirect(url_for('admin_live_config'))

    with get_db() as db:
        realtime_state = db.query(RealTimeState).first()
        existing_pdfs = db.query(PDFS).all()
        
        event = {
            'name': realtime_state.active_event if realtime_state else '',
            'visibility': realtime_state.active_race_state if realtime_state else 0
        }
        
        pdf_list = [
            {
                'id': pdf.id,
                'filename': pdf.file_name,
                'display_name': pdf.file_title
            }
            for pdf in existing_pdfs
        ]

        return render_template(
            'admin_live_config.html',  # Make sure this template name matches your actual template
            event=event,
            existing_pdfs=pdf_list
        )

    with get_db() as db:
        realtime_state = db.query(RealTimeState).first()
        existing_pdfs = db.query(RealTimeData).all()
        
        if realtime_state:
            realtime_state = realtime_state.to_dict()
        
        pdf_list = [
            {
                'id': pdf.id,
                'filename': os.path.basename(pdf.path) if hasattr(pdf, 'path') else '',
                'display_name': pdf.name if hasattr(pdf, 'name') else ''
            }
            for pdf in existing_pdfs
        ]

    return render_template(
        'admin_live_config.html',
        event=realtime_state,
        existing_pdfs=pdf_list
    )
@app.route('/event/<event_name>/race/<race_title>')
def race_details(event_name: str, race_title: str):
    events, live_event_state = get_event_race_data()
    date = event_name[:4]
    date_full = event_name[:10]
    event_name_formatted = event_name[5:]

    db = next(get_db())
    
    # Query for all event data ordered by date
    event_data = db.query(RaceData).filter(RaceData.race_title==race_title, RaceData.date.ilike(f'%{date}%'), RaceData.event_title.ilike(f'%{event_name_formatted}%')).order_by(RaceData.finishtime).all()

    results = []
    fastest_times = {}
    heats = 0

    for k, entry in enumerate(event_data):
        if heats < entry.heat:
            heats = entry.heat

        result = {
            "name": entry.driver_name,
            "driver_club": entry.driver_club,
            "heat": entry.heat,
            "snowmobile": entry.vehicle,
            "finishtime": entry.finishtime,
            "penalty": entry.penalty,
        }
        results.append({k: result})

        # Update fastest times
        if entry.driver_name not in fastest_times or entry.finishtime < fastest_times[entry.driver_name]['time']:
            fastest_times[entry.driver_name] = {
                'time': entry.finishtime,
                'club': entry.driver_club,
                'snowmobile': entry.vehicle,
                "penalty" : entry.penalty,
            }

    # Sort fastest times
    sorted_fastest_times = sorted(
        [{'driver': driver, **data} for driver, data in fastest_times.items()],
        key=lambda x: x['time']
    )

    if "kvalifisering" in race_title.lower():
        template = 'race_details_kvali.html'
    elif "stige" in race_title.lower():
        template = 'race_details_stige.html'
    else:
        template = 'race_details.html'

    return render_template(template, 
                           race_title=race_title,
                           events=events, 
                           event_name=event_name_formatted, 
                           race_results=results,
                           fastest_times=sorted_fastest_times,
                           date=date,
                           heats=heats,
                           table_data=table_data,
                           date_full=date,
                           live_event_state=live_event_state)

@app.route("/sql_test/")
def sql_test():
    import jsonify
    import json

    race_title = request.args.get('race_title')
    date = request.args.get('date')

    db = next(get_db())

    #event_title = "Eikerapen Bakkeløp"
    #race_title = "850 Stock - Finale"
    #date = "2023-03-18"

    return_data = []

    return render_template('active_ladder.html', race_title=race_title, date=date)


@app.route("/get_stige_data", methods = ['POST'])
def get_stige_data():
    import jsonify
    import json
    from models import RaceData

    request_data = request.json

    date = request_data["date"]
    race_title = request_data["race_title"]
    
    db = next(get_db())
    
    event_data = db.query(RaceData).filter(RaceData.race_title==race_title, RaceData.date.ilike(f'%{date}%')).order_by(RaceData.heat).all()
    data = {
        "Timedata": {},
        "event_data": []
    }
    for k, t in enumerate(event_data):
        if t.heat not in data["Timedata"]:
            data["Timedata"][t.heat] = []
        data["Timedata"][t.heat].append([t.cid, t.driver_name, "", t.driver_club, t.vehicle, t.finishtime, t.penalty, t.inter_1])
        if data["event_data"] == []:
            data["event_data"].append(t.race_title)
            data["event_data"].append(1)

    return_data = []



    return data

@app.route("/get_drivers/")
def get_drivers():
    try:
        with get_db() as db:
            query = queries.get_all_drivers()
            result = db.execute(text(query))
            rows = result.fetchall()
        
        results_set = set(row[0] for row in rows if row[0])
        results_list = list(results_set)
        
        response = jsonify(results_list)
        
        print("Response Headers:")
        for header, value in response.headers.items():
            print(f"{header}: {value}")
        
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-data/", methods=['POST'])
def upload_data():
    data = request.json
    db = SessionLocal()
    token = request.headers.get("token")

    if use_auth:
        if not check_creds(token):
            return jsonify({"error": "Authentication Failed"}), 401 
    try:
        for event in data:
            event_config = event[0]['race_config']
            event_date = date.fromisoformat(event_config['DATE'])
            event_title = event_config['TITLE_1']
            race_title = event_config['TITLE_2']
            mode = int(event_config['MODE'])
            heat = int(event_config['HEAT'])

            for race in event[1:]:
                for k, driver in enumerate(race['drivers']):
                    driver_name = driver['first_name'] + " " + driver['last_name']
                    driver_club = driver['club']

                    c_id = driver["id"]
                    pair_id = (k + 1)

                    existing_entry = db.query(RaceData).filter_by(
                        date=event_date,
                        event_title=event_title,
                        race_title=race_title,
                        heat=heat,
                        mode=mode,
                        driver_name=driver_name
                    ).first()

                    if existing_entry:
                        existing_entry.driver_club = driver_club
                        existing_entry.finishtime = float(driver['time_info']['FINISHTIME'])
                        existing_entry.inter_1 = float(driver['time_info']['INTER_1'])
                        existing_entry.inter_2 = float(driver['time_info']['INTER_2'])
                        existing_entry.penalty = float(driver['time_info']['PENELTY'])
                        existing_entry.speed = float(driver['time_info']['SPEED'])
                        existing_entry.vehicle = driver['vehicle']
                        existing_entry.status = driver.get('status')
                    else:
                        
                        new_entry = RaceData(
                            date=event_date,
                            cid=c_id,
                            event_title=event_title,
                            race_title=race_title,
                            heat=heat,
                            mode=mode,
                            driver_name=driver_name,
                            driver_club=driver_club,
                            pair_id=race['race_id'],
                            finishtime=float(driver['time_info']['FINISHTIME']),
                            inter_1=float(driver['time_info']['INTER_1']),
                            inter_2=float(driver['time_info']['INTER_2']),
                            penalty=float(driver['time_info']['PENELTY']),
                            speed=float(driver['time_info']['SPEED']),
                            vehicle=driver['vehicle'],
                            status=driver.get('status'),
                            run=pair_id,
                        )
                        db.add(new_entry)

        db.commit()
        return jsonify({"message": "Data uploaded successfully"}), 200
    except Exception as e:
        db.rollback()
        print(str(e))
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

        init_db()

if __name__ == '__main__':


    app.config['race_active'] = False
    socketio.run(app, debug=True, host="192.168.20.218")