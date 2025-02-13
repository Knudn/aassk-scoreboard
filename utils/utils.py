from datetime import datetime, timedelta
from sqlalchemy import func, desc
import geoip2.database
from flask import request, session
import time

def get_top_drivers_finale():
    from app import get_db
    from models import RaceData
    from sqlalchemy import func
    
    valid_classes = [
        "700 Stock",
        "900 Stock",
        "Pro Stock",
        "Pro Stock 600",
        "Rekrutt 11-12",
        "Rekrutt 13-14",
        "Ungdom 14-16",
        "Women 900 Stock",
        "Millennium Stock",
        "Rookie 16-18",
        "900 Stock",
        "2-Takt Turbo Modified",
        "Top Fuel",
        "Millennium Improved Stock",
    ]
    
    with get_db() as db:
        # Get all unique combinations of date, event_title, and race_title
        unique_races = db.query(
            RaceData.date,
            RaceData.event_title,
            RaceData.race_title
        ).filter(
            RaceData.race_title.ilike('%Finale%')
        ).distinct().all()
        
        points = {}
        
        # Process each unique race
        for race_date, event_title, race_title in unique_races:
            # Get all valid runs for this specific race, ordered by finish time
            race_results = db.query(RaceData).filter(
                RaceData.date == race_date,
                RaceData.event_title == event_title,
                RaceData.race_title == race_title,
                RaceData.penalty == 0,  # Only runs without penalties
                RaceData.finishtime > 0  # Ensure valid finish times
            ).order_by(
                RaceData.finishtime
            ).all()
            
            # Group results by race class
            class_results = {}
            for entry in race_results:
                data_entry = entry.to_dict()
                race_class = data_entry["race_class"]
                
                # Handle special case for Millenium
                if race_class == "Millenium":
                    race_class = "Millenium Stock"
                
                # Handle NM cases
                if "NM" in race_class:
                    race_class = race_class.split("NM")[0][:-1]
                    if race_class[-1] == " ":
                        race_class = race_class[:-1]
                
                if race_class not in valid_classes:
                    continue
                
                if race_class not in class_results:
                    class_results[race_class] = []
                
                class_results[race_class].append(data_entry)
            
            # Process each race class
            for race_class, entries in class_results.items():
                # Sort entries by finish time
                sorted_entries = sorted(entries, key=lambda x: x['finishtime'])
                
                # Initialize race class in points dict if needed
                if race_class not in points:
                    points[race_class] = {}
                
                # Award points to top 3 finishers
                for position, entry in enumerate(sorted_entries[:3]):
                    driver_name = entry['driver_name']
                    
                    # Initialize driver if not exists
                    if driver_name not in points[race_class]:
                        points[race_class][driver_name] = {
                            'total_points': 0,
                            'first_places': 0,
                            'second_places': 0,
                            'third_places': 0
                        }
                    
                    # Award points based on position
                    if position == 0:  # First place
                        points[race_class][driver_name]['total_points'] += 3
                        points[race_class][driver_name]['first_places'] += 1
                    elif position == 1:  # Second place
                        points[race_class][driver_name]['total_points'] += 2
                        points[race_class][driver_name]['second_places'] += 1
                    elif position == 2:  # Third place
                        points[race_class][driver_name]['total_points'] += 1
                        points[race_class][driver_name]['third_places'] += 1
        
        return points

def get_top_drivers_stige():
    from app import get_db
    from models import RaceData
    from sqlalchemy import func




    valid_classes = [
        "700 Stock",
        "900 Stock",
        "Pro Stock",
        "Pro Stock 600",
        "Rekrutt 11-12",
        "Rekrutt 13-14",
        "Ungdom 14-16",
        "Women 900 Stock",
        "Millennium Stock",
        "Rookie 16-18",
        "900 Stock",
        "2-Takt Turbo Modified",
        "Top Fuel",
        "Millennium Improved Stock",
    ]
    
    with get_db() as db:
        # Modified subquery to include event_title
        subquery = db.query(
            RaceData.event_title,
            RaceData.race_title,
            func.max(RaceData.heat).label('max_heat')
        ).filter(
            RaceData.race_title.ilike('%Stige%')
        ).group_by(
            RaceData.event_title,
            RaceData.race_title
        ).subquery()

        # Modified join condition to include event_title
        events = db.query(RaceData).join(
            subquery,
            (RaceData.event_title == subquery.c.event_title) &
            (RaceData.race_title == subquery.c.race_title) &
            (RaceData.heat == subquery.c.max_heat)
        ).all()

        points = {}

        for a in events:
            data_entry = a.to_dict()
            race_class = data_entry["race_class"]

            print(race_class)
            driver_name = data_entry["driver_name"]
            if race_class not in valid_classes:
                continue

            # Initialize race class if not exists
            if race_class not in points:
                points[race_class] = {}
            
            # Initialize driver if not exists
            if driver_name not in points[race_class]:
                points[race_class][driver_name] = {
                    'total_points': 0,
                    'first_places': 0,
                    'second_places': 0,
                    'third_places': 0
                }
            
            if data_entry["pair_id"] == 1:
                if data_entry["status"] == 1:
                    # First place
                    points[race_class][driver_name]['total_points'] += 3
                    points[race_class][driver_name]['first_places'] += 1
                elif data_entry["status"] == 2:
                    # Second place
                    points[race_class][driver_name]['total_points'] += 2
                    points[race_class][driver_name]['second_places'] += 1
            elif data_entry["pair_id"] == 2:
                if data_entry["status"] == 1:
                    # Third place
                    points[race_class][driver_name]['total_points'] += 1
                    points[race_class][driver_name]['third_places'] += 1

        return points
            

def get_kvali(event=None):
    from app import get_db
    
    from models import RealTimeData
    from sqlalchemy import func, case, literal_column, or_
    from sqlalchemy.orm import aliased

    with get_db() as db:
        subq = (
            db.query(
                RealTimeData.driver_name,
                func.min(case(
                    (RealTimeData.penalty == 0, case(
                        (RealTimeData.finishtime > 0, RealTimeData.finishtime),
                        else_=literal_column('999999')
                    )),
                    else_=literal_column('888888')
                )).label('best_time'),
                func.min(case((RealTimeData.penalty == 0, 1), else_=0)).label('has_valid_run'),
                func.max(case((RealTimeData.finishtime > 0, 1), else_=0)).label('has_finish_time')
            )
            .filter(RealTimeData.race_title == event)
            .group_by(RealTimeData.driver_name)
            .subquery()
        )

        rtd = aliased(RealTimeData)

        query = (
            db.query(rtd)
            .join(subq, rtd.driver_name == subq.c.driver_name)
            .filter(rtd.race_title == event)
            .filter(
                or_(
                    ((subq.c.has_valid_run == 1) & (subq.c.has_finish_time == 1) &
                     (rtd.finishtime == subq.c.best_time) & (rtd.penalty == 0)),
                    ((subq.c.has_valid_run == 0) & (rtd.penalty != 0)),
                    ((subq.c.has_valid_run == 1) & (subq.c.has_finish_time == 0))
                )
            )
            .order_by(
                case(
                    (subq.c.has_valid_run == 1, 1),
                    (subq.c.has_valid_run == 0, 2),
                    else_=3
                ),
                rtd.finishtime
            )
        )

    data = query.all()

    best_time_results = []
    for i in data:
        best_time_results.append(i.to_dict())

    return best_time_results


def get_finale_live(event_name):
    from models import RealTimeData
    from app import get_db

    entry_data = None

    with get_db() as db:
        event_data = (
            db.query(RealTimeData)
            .filter(
                RealTimeData.race_title == event_name
            )
            .order_by(
                RealTimeData.penalty != 0,
                RealTimeData.finishtime == 0,
                RealTimeData.finishtime
            )
            .all()
        )
        table_data = []
        for i in event_data:
            table_data.append(i.to_dict())

        return table_data


def fix_names(first_name, last_name, club):
    if "é" in first_name:
        first_name = first_name.replace('é', 'e')

    if "é" in last_name:
        last_name = first_name.replace('é', 'e')

    if "Throsland" in last_name and "Vilde" in first_name:
        first_name = "Vilde"
        last_name = "Thorsland Lauen"

    if "Vilde Thorsland" in first_name:
        first_name = "Vilde"
        last_name = "Thorsland Lauen"
    
    if "Yngve" in first_name and "Ousdal" in last_name:
        first_name = "Yngve"
        last_name = "Ousdal"
    
    if "Sigurd S" in first_name:
        first_name = "Sigurd Selmer"

    if first_name == "Ole B":
        first_name = "Ole Bjørnestad"

    if last_name == "Håvorstad":
        last_name = "Håverstad"

    if first_name == "Maja Alexandra":
        first_name = "Maja Alexandra Egelandsdal" 
    
    if "Live Sunniva" in first_name:
        club = "Kongsberg & Numedal SNK"
    
    if first_name == "Fredrik Åsland":
        first_name = "Fredrik"
        last_name = "Åsland"
    
    if first_name == "Bjørnar" and last_name == "Bjørnestad":
        first_name = "Bjørnar Kongevold"
    
    if first_name == "Eline Åsland" and last_name == "Thorsland":
        first_name = "Eline"
        last_name = "Åsland Thorsland"
    
    if first_name == "Jørund" and last_name == "Åsland":
        first_name = "Jørund Haugland"
    if last_name == "Skeiebrok":
        last_name = "Skeibrok"

    if first_name == "Live Sunniva":
        club="Kongsberg & Numedal SNK"

    if first_name == "Live Sunniva ":
        first_name="Live Sunniva"

    if first_name == "Madelen E":
        first_name = "Madelen Egelandsdal"

    if first_name == "Preben" and last_name == "Knabenes":
        first_name = "Preben Bjørnestad"
        last_name = "Knabenes"

    name = first_name + " " + last_name 
    return name, club




