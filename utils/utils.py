from datetime import datetime, timedelta
from sqlalchemy import func, desc
import geoip2.database
from flask import request, session
import time

def get_top_drivers_finale(driver_name=None):
   from app import get_db
   from models import RaceData, ManualEntries
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
       "Trail Unlimited"
   ]
   
   filter_conditions = [RaceData.race_title.ilike('%Finale%'), RaceData.enabled == True]

   if driver_name is not None:
       filter_conditions.append(RaceData.driver_name == driver_name)

   with get_db() as db:
       manual_entrues = db.query(ManualEntries).filter().all()

       if driver_name is not None:
           # For specific driver, get their race results
            result = {}

            for a in manual_entrues:
                man_data = a.to_dict()
                man_event_title = man_data["event_title"]
                man_date = man_data["event_date"]

                for b in man_data["races"]:
                    driver_pos = b["driver_places"]
                    race_title = b["race_title"]
                    if "finale" in race_title.lower():
                        mode = b["mode"]
                        for c in driver_pos:
                            if driver_name in c["driver"] and int(mode) == 3:
                                key = f"{man_date} - {man_event_title} - {race_title}"
                                pos = c["position"]
                                if pos < 4 and pos != 0:
                                    result[key] = {key: 4 - pos}

            unique_races = db.query(
                RaceData.date,
                RaceData.event_title,
                RaceData.race_title
            ).filter(
                *filter_conditions
            ).distinct().all()
           
            for race_date, event_title, race_title in unique_races:
                race_results = db.query(RaceData).filter(
                    RaceData.date == race_date,
                    RaceData.event_title == event_title,
                    RaceData.race_title == race_title,
                    RaceData.penalty == 0,
                    RaceData.finishtime > 0
                ).order_by(
                    RaceData.finishtime
                ).all()
                
                # Convert to dict and sort by finish time
                entries = [entry.to_dict() for entry in race_results]
                sorted_entries = sorted(entries, key=lambda x: x['finishtime'])
                
                # Find position of our driver if they participated
                try:
                    position = next(i for i, entry in enumerate(sorted_entries) if entry['driver_name'] == driver_name)
                    points = 3 if position == 0 else (2 if position == 1 else (1 if position == 2 else 0))
                    
                    key = f"{race_date} - {event_title} - {race_title}"
                    result[key] = {key: points}
                except StopIteration:
                    # Driver didn't participate in this race
                    continue

            # Convert to list and sort by date
            return sorted(result.values(), key=lambda x: list(x.keys())[0])
           
       else:
           # Original logic for all drivers
           unique_races = db.query(
               RaceData.date,
               RaceData.event_title,
               RaceData.race_title
           ).filter(
               *filter_conditions
           ).distinct().all()
           
           points = {}
           
           for race_date, event_title, race_title in unique_races:
               race_results = db.query(RaceData).filter(
                   RaceData.date == race_date,
                   RaceData.event_title == event_title,
                   RaceData.race_title == race_title,
                   RaceData.penalty == 0, 
                   RaceData.finishtime > 0
               ).order_by(
                   RaceData.finishtime
               ).all()
               
               class_results = {}
               for entry in race_results:
                   data_entry = entry.to_dict()
                   race_class = data_entry["race_class"]
                   
                   if race_class not in valid_classes:
                       continue
                   
                   if race_class not in class_results:
                       class_results[race_class] = []
                   
                   class_results[race_class].append(data_entry)
               
               for race_class, entries in class_results.items():
                   sorted_entries = sorted(entries, key=lambda x: x['finishtime'])
                   
                   if race_class not in points:
                       points[race_class] = {}
                   
                   for position, entry in enumerate(sorted_entries[:3]):
                       driver_name = entry['driver_name']
                       
                       
                       if driver_name not in points[race_class]:
                           points[race_class][driver_name] = {
                               'total_points': 0,
                               'first_places': 0,
                               'second_places': 0,
                               'third_places': 0
                           }

                       if position == 0:
                           points[race_class][driver_name]['total_points'] += 3
                           points[race_class][driver_name]['first_places'] += 1
                       elif position == 1:
                           points[race_class][driver_name]['total_points'] += 2
                           points[race_class][driver_name]['second_places'] += 1
                       elif position == 2:
                           points[race_class][driver_name]['total_points'] += 1
                           points[race_class][driver_name]['third_places'] += 1
           
           return points

def get_top_drivers_stige(driver_name=None):
    from app import get_db
    from models import RaceData, ManualEntries
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
        "Trail Unlimited"
    ]

    with get_db() as db:
        filter_conditions = [RaceData.race_title.ilike('%Stige%'), RaceData.enabled == True]

#        if driver_name is not None:
#            filter_conditions.append(RaceData.driver_name == driver_name)

        subquery = db.query(
            RaceData.event_title,
            RaceData.race_title,
            func.max(RaceData.heat).label('max_heat')
        ).filter(
            *filter_conditions
        ).group_by(
            RaceData.event_title,
            RaceData.race_title
        ).subquery()

        events = db.query(RaceData).join(
            subquery,
            (RaceData.event_title == subquery.c.event_title) &
            (RaceData.race_title == subquery.c.race_title) &
            (RaceData.heat == subquery.c.max_heat)
        ).all()

        manual_entrues = db.query(ManualEntries).filter().all()

        if driver_name is not None:
            result = {}

            for a in manual_entrues:
                man_data = a.to_dict()
                man_event_title = man_data["event_title"]
                man_date = man_data["event_date"]

                for b in man_data["races"]:
                    driver_pos = b["driver_places"]
                    race_title = b["race_title"]
                    mode = b["mode"]
                    if "stige" in race_title.lower():
                        for c in driver_pos:
                            if driver_name in c["driver"] and int(mode) == 3:
                                key = f"{man_date} - {man_event_title} - {race_title}"
                                pos = c["position"]
                                print(pos, key)
                                if pos < 4 and pos != 0:
                                    result[key] = {key: 4 - pos}
                
            for event in events:
                data_entry = event.to_dict()
                if data_entry["driver_name"] != driver_name:
                    continue
                    
                key = f"{data_entry['date']} - {data_entry['event_title']} - {data_entry['race_title']}"
                points = 0

                if data_entry["pair_id"] == 1:
                    if data_entry["status"] == 1:
                        points = 3
                    elif data_entry["status"] == 2:
                        points = 2
                elif data_entry["pair_id"] == 2:
                    if data_entry["status"] == 1:
                        points = 1

                result[key] = {key: points}

            return sorted(result.values(), key=lambda x: list(x.keys())[0])

        man_point = {}
        points = {}

        for a in manual_entrues:
            man_data = a.to_dict()
            man_event_title = man_data["event_title"]
            man_date = man_data["event_date"]
            for b in man_data["races"]:

                if "stige" in b["race_title"].lower():
                    driver_pos = b["driver_places"]
                    race_title = b["race_title"]
                    race_class = race_title.replace(" - Stige", "")
                    race_class = race_class.replace(" -Stige", "")

                    for entry in b["driver_places"]:
                        driver_name = entry["driver"]
                        points_man = entry["position"]

                        if race_class not in points:
                            points[race_class] = {}
                        
                        if driver_name not in points[race_class]:
                            points[race_class][driver_name] = {
                                'total_points': 0,
                                'first_places': 0,
                                'second_places': 0,
                                'third_places': 0
                            }

                        if points_man == 1:
                            if driver_name == "Jon Atle Helle":
                                print(driver_name, man_event_title, man_date, "dddddd")
                            points[race_class][driver_name]['total_points'] += 3
                            points[race_class][driver_name]['first_places'] += 1

                        elif points_man == 2:
                            points[race_class][driver_name]['total_points'] += 2
                            points[race_class][driver_name]['second_places'] += 1

                        if points_man == 3:

                            points[race_class][driver_name]['total_points'] += 1
                            points[race_class][driver_name]['third_places'] += 1


        for a in events:
            data_entry = a.to_dict()
            race_class = data_entry["race_class"]
            race_title = data_entry["event_title"]

            driver_name = data_entry["driver_name"]
            
            if race_class == "Rookie: 0-850ccm (16-20)":
                race_class = "Rookie 16-18"
            elif race_class == "Rookie 16-18 (850 Stock)":
                race_class = "Rookie 16-18"

            if race_class not in points:
                points[race_class] = {}
            
            if driver_name not in points[race_class]:
                points[race_class][driver_name] = {
                    'total_points': 0,
                    'first_places': 0,
                    'second_places': 0,
                    'third_places': 0
                }
            
            if data_entry["pair_id"] == 1:
                if data_entry["status"] == 1:
                    points[race_class][driver_name]['total_points'] += 3
                    points[race_class][driver_name]['first_places'] += 1
                elif data_entry["status"] == 2:

                    points[race_class][driver_name]['total_points'] += 2
                    points[race_class][driver_name]['second_places'] += 1
            elif data_entry["pair_id"] == 2:
                if data_entry["status"] == 1:
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




