from flask import Flask,send_from_directory , render_template, request, jsonify, Response, current_app, redirect, session, url_for, flash
from sqlalchemy import create_engine, and_, text, func, Date, extract
from sqlalchemy.orm import sessionmaker, Session
from queries import *
from models import Base, RaceData
from utils.utils import fix_names
#from flask_cors import CORS
from datetime import date
import jwt
from functools import wraps
from contextlib import contextmanager
from collections import defaultdict
from typing import Any, Dict, List, Union
from flask_socketio import SocketIO, emit, join_room
import os
from datetime import date



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
app.config['last_json_data'] = {}
socketio = SocketIO(app)

use_auth = True

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "RatSalad1337"


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

def get_ladder_data_live(race_title=None):
    from models import RealTimeData

    with get_db() as db:
        if race_title is not None:
            event_data = db.query(RealTimeData).filter(RealTimeData.race_title==race_title).order_by(RealTimeData.race_title).all()
        else:
            event_data = db.query(RealTimeData).filter(RealTimeData.race_title.ilike(f'%Stige%')).order_by(RealTimeData.race_title).all()
        
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
        
        if race_title != None:
            return event_lst
        return event_lst, table_data, event_date

def get_finale(year, event_name, event_type):
    from models import ManualEntries

    entry_data = None

    with get_db() as db:
        event_data = (
            db.query(RaceData)
            .filter(
                RaceData.race_title.ilike(f'%{event_type}%'),
                RaceData.date.ilike(f'%{year}%'),
                RaceData.event_title == event_name
            )
            .order_by(
                RaceData.penalty != 0,
                RaceData.finishtime == 0,
                RaceData.finishtime
            )
            .all()
        )

        manual = False

        if len(event_data) == 0:
            manual_entries = db.query(ManualEntries).filter(
                ManualEntries.event_title == event_name,
                ManualEntries.event_date.isnot(None) & (extract('year', ManualEntries.event_date) == year)
            ).all()

            keep_strings = ["Finale"]
            mid_lst = []
            
            for entry in manual_entries:
                for race in entry.to_dict()["races"]:
                    entry_date = entry.to_dict()["event_date"]
                    event_title = entry.to_dict()["event_title"]

                    if "finale" in race["race_title"].lower():
                        mid_lst.append(race)

                        race_title = race["race_title"]

            table_data = [{
                "date":entry_date,
                "event_title": event_title,
                "race_title": race_title,
                "drivers": mid_lst
            }]

            return table_data, entry_date, True

        table_data = {}
        
        for table_nr, entry in enumerate(event_data):
            table_nr += 1
            if entry.race_title not in table_data.keys():
                table_data[entry.race_title] = {}
            
            if entry_data is None:
                entry_date = entry.date

            table_data[entry.race_title][table_nr] = {
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
            }


        return table_data, entry_date, False


def process_race_standings(event_data):
    """
    Process race data from database query results and determine standings for all races.
    
    Args:
        event_data: List of RaceData objects from database query
    
    Returns:
        dict: Nested dictionary of events, races, and driver standings
              Format: {event_title: {race_title: [{'driver': name, 'position': pos, 'points': pts}]}}
    """
    
    events = {}
    for a in event_data:
        entry_dict = a.to_dict()
        
        if entry_dict["event_title"] not in events:
            events[entry_dict["event_title"]] = {}
            
        if entry_dict["race_title"] not in events[entry_dict["event_title"]]:
            events[entry_dict["event_title"]][entry_dict["race_title"]] = {}
            
        events[entry_dict["event_title"]][entry_dict["race_title"]][entry_dict["driver_name"]] = [
            entry_dict["heat"], 
            entry_dict["pair_id"], 
            entry_dict["status"], 
            entry_dict["finishtime"], 
            entry_dict["penalty"]
        ]
    
    results = {}
    
    point_system = {
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
        9: 6,
        17: 7
    }
    
    for event_title, races in events.items():
        results[event_title] = {}
        
        for race_title, drivers in races.items():
            if not drivers:
                continue
                
            max_heat = max(drivers[driver][0] for driver in drivers)
            
            drivers_by_heat = {}
            for driver_name, data in drivers.items():
                heat = data[0]
                if heat not in drivers_by_heat:
                    drivers_by_heat[heat] = []
                
                drivers_by_heat[heat].append({
                    'name': driver_name,
                    'heat': heat,
                    'pair_id': data[1],
                    'status': data[2],
                    'finishtime': data[3],
                    'penalty': data[4]
                })
            
            # Identify the top 4 positions
            finalists = drivers_by_heat.get(max_heat, [])
            
            # Initialize positions
            first, second, third, fourth = None, None, None, None
            
            # Find 1st and 2nd place (pair_id = 1 in the finals)
            final_pair1 = [d for d in finalists if d['pair_id'] == 1]
            if len(final_pair1) == 2:
                winner = next((d for d in final_pair1 if d['status'] == 1), None)
                loser = next((d for d in final_pair1 if d['status'] == 2), None)
                
                if winner:
                    first = winner['name']
                if loser:
                    second = loser['name']
            
            # Find 3rd and 4th place (pair_id = 2 in the finals)
            final_pair2 = [d for d in finalists if d['pair_id'] == 2]
            if len(final_pair2) == 2:
                winner = next((d for d in final_pair2 if d['status'] == 1), None)
                loser = next((d for d in final_pair2 if d['status'] == 2), None)
                
                if winner:
                    third = winner['name']
                if loser:
                    fourth = loser['name']
            
            # Calculate points for all drivers
            total_drivers = len(drivers)
            points = {}
            
            # Determine default points based on total number of drivers
            default_points = 7  # For 17-32 drivers
            if total_drivers <= 4:
                default_points = 4
            elif total_drivers <= 8:
                default_points = 5
            elif total_drivers <= 16:
                default_points = 5
            
            for driver in drivers:
                points[driver] = default_points
            
            if first:
                points[first] = 1
            if second:
                points[second] = 2
            if third:
                points[third] = 3
            if fourth:
                points[fourth] = 4
            
            if max_heat > 1:
                semifinal_heat = max_heat - 1
                semifinalists = drivers_by_heat.get(semifinal_heat, [])
                
                # Exclude drivers who advanced to finals
                top_four = [name for name in [first, second, third, fourth] if name]
                eliminated_semifinalists = [
                    driver for driver in semifinalists 
                    if driver['name'] not in top_four
                ]
                
                # Assign 5 points to 5th-8th places
                for driver in eliminated_semifinalists:
                    points[driver['name']] = 5
            
            # Create final standings sorted by points
            standings = [
                {'driver': driver, 'position': i+1, 'points': pts}
                for i, (driver, pts) in enumerate(sorted(points.items(), key=lambda x: x[1]))
            ]
            
            # Store results for this race
            results[event_title][race_title] = standings
    
    return results

def get_ladder_data_standing(year, event_name):
    from sqlalchemy import or_, and_

    with get_db() as db:
        event_data = db.query(RaceData).filter(
            and_(
                or_(*[RaceData.race_title.ilike(f'%{name}%') for name in event_name]),
                RaceData.date.ilike(f'%{year}%'),
            )
        ).order_by(RaceData.event_title).all()
        data = process_race_standings(event_data)

    return data

def get_ladder_data(year, event_name, event_type, cup=None):
    from sqlalchemy import or_, and_
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
        if cup == None:        
        # Add the last group of data after the loop ends
            if data["event_data"] != []:
                event_lst.append(data)
            else:
                from models import ManualEntries
                manual_entries = db.query(ManualEntries).filter(
                    ManualEntries.event_title == event_name,
                    ManualEntries.event_date.isnot(None) & (extract('year', ManualEntries.event_date) == year)
                ).all()

                keep_strings = ["Stige"]
                mid_lst = []
                
                for entry in manual_entries:
                    for race in entry.to_dict()["races"]:
                        entry_date = entry.to_dict()["event_date"]
                        event_title = entry.to_dict()["event_title"]

                        if "stige" in race["race_title"].lower():
                            mid_lst.append(race)

                            race_title = race["race_title"]

                table_data = [{
                    "date":entry_date,
                    "event_title": event_title,
                    "race_title": race_title,
                    "drivers": mid_lst
                }]
                return event_lst, table_data, event_date, True

        return event_lst, reordered_table_data, event_date, False
    
def get_event_race_data():
    from models import RealTimeState, ManualEntries

    with get_db() as db:
        event_data = db.query(
            RaceData.date,
            RaceData.event_title,
            RaceData.race_title
        ).filter(RaceData.enabled==True).order_by(RaceData.date).all()
        manual_entries = db.query(ManualEntries).all()

        manual_entries_dict = {}

        for a in manual_entries:
            
            event_date = a.event_date.isoformat()
            event_title = a.event_title

            for b in a.races:

                race_title = b["race_title"]
                if event_date not in manual_entries_dict:
                    manual_entries_dict[event_date] = {}
                if event_title not in manual_entries_dict[event_date]:
                    manual_entries_dict[event_date][event_title] = []
                
                manual_entries_dict[event_date][event_title].append(race_title)
        
        live_state = db.query(RealTimeState).first()

        if live_state is not None:

            if live_state.active_race_state == 0:
                live_state_name = "NONE"
            elif live_state.active_race_state == 1 and is_user_logged_in():
                live_state_name = live_state.active_event
            elif live_state.active_race_state == 2:
                live_state_name = live_state.active_event
            else:
                live_state_name = "NONE"
        else:
            live_state_name = "NONE"

        result = defaultdict(lambda: defaultdict(list))

        manual_entries_dict = {}

        for a in manual_entries:
            event_date = a.event_date.isoformat()
            event_title = a.event_title

            for b in a.races:
                race_title = b["race_title"]
                if event_date not in manual_entries_dict:
                    manual_entries_dict[event_date] = {}
                if event_title not in manual_entries_dict[event_date]:
                    manual_entries_dict[event_date][event_title] = []

                manual_entries_dict[event_date][event_title].append(race_title)

        for date, event_title, race_title in event_data:
            result[date.isoformat()][event_title].append(race_title)

        for date, events in manual_entries_dict.items():
            for event_title, race_titles in events.items():
                
                result[date][event_title].extend(race_titles)

        formatted_result = {}

        result = dict(sorted(result.items()))

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
    
def aggregate_driver_points(race_standings):
    """
    Aggregate points for each driver by race title across all events.
    
    Args:
        race_standings (dict): Nested dictionary of event standings from process_race_standings
                              Format: {event_title: {race_title: [{'driver': name, 'position': pos, 'points': pts}]}}
    
    Returns:
        dict: Updated race_standings with a new key 'aggregated_points' containing
              aggregated points by race title
              Format: race_standings['aggregated_points'] = {race_title: [{'driver': name, 'total_points': points}]}
    """
    # Initialize the aggregated points dictionary
    aggregated_points = {}
    
    # Collect all unique race titles
    all_race_titles = set()
    for event in race_standings.values():
        all_race_titles.update(event.keys())
    
    # Initialize aggregated points structure for each race title
    for race_title in all_race_titles:
        aggregated_points[race_title] = {}
    
    # Aggregate points across all events for each race title and driver
    for event_title, races in race_standings.items():
        for race_title, standings in races.items():
            for standing in standings:
                driver_name = standing['driver']
                points = standing['points']
                
                # Initialize driver in aggregated points if not present
                if driver_name not in aggregated_points[race_title]:
                    aggregated_points[race_title][driver_name] = 0
                
                # Add points to driver's total for this race title
                aggregated_points[race_title][driver_name] += points
    
    # Convert to the desired format: {race_title: [{'driver': name, 'total_points': points}]}
    formatted_aggregated_points = {}
    for race_title, drivers in aggregated_points.items():
        # Sort drivers by points (lowest first, as lower points are better)
        sorted_drivers = sorted(
            [{'driver': driver, 'total_points': points} for driver, points in drivers.items()],
            key=lambda x: x['total_points']
        )
        formatted_aggregated_points[race_title] = sorted_drivers
    
    # Add the aggregated points to the original standings dictionary
    race_standings['aggregated_points'] = formatted_aggregated_points
    
    return race_standings

def filter_drivers(results_dict, allowed_drivers_dict):
    """
    Filter out drivers from the results dictionary who are not in the allowed drivers dictionary.
    If a driver is in allowed_drivers_dict but not in results_dict, they get 
    one more point than the highest-scoring driver in that class.
    
    Args:
        results_dict (dict): Nested dictionary containing competition results
        allowed_drivers_dict (dict): Dictionary with class names as keys and lists of allowed drivers as values
        
    Returns:
        dict: Filtered results dictionary
    """
    filtered_results = {}

    for event_name, event_data in results_dict.items():
        filtered_results[event_name] = {}
                
        for class_name, class_data in event_data.items():
            filtered_results[event_name][class_name] = []
            
            base_class_name = class_name.split(" - Stige")[0]
            
            if base_class_name in allowed_drivers_dict:
                allowed_names = allowed_drivers_dict[base_class_name]
                
                # First pass: gather existing drivers and find max points
                existing_drivers = set()
                max_points = 0
                
                for driver_entry in class_data:
                    if driver_entry["driver"] in allowed_names:
                        filtered_results[event_name][class_name].append(driver_entry)
                        existing_drivers.add(driver_entry["driver"])
                        if "points" in driver_entry and driver_entry["points"] > max_points:
                            max_points = driver_entry["points"]
                
                # Second pass: add missing drivers with max_points + 1
                for driver_name in allowed_names:
                    if driver_name not in existing_drivers:
                        new_entry = {
                            "driver": driver_name,
                            "points": max_points + 1
                        }
                        filtered_results[event_name][class_name].append(new_entry)
            else:
                filtered_results[event_name][class_name] = []

    return filtered_results

@app.route('/cup', methods=['GET', 'POST'])
def cup_test():
    import json
    from models import CupEntries
    out = request.args.get('output')
    
    event_name = "Norgermesterskap"
    race_type = "Stige"
    data = {
        "2-Takt Turbo Open Modified": ["Bjørn Viki", "Espen Bryggeså", "Fredrik Åsland", "Jan Sigvald Thorsland", "Ole André Olsen", "Olav Kristian Stangvik"],
        "2-Takt Turbo Stock": ["Jan Sigvald Thorsland","Espen Bryggeså", "Fredrik Åsland", "Gaute Eikild", "Johnny Bjelland", "Lars Erik Skeibrok", "Lukas Helle", "Ole André Olsen"],
        "600 Stock": ["Daniel Stulien", "Espen Bryggeså", "Johnny Bjelland", "John Ola Åsland", "Knut Even Nesland", "Lukas Helle", "Ole André Olsen", "Olav Kristian Stangvik", "Sigbjørn Oksefjell Ribe", "Terje Verdal", "Tor Elling Eikerapen", "Vilde Thorsland Lauen", "Yngve Ousdal"],
        "700 Stock": ["Daniel Stulien", "John Ola Åsland", "Knut Even Nesland", "Mathias Skomedal", "Ole André Olsen", "Olav Kristian Stangvik", "Sigbjørn Oksefjell Ribe", "Svein Rune Lauen", "Terje Verdal", "Yngve Ousdal"],
        "800 Stock": ["Aanund Slettetveit", "Dag Helge Aas", "Jan Sigvald Thorsland", "Knut Even Nesland", "Margrethe Stølen-Stean", "Olav Kristian Stangvik", "Vilde Ketilsdotter Homme", "Vilde Thorsland Lauen"],
        "900 Stock": ["Andine Telhaug","Aanund Slettetveit", "Daniel Harstad", "Edvin Rykkelid", "Gaute Eikild", "Hege Viki", "Jan Sigvald Thorsland", "Lars Kåre Egelandsdal Skeie", "Oda Tobiassen Seland", "Olav Kristian Stangvik", "Sigbjørn Oksefjell Ribe", "Terje Verdal", "Yngve Ousdal"],
        "Pro Stock": ["Aanund Slettetveit", "Even Hobbesland", "Gaute Eikild", "Geir Josdal", "Hege Viki", "Jan Sigvald Thorsland", "Lars Kåre Egelandsdal Skeie", "Ola Terje Handeland", "Olav Kristian Stangvik", "Terje Verdal", "Torstein Hermansen", "Yngve Ousdal"],
        "Rekrutt 13-14": ["Andreas Nøkland", "Anna Hodne Syvertsen", "Daniel Honnemyr", "Jonas Ovedal"],
        "Retro klasse 8": ["Dag Helge Aas", "Espen Urevatn", "Fredrik Åsland", "Gaute Eikild", "Geir Josdal", "Johnny Bjelland", "Svein Oskar Waldeland", "Tom Handeland", "Tor Elling Eikerapen"],
        "Top Fuel": ["Dag Gunnar Telhaug","Arne Johnnysson Pedersen", "Bjørn Terje Viki", "Bjørn Vidar Klepsland", "Daniel Stulien", "Fredrik Rysstad", "Håvard Rafoss", "Håvard Skeie Holte", "Jan Erik Uppstad", "Jostein Nomeland", "Ole André Olsen", "Olav Kristian Stangvik", "Tom Handeland", "Tor Arne Larsen Kasin", "Tor-Agnar Slåtta"],
        "Trail Unlimited": ["Arne Johnnysson Pedersen", "Bjørn Terje Viki", "Bjørn Viki", "Bjørn Nøkland", "Daniel Harstad", "Daniel Stulien", "Edvin Rykkelid", "Fredrik Rysstad", "Håvard Skeie Holte", "Jakob Austegard", "Jan Erik Uppstad", "Jostein Nomeland", "Lars Erik Skeibrok", "Morten Håvorstad", "Ole André Olsen", "Olav Kristian Stangvik", "Tom Handeland", "Tor Arne Larsen Kasin", "Tor-Agnar Slåtta", "Vilde Ketilsdotter Homme"],
        "Ungdom 14-16 Med Pro Stock 600": ["Aksel Josdal Nymoen", "Arthur Nordgaard", "August Haddeland", "Benjamin Sandåker-Åsland", "Brynjar Smeland", "Daniel Hauan Skille", "Eivind Austad Uppstad", "Håvard Oksefjell Ribe", "Magnus Reiersdal", "Ole Bjørnestad Josdal", "Ole Gunnar Lio Hermansen", "Torleiv Håkon Løyland-Helle"],
        "Ungdom 14-16 Uten Pro Stock 600": ["August Haddeland", "Brynjar Smeland", "Daniel Hauan Skille"],
        "Trail Turbo":["Tom Handeland", "Fredrik Åsland", "Johnny Bjelland", "Jan Sigvald Thorsland", "Ole André Olsen", "Øyvind Urevatn", "Håvard Skeie Holte", "Lars Erik Skeibrok"],
    }
    classes = [
        "2-Takt Turbo Open Modified - Stige",
        "2-Takt Turbo Stock - Stige",
        "600 Stock - Stige",
        "700 Stock - Stige",
        "800 Stock - Stige",
        "900 Stock - Stige",
        "Pro Stock - Stige",
        "Rekrutt 13-14 - Stige",
        "Retro klasse 8 - Stige",
        "Top Fuel - Stige",
        "Trail Unlimited - Stige",
        "Ungdom 14-16 Med Pro Stock 600 - Stige",
        "Ungdom 14-16 Uten Pro Stock 600 - Stige",
        "Trail Turbo - Stige",
    ] 
    year = 2025
    race_type = "Stige"
    test = get_ladder_data_standing(year, classes)
    filtered = filter_drivers(test, data)
    sorted_points = aggregate_driver_points(filtered)

    for k, b in enumerate(sorted_points):
        if k == 0:
            for t in sorted_points[b]:
                if t == "Trail Turbo - Stige":
                    print(sorted_points[b][t])
                else:
                    print(t)
    if out == "json":
        return json.dumps(sorted_points) 
    events, live_event_state = get_event_race_data()
    return render_template('cup.html', data=sorted_points, events=events, live_event_state=live_event_state)

@app.route('/')
def index():
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
                display_quali=False,

            )
            db.add(default_state)
            db.commit()
            realtime_state = default_state
        

        realtime_state_dict = realtime_state.to_dict()

        active_event = realtime_state_dict["active_event"]
        event_state = realtime_state_dict["active_race_state"]
        if realtime_state_dict["active_race"] == None:
            return render_template('live_none.html', events=events, live_event_state=live_event_state)

        elif "finale" in realtime_state_dict["active_race"].lower():
            return render_template('live_finale.html', events=events, live_event_state=live_event_state)
        
        elif "stige" in realtime_state_dict["active_race"].lower():
            print("asdasdasd")
            return render_template('live_stige.html', events=events, live_event_state=live_event_state)
        
        elif "kval" in realtime_state_dict["active_race"].lower():

            display_quali_value = db.query(RealTimeState.display_quali).first()[0]
            return render_template('live_kvali.html', events=events, live_event_state=live_event_state, display_quali=display_quali_value)
    
    return render_template('live_none.html', events=events, json_RealTimeData=json_RealTimeData, active_event=active_event, event_state=event_state, live_event_state=live_event_state)

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
            if "finale" in realtime_state["active_race"].lower():
                real_time_data_objects = db.query(RealTimeData).filter(RealTimeData.race_title==realtime_state["active_race"], RealTimeData.heat==realtime_state["active_heat"]).all()
                json_data["driver_data"] = []
                json_data["state"] = realtime_state

                for a in real_time_data_objects:
                    json_data["driver_data"].append(a.to_dict())
                    
            
            elif "kvalifisering" in realtime_state["active_race"].lower():
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

            else:
                real_time_data_objects = db.query(RealTimeData).filter(RealTimeData.race_title==realtime_state["active_race"], RealTimeData.heat==realtime_state["active_heat"]).all()
                race_data = [rdata.to_dict() for rdata in real_time_data_objects]
                json_data["state"] = realtime_state
                json_data["driver_data"] = race_data
                
                json_data["ladder_data"] = get_ladder_data_live(realtime_state["active_race"])
        
        emit('server_response', {'data': json.dumps(json_data)}, room=request.sid)

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


@app.route("/live/eventer", methods=['GET'])
def live_eventer():
    from models import live_event_liste
    from models import RealTimeState

    

    active_events = []

    with get_db() as db: 
        events_active = db.query(live_event_liste).all()
        active_event = db.query(RealTimeState.active_race, RealTimeState.active_heat).first()

        event_name = active_event[0]
        active_heat = active_event[1]

        for b in events_active:
            active_events.append(b.to_dict())

    events, live_event_state = get_event_race_data()

    return render_template('live_event_list.html', events=events,live_event_state=live_event_state, active_events=active_events, event_name=event_name, active_heat=active_heat)

@app.route("/test", methods=['GET'])
def test():
    import json

    data = get_ladder_data_live("Trail Unlimited - Stige")

    return json.dumps(data)

@app.route("/live/resultatliste", methods=['GET'])
def live_resultatliste():
    from models import RealTimeData, RealTimeKvaliData, RealTimeState
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
         return render_template('live_resultatliste_none.html', events=events, categories=categories, live_event_state=live_event_state)
    
    if str(data_type).lower() == "stige":
        event_data, table_data, event_date = get_ladder_data_live()

        return render_template('live_resultatliste_stige.html', events=events, categories=categories, eventData=event_data, live_event_state=live_event_state)
    
    elif str(data_type).lower() == "kvalifisering":
        with get_db() as db:
            display_quali_value = db.query(RealTimeState.display_quali).first()[0]
        return render_template('live_resultatliste_kval.html', events=events, categories=categories, race_titles=race_titles, kvali_data=kvali_data_dicts, live_event_state=live_event_state, display_quali=display_quali_value)
        
    elif str(data_type).lower() == "finale":

        return render_template('live_resultatliste_finale.html', events=events, categories=categories, 
                               race_titles=race_titles, live_event_state=live_event_state)

    else:
        return render_template('live_resultatliste_none.html', events=events, categories=categories, live_event_state=live_event_state)




@app.route("/admin/edit_names", methods=['POST', 'GET'])
def edit_names():
    if request.method == 'POST':
        from models import RaceData
        from sqlalchemy import distinct, update
        data = request.json

        old_name = data['old_names']
        new_name = data['new_names']

        print(old_name, "OLD")
        print(new_name, "NEW")
        for a in range(len(old_name)):
            with get_db() as db:
                affected_count = db.query(RaceData).filter(
                    RaceData.driver_name == old_name[a]
                ).count()
                
                if affected_count == 0:
                    return False, f"No entries found for driver name: {old_name[a]}"
                
                # Perform the update
                result = db.execute(
                    update(RaceData)
                    .where(RaceData.driver_name == old_name[a])
                    .values(driver_name=new_name[a])
                )


    return render_template('admin_name_edit.html')

import base64
from pathlib import Path
from flask import jsonify, request, render_template
from sqlalchemy.exc import SQLAlchemyError

@app.route("/admin/add_manually", methods=['POST', 'GET'])
def add_manually():
    from models import ManualEntries
    import subprocess
    import hashlib

    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data received'}), 400

            action = data.get('action')
            if not action:
                return jsonify({'success': False, 'message': 'No action specified'}), 400

            with get_db() as db:
                # Handle deletion
                if action == 'delete':
                    if not data.get('id'):
                        return jsonify({'success': False, 'message': 'No ID provided for deletion'}), 400

                    db.query(ManualEntries).filter(
                        ManualEntries.id == data['id']
                    ).delete()
                    db.commit()
                    return jsonify({'success': True, 'message': 'Event deleted successfully'})

                # For creation, check for event title uniqueness
                elif action == 'create':
                    existing_event = db.query(ManualEntries).filter(
                        ManualEntries.event_title == data['event_title']
                    ).first()
                    if existing_event:
                        return jsonify({'success': False, 'message': 'An event with this title already exists'}), 400

                # Process PDF uploads for both creation and editing
                if action in ['create', 'edit']:
                    for race in data.get("races", []):
                        if race.get('pdf'):
                            try:
                                pdf_data = race['pdf']
                                filename = pdf_data['filename']
                                content = pdf_data['content']
                                frontend_hash = pdf_data.get('hash', 'No hash provided')

                                # Create sanitized filenames using event and race titles
                                event_title = data['event_title'].replace(" ", "_")
                                race_title = race['race_title'].replace(" ", "_")
                                eventdate = data['event_date'].replace(" ", "_")
                                unique_filename = f"{eventdate}_{event_title}_{race_title}.pdf"

                                # Ensure the target directory exists
                                pdf_dir = Path('static/pdfs/manual_entries')
                                pdf_dir.mkdir(exist_ok=True)

                                # Save the PDF file
                                pdf_path = pdf_dir / unique_filename
                                pdf_content = base64.b64decode(content)
                                backend_hash = hashlib.sha256(pdf_content).hexdigest()
                                
                                print(f"PDF Upload for {race_title}:")
                                print(f"Frontend Hash: {frontend_hash}")
                                print(f"Backend Hash:  {backend_hash}")
                                print(f"Hashes match: {frontend_hash == backend_hash}")
                                
                                pdf_path.write_bytes(pdf_content)

                                # Record the PDF filename.
                                race['pdf_filename'] = unique_filename

                                # Prepare output image path.
                                output_image_filename = f"{eventdate}_{event_title}_{race_title}.jpg"
                                output_image_path = pdf_dir / output_image_filename

                                output_basename = str(output_image_path.with_suffix(''))
                                cmd = [
                                    'pdftoppm',
                                    '-jpeg',
                                    '-singlefile',
                                    str(pdf_path),
                                    output_basename
                                ]
                                # Run the command. If it fails, subprocess.CalledProcessError is raised.
                                subprocess.run(cmd, check=True)

                                # Optionally store the thumbnail filename for later use.
                                race['thumbnail_filename'] = output_image_filename

                                # Remove the raw PDF data from the race dictionary.
                                del race['pdf']

                            except Exception as e:
                                return jsonify({
                                    'success': False,
                                    'message': f'Error processing PDF: {str(e)}'
                                }), 400

                if action == 'edit':
                    db.query(ManualEntries).filter(
                        ManualEntries.event_title == data['event_title']
                    ).delete()

                event_date_new = date.fromisoformat(data["event_date"])

                new_entry = ManualEntries(
                    event_title=data['event_title'],
                    event_date=event_date_new,
                    races=data['races']
                )
                db.add(new_entry)

                try:
                    db.commit()
                except SQLAlchemyError as e:
                    db.rollback()
                    return jsonify({
                        'success': False,
                        'message': f'Database error: {str(e)}'
                    }), 500

                return jsonify({
                    'success': True,
                    'message': f'Event {action}d successfully'
                })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Server error: {str(e)}'
            }), 500

    else:  # GET request
        try:
            with get_db() as db:
                events = db.query(ManualEntries).all()
                events_lst = []
                for event in events:
                    try:
                        races = event.races if event.races else []
                        event_dict = {
                            'id': event.id,
                            'event_title': event.event_title,
                            'races': races,
                            'event_date': event.event_date.isoformat() if event.event_date else None,
                            'race_title': races[0]['race_title'] if races else '',
                            'mode': races[0]['mode'] if races else 1,
                            'driver_places': races[0]['driver_places'] if races else [],
                            'pdf_filename': races[0].get('pdf_filename') if races else "None"
                        }

                        events_lst.append(event_dict)
                    except Exception as e:
                        print(f"Error processing event {event.id}: {str(e)}")
                        continue

            return render_template('admin_add_manual.html', manual_entries=events_lst)

        except Exception as e:
            print(f"Database error: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error loading entries: {str(e)}'
            }), 500

@app.route('/api/search-drivers')
def search_drivers():
    from models import RaceData
    from sqlalchemy import distinct

    term = request.args.get('term')
    with get_db() as db:
        matching_names = (
                    db.query(distinct(RaceData.driver_name))
                    .filter(RaceData.driver_name.isnot(None))
                    .filter(RaceData.driver_name != '')
                    .filter(RaceData.driver_name.ilike(f'%{term}%'))
                    .order_by(RaceData.driver_name)
                    .all()
                )        
        return [name[0] for name in matching_names]

@app.route("/admin/edit_archive", methods=['POST', 'GET'])
def edit_archive():
    from models import RaceData, RaceClasses
    from sqlalchemy import distinct, func

    classes_list = []
    
    with get_db() as db:
        all_dates = db.query(RaceData.date).distinct().all()


        years = sorted(list(set(date[0].year for date in all_dates)), reverse=True)
        
        races_by_year = {}
        for year in years:
            events = db.query(
                RaceData.race_title,
                RaceData.id,
                RaceData.event_title,
                RaceData.date,
                RaceData.enabled,
                RaceData.race_class
            ).filter(
                RaceData.date >= f'{year}-01-01',
                RaceData.date <= f'{year}-12-31'
            ).order_by(RaceData.date.desc()).distinct(RaceData.race_title).all()

            events_by_title = {}
            added = []

            for e in events:
                if [year, e.race_title, e.event_title] not in added:
                    added.append([year, e.race_title, e.event_title])
                    
                    if e.event_title not in events_by_title:
                        events_by_title[e.event_title] = []
                    
                    events_by_title[e.event_title].append({
                        'id': e.id,
                        'race_title': e.race_title,
                        'event_title': e.event_title,
                        'date': e.date,
                        'race_class': e.race_class,
                        'enabled': e.enabled
                    })

            races_by_year[year] = events_by_title

        total_events = sum(len(year_data.keys()) for year_data in races_by_year.values())

        return render_template(
            'admin_archive_edit.html', 
            races_by_year=races_by_year,
            total_events=total_events,
        )
    
@app.route('/admin/edit_archive/event-title', methods=['GET', 'POST'])
def event():
    from models import RaceData
    from sqlalchemy import distinct, func
    import datetime

    
    if request.method == 'GET':
        year = request.args.get('year')
        event = request.args.get('event_name')
        with get_db() as db:
            entry = db.query(RaceData).filter(
                RaceData.event_title == event,
                func.strftime('%Y', RaceData.date) == str(year)
            ).first().to_dict()
            entry["date"] = entry["date"].isoformat()
            return entry

    elif request.method == 'POST':
        data = request.json

        old_config = data.get('old_config')
        new_config = data.get('new_config')

        new_date = datetime.datetime.strptime(new_config['date'], '%Y-%m-%d').date()

        with get_db() as db:
            current_data = db.query(RaceData).filter(
                RaceData.event_title == old_config['event_title'],
                RaceData.date == old_config['date']
            ).all()
            
            for record in current_data:
                record.event_title = new_config['event_title']
                record.date = new_date
                record.enabled = new_config['enabled']
            db.commit()

    return jsonify({"success": True})

@app.route('/admin/edit_archive/race', methods=['GET', 'POST'])
def edit_archive_race_title():
    from models import RaceData, RaceClasses
    from sqlalchemy import distinct, func
    import datetime
    import json

    classes_list = []
    return_data = {}
    
    if request.method == 'GET':



        race_id = request.args.get('race_id')

        with get_db() as db:
            classes_query = db.query(RaceClasses.name).all()
            for a in classes_query:
                classes_list.append(a.name)

            entry = db.query(RaceData).filter(RaceData.id == race_id).first().to_dict()
            entry["date"] = entry["date"].isoformat()

            return_data["entry"] = entry
            return_data["classes"] = classes_list


            return return_data
            
    elif request.method == 'POST':
        data = request.json

        
        old_config = data.get('old_config')
        new_config = data.get('new_config')
        new_date = datetime.datetime.strptime(new_config['date'], '%Y-%m-%d').date()

        with get_db() as db:
            current_data = db.query(RaceData).filter(
                RaceData.event_title == old_config['event_title'],
                RaceData.race_title == old_config['race_title'],
                RaceData.date == old_config['date']
            ).all()
            
            for record in current_data:
                record.event_title = new_config['event_title']
                record.date = new_date
                record.enabled = new_config['enabled']
                record.race_title = new_config['race_title']
                record.race_class = new_config['race_class']
                record.mode = new_config['mode']

            db.commit()


    return jsonify({"success": True})

@app.route('/admin/edit_archive/drivers', methods=['GET', 'POST'])
def edit_archive_driver_data():
    from models import RaceData

    race_id = request.args.get('race_id')  
    with get_db() as db:
        race = db.query(RaceData).filter_by(id=race_id).first()
        
        # Get all drivers for this race
        drivers = db.query(RaceData)\
            .filter_by(race_title=race.race_title, date=race.date)\
            .order_by(RaceData.heat, RaceData.run)\
            .all()
        
        return jsonify({
            "race_id": race_id,
            "race_title": race.race_title,
            "drivers": [{
                "id": d.id,
                "heat": d.heat,
                "run": d.run,
                "driver_name": d.driver_name,
                "driver_club": d.driver_club,
                "finishtime": d.finishtime,
                "status": d.status,
                "inter_1": d.inter_1,
                "inter_2": d.inter_2,
                "penalty": d.penalty,
                "vehicle": d.vehicle
            } for d in drivers]
        })

@app.route("/api/realtime_data", methods=['POST'])
def realtime_data_update():
    from models import RealTimeData, RealTimeState, RealTimeKvaliData
    import json    

    data = request.json

    with get_db() as db:
        token = data["token"]

        if use_auth and not check_creds(token):
            return jsonify({"error": "Authentication Failed"}), 401

        race_data = data["data"]
        
        if data["single_event"]:
            from utils.utils import get_kvali, get_finale_live
            
            race_config = race_data[0]["race_config"]
            race_title = race_config["TITLE_2"]
            mode = race_config["MODE"]
            heat = race_config["HEAT"]

            
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


                    try:
                        print(t["status"])
                    except:
                        t["status"] = "None"

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
            if active_race_stats is None:
                active_race_stats = RealTimeState(
                        active_driver_1=0,
                        active_driver_2=0,
                        active_event="None",
                        active_race="None",
                        active_heat="None",
                        active_mode="None",
                        active_race_state=False,
                        display_quali=False
                    )
                db.add(active_race_stats)
                db.commit()

            active_race_stats.active_race = race_title
            active_race_stats.active_heat = heat

            if active_driver_1 is not None or active_driver_2 is not None:
                active_race_stats.active_driver_1 = active_driver_1
                active_race_stats.active_driver_2 = active_driver_2
            
            else:
                active_race_stats.active_driver_1 = 0
                active_race_stats.active_driver_2 = 0

            db.commit()
            
            

            realtime_state = db.query(RealTimeState).first()
            realtime_state_dict = realtime_state.to_dict()

            if realtime_state != None:
                realtime_state_dict = realtime_state.to_dict()

            real_time_data_objects = db.query(RealTimeData).filter(RealTimeData.race_title==realtime_state_dict["active_race"], RealTimeData.heat==realtime_state_dict["active_heat"]).all()
            race_data = [rdata.to_dict() for rdata in real_time_data_objects]
            kvali__crit_data = db.query(RealTimeKvaliData.kvali_num).filter(RealTimeKvaliData.race_title==race_title).first()

            if "kvalifisering" in race_title.lower():
                kvali_data = get_kvali(race_title)
                mode = "kvali"
            elif "finale" in race_title.lower():
                finale_data = get_finale_live(race_title)
                mode = "finale"
            elif "stige" in race_title.lower():
                 json_data["ladder_data"] = get_ladder_data_live(race_title)

            else:
                kvali_data = None
            json_data["state"] = realtime_state_dict

            json_data["driver_data"] = race_data
            if mode == "kvali":
                json_data["kvali_data"] = kvali_data
            try:
                json_data["kvali_crit"] = kvali__crit_data[0]
            except:
                json_data["kvali_crit"] = 99
            
            if json_data != app.config["last_json_data"]:
                
                socketio.emit('message', {'data': json.dumps(json_data)}, room='live_data', namespace='/live_data')
                app.config["last_json_data"] = json_data

        else:
            from models import live_event_liste

            db.query(RealTimeData).delete()
            kvali_nr_dict = json.loads(data["kvali_ranking"])
            db.query(RealTimeKvaliData).delete()
            db.query(live_event_liste).delete()

            for a in kvali_nr_dict:
                db.add(RealTimeKvaliData(id=a["id"], kvali_num=a["kvalinr"], race_title=a["event"]))

            events = json.loads(data["event_data"])

               
            for b in events:
                db.add(live_event_liste(id=b["order"], event_navn=b["event_name"], heat=b["run"], mode=b["mode"]))

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
    



@app.route('/event/<year>/<event_name>/<race_type>')
def event_overview(year, event_name, race_type):
    if str(race_type).lower() == "kval":
        race_type = "kvalifisering"

    events, live_event_state = get_event_race_data()

    if str(race_type).lower() == "kvalifisering":
        event_data, table_data, event_date = get_kvali_data(year, event_name, race_type)
        return render_template('event_overview_kval.html', events=events, event_name=event_name, table_data=table_data, event_date=event_date, live_event_state=live_event_state)
    elif str(race_type).lower() == "stige":
        


        event_data, table_data, event_date, manual_entry = get_ladder_data(year, event_name, race_type)
        if manual_entry:
            return render_template('event_overview_finale_manual.html', events=events, event_name=event_name, table_data=table_data, event_date=event_date, live_event_state=live_event_state)
        else:
            return render_template('event_overview_stige.html', events=events, event_name=event_name, event_data=event_data, table_data=table_data, event_date=event_date, live_event_state=live_event_state)
    
    elif str(race_type).lower() == "finale":
        table_data, event_date, manual_entry = get_finale(year, event_name, race_type)
        if manual_entry:
            return render_template('event_overview_finale_manual.html', events=events, event_name=event_name, table_data=table_data, event_date=event_date, live_event_state=live_event_state)
        else:
            return render_template('event_overview_finale.html', events=events, event_name=event_name, table_data=table_data, event_date=event_date, live_event_state=live_event_state)

@app.route('/hall-of-fame')
def hall_of_fame():
    from utils.utils import get_top_drivers_stige, get_top_drivers_finale
    name = request.args.get('name')


    events, live_event_state = get_event_race_data()

    stige_points=get_top_drivers_stige(name)
    finale_points=get_top_drivers_finale(name)

    if name != None:
        return render_template('driver_scores.html', events=events, live_event_state=live_event_state,
                                                    stige_points=stige_points, finale_points=finale_points)


    return render_template('hall_of_fame.html', events=events, live_event_state=live_event_state,
                                                stige_points=stige_points, finale_points=finale_points)

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
    
    events, live_event_state = get_event_race_data()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
       
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user_id'] = 1
            return redirect("/admin")
            
        flash('Invalid credentials')
        return redirect("/login")
        
    return render_template('login.html', events=events, live_event_state=live_event_state)

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
        displayquali = bool(data.get("displayqualiCheckbox"))

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
            realtime_state.display_quali = displayquali



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
        
        try:
            if realtime_state.display_quali == False:
                quli_state = ""
            else:
                quli_state = "checked"
        except:
            quli_state = "checked"

        event = {
            'name': realtime_state.active_event if realtime_state else '',
            'visibility': realtime_state.active_race_state if realtime_state else 0,
            'display_quali': quli_state,
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
        
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-data/", methods=['POST'])
def upload_data():
    from models import RaceClasses
    data = request.json
    class_types = []
    class_list = {
            "700 Stock":["700 Stock","600","600 Stock","650 Stock","650 Stock (NM)","650 Stock-","700 Stock"],
            "900 Stock":["900 Stock","800","850 Stock","900 Stock","900 Stock (NM)","900 Stock NM"],
            "2-Takt Turbo Modified":[],
            "Bakkecross Pro Stock 600":[],
            "Bakkecross Semi Pro Stock":[],
            "Women 900 Stock":["Women 900 Stock","Dame (Max 850cc)","Damer","Damer (850 Stock)","Damer (Maks 850cc)","Damer 2-Takt Turbo Modified","Women 900 Stock"],
            "Women Pro Stock (NM)":[],
            "Millennium Stock":["Millennium Stock","Millenium","Millenium Stock","Millennium (Sittescooter pre 2003)","Millennium Stock"],
            "Millennium Improved Stock":["Millennium Improved Stock"],
            "Pro Stock":["Pro Stock","Pro Stock","Pro Stock NM"],
            "Pro Stock 600":["Pro Stock 600","Pro Stock 600","Pro Stock 600 (NM)"],
            "Rekrutt 11-12":["Rekrutt 11-12","Rekrutt 11-12år"],
            "Rekrutt 13-14":["Rekrutt 13-14","Rekrutt 13-14","Rekrutt 13-14år","Ungdom 12-14 (maks 600cc luft)"],
            "Ungdom 14-16":["Ungdom 14-16år","Rekrutt 13-15","Rekrutt 13-16","Ungdom 13-16","Ungdom 13-16år","Ungdom 14-16","Ungdom 14-16år","Ungdom 14-16år (NM)","Rekrutt 11-16"],
            "Rookie 16-18":["Rookie 16-18 (maks 850cc)","Rookie 16-18år","Rookie","Rookie (Max 850cc)","Rookie 0-850cc (16-20)","Rookie 16-18 (850cc)","Rookie 16-18år","Ungdom (Max 850cc)","Ungdom 16-20 (Max 850cc)","Ungdom 16-20 (max 850cc)"],
            "Top Fuel":["Top Fuel","Top Fuel (NM)","Top Fuel NM"],
            "Trail Unlimited":["Trail Unlimited","Trail Unlimited (NM)"]
        }

    class_strings = ["kval", "finale", "stige", "kvalifisering"]

    with get_db() as db:

        token = request.headers.get("token")
        race_classes = db.query(RaceClasses).all()
        for a in race_classes:
            class_types.append(a.name)

        if use_auth:
            if not check_creds(token):
                return jsonify({"error": "Authentication Failed"}), 401 
        try:
            for event in data:
                event_config = event[0]['race_config']
                event_date = date.fromisoformat(event_config['DATE'])
                event_title = event_config['TITLE_1']
                race_title = event_config['TITLE_2']

                race_title_lst_string = race_title.split()
                if race_title_lst_string[len(race_title_lst_string) - 1].lower() in class_strings:
                    if race_title_lst_string[len(race_title_lst_string) - 2] == "-":
                        class_string = race_title.rsplit(' ', 2)[0]

                        #new_race_class_entry = RaceClasses(name=class_string)
                    else:
                        class_string = race_title.rsplit(' ', 1)[0]
                    for t in class_list:
                        if class_string in class_list[t]:
                            class_string = t
                            f = True
                    if f == False:
                        print(class_string)

                    new_race_class_entry = RaceClasses(name=class_string)

                    if class_string not in class_types:
                        db.add(new_race_class_entry) 
                        class_types.append(class_string)
                else:
                    class_string = "None"

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
                                race_class=class_string
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
    socketio.run(app, 
                 debug=True, 
                 host="192.168.20.218",
                 port=5000,
                )
