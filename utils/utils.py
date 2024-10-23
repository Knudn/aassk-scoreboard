def get_kvali(event=None):
    from app import get_db
    from models import RealTimeData
    from sqlalchemy import func, case, literal_column, or_
    from sqlalchemy.orm import aliased

    with get_db() as db:
        # Subquery to get the best time for each driver
        subq = (
            db.query(
                RealTimeData.driver_name,
                func.min(case(
                    (RealTimeData.penalty == 0, case(
                        (RealTimeData.finishtime > 0, RealTimeData.finishtime),
                        else_=literal_column('999999')
                    )),
                    else_=literal_column('888888')  # Penalty runs
                )).label('best_time'),
                func.min(case((RealTimeData.penalty == 0, 1), else_=0)).label('has_valid_run'),
                func.max(case((RealTimeData.finishtime > 0, 1), else_=0)).label('has_finish_time')
            )
            .filter(RealTimeData.race_title == event)
            .group_by(RealTimeData.driver_name)
            .subquery()
        )

        rtd = aliased(RealTimeData)

        # Main query
        query = (
            db.query(rtd)
            .join(subq, rtd.driver_name == subq.c.driver_name)
            .filter(rtd.race_title == event)
            .filter(
                or_(
                    # Driver has a valid finish time
                    ((subq.c.has_valid_run == 1) & (subq.c.has_finish_time == 1) &
                     (rtd.finishtime == subq.c.best_time) & (rtd.penalty == 0)),
                    # Driver has only penalty runs
                    ((subq.c.has_valid_run == 0) & (rtd.penalty != 0)),
                    # Driver hasn't started (all finishtime == 0 and penalty == 0)
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

def insert_into_database(data):
    pass
