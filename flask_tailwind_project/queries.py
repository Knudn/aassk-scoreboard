
from sqlalchemy import func, and_, not_
from sqlalchemy.orm import aliased
from models import RaceData

def get_all_drivers():
    return "select driver_name from race_data;"


def get_single_placement_sqlalchemy(session, driver):
    # Create an alias for self-joining
    RD = aliased(RaceData)

    # Subquery
    subquery = (
        session.query(
            RD.date.label('race_date'),
            (RD.event_title + ' - ' + RD.race_title).label('full_race_title'),
            RD.id.label('race_id'),
            RD.driver_name,
            RD.vehicle,
            RD.finishtime,
            func.rank().over(
                partition_by=RD.date,
                order_by=RD.finishtime
            ).label('placement'),
            func.count().over(
                partition_by=RD.date
            ).label('total_drivers')
        )
        .filter(and_(
            RD.mode == 0,
            RD.finishtime > 0,
            RD.penalty == 0
        ))
        .subquery()
    )

    # Main query
    query = (
        session.query(
            subquery.c.race_date,
            subquery.c.full_race_title,
            subquery.c.race_id,
            subquery.c.driver_name,
            subquery.c.vehicle,
            subquery.c.finishtime,
            subquery.c.placement,
            subquery.c.total_drivers
        )
        .filter(
            subquery.c.driver_name == driver,
        )
        .order_by(
            subquery.c.race_date,
            subquery.c.race_id,
            subquery.c.finishtime
        )
    )

    # Execute the query and return the results
    results = query.all()
    return results

def get_ladder_results():
    return """
WITH FinalResults AS (
    SELECT 
        r.race_id,
        MAX(r.run_id) AS last_pair_id,
        MAX(r.pair_id) AS last_run_id
    FROM 
        run r
    JOIN 
        races ra ON r.race_id = ra.id
    WHERE 
        ra.mode = 3
    GROUP BY 
        r.race_id
),
Thirdplace AS (
    SELECT 
        r.race_id,
        d.first_name || ' ' || d.last_name AS winner,
        '3' AS position,
        rd.title || ' - ' || ra.title AS race_name
    FROM 
        run r
    JOIN 
        FinalResults fr ON r.race_id = fr.race_id AND r.run_id = fr.last_run_id AND r.pair_id = fr.last_pair_id
    JOIN 
        drivers d ON r.driver_id = d.id
    JOIN 
        races ra ON r.race_id = ra.id
    JOIN 
        racedays rd ON ra.raceday_id = rd.id
    WHERE 
        r.status = 1
),
FourthPlace AS (
    SELECT 
        r.race_id,
        d.first_name || ' ' || d.last_name AS runner_up,
        '4' AS position,
        rd.title || ' - ' || ra.title AS race_name
    FROM 
        run r
    JOIN 
        FinalResults fr ON r.race_id = fr.race_id AND r.run_id = fr.last_run_id AND r.pair_id = fr.last_pair_id
    JOIN 
        drivers d ON r.driver_id = d.id
    JOIN 
        races ra ON r.race_id = ra.id
    JOIN 
        racedays rd ON ra.raceday_id = rd.id
    WHERE 
        r.status = 2
),
FirstAndSecond AS (
    SELECT 
        r.race_id,
        d.first_name || ' ' || d.last_name AS driver,
        CASE
            WHEN r.status = 1 THEN '1'
            ELSE '2'
        END AS position,
        rd.title || ' - ' || ra.title AS race_name
    FROM 
        run r
    JOIN 
        FinalResults fr ON r.race_id = fr.race_id AND r.run_id = fr.last_run_id AND r.pair_id = fr.last_pair_id - 1
    JOIN 
        drivers d ON r.driver_id = d.id
    JOIN 
        races ra ON r.race_id = ra.id
    JOIN 
        racedays rd ON ra.raceday_id = rd.id
    WHERE 
        ra.mode = 3
)


SELECT * FROM Thirdplace
UNION ALL
SELECT * FROM FourthPlace
UNION ALL
SELECT * FROM FirstAndSecond
ORDER BY race_id, position;

    """

def get_parallel_driver_results_sql(driver):
    return """SELECT 
    d1.name,
    d2.name,
    CASE 
        WHEN r1.status = 1 THEN 'Winner'
        WHEN r1.status = 2 THEN 'Loser'
        ELSE 'Unknown'
    END as result_driver1,
    CASE 
        WHEN r2.status = 1 THEN 'Winner'
        WHEN r2.status = 2 THEN 'Loser'
        ELSE 'Unknown'
    END as result_driver2,
	rd.title AS race_day,
    ra.title AS race_title,
    rd.date AS race_date,
	r1.finishtime AS d1_finishtime,
	r2.finishtime AS d2_finishtime,
	r1.vehicle AS d1_snowmobile,
	r2.vehicle AS d2_snowmobile
FROM 
    run r1
JOIN 
    drivers d1 ON r1.driver_id = d1.id
LEFT JOIN 
    run r2 ON r1.race_id = r2.race_id AND r1.run_id = r2.run_id AND r1.pair_id = r2.pair_id AND r1.driver_id != r2.driver_id
LEFT JOIN 
    drivers d2 ON r2.driver_id = d2.id
JOIN 
    races ra ON r1.race_id = ra.id
JOIN 
    racedays rd ON ra.raceday_id = rd.id
WHERE 
    (d1.name = '{0}')
    AND ((ra.mode IN (2, 3) AND r2.id IS NOT NULL))
ORDER BY 
    rd.date, ra.title, r1.run_id, r1.pair_id;""".format(driver)



def get_snowmobiles_sql(driver):
    return """
        SELECT DISTINCT d.name, r.vehicle, rd.date, rd.title
        FROM drivers d
        JOIN run r ON d.id = r.driver_id
        JOIN races ra ON r.race_id = ra.id
        JOIN racedays rd ON ra.raceday_id = rd.id
        WHERE d.name = '{0}' AND r.vehicle <> '';
    """.format(driver)

def get_race_entries_for_driver(driver):
    return """
SELECT 
    r.id AS race_id, 
    r.title AS race_title, 
    rd.id AS raceday_id, 
    rd.title AS raceday_title, 
    ru.pair_id,
    ru.driver_id, 
    d.name AS driver_name,
    ru.finishtime,
    ru.penalty,
    ru.run_id,
    ru.pair_id,
    ru.vehicle,
    rd.date

FROM races r
JOIN run ru ON r.id = ru.race_id
JOIN drivers d ON ru.driver_id = d.id
JOIN racedays rd ON r.raceday_id = rd.id
WHERE r.id IN (
    SELECT race_id 
    FROM run 
    WHERE driver_id = (
        SELECT id 
        FROM drivers 
        WHERE name = '{0}'
    )
) and r.mode = 3
ORDER BY r.id, ru.pair_id, ru.finishtime;

""".format(driver)


def get_single_placement_sql(driver):
    return """
SELECT 
    sub.race_date,
    sub.full_race_title,
    sub.race_id,
    sub.driver_name,
    sub.vehicle,
    sub.finishtime,
    sub.placement,
    sub.total_drivers
FROM 
    (SELECT 
        rd.date AS race_date,
        rd.title || ' - ' || r.title AS full_race_title,
        r.id AS race_id,
        d.name AS driver_name,
        ru.vehicle,
        ru.finishtime,
        RANK() OVER (PARTITION BY ru.race_id ORDER BY ru.finishtime ASC) as placement,
        COUNT(*) OVER (PARTITION BY ru.race_id) as total_drivers
    FROM 
        racedays rd
    INNER JOIN 
        races r ON rd.id = r.raceday_id
    INNER JOIN 
        run ru ON r.id = ru.race_id
    INNER JOIN 
        drivers d ON ru.driver_id = d.id
    WHERE 
        r.mode = 0 AND 
        ru.finishtime > 0 AND 
        ru.penalty = 0) sub
WHERE 
    sub.driver_name = '{0}' AND 
	sub.full_race_title NOT LIKE '%Kval%'
ORDER BY 
    sub.race_date, sub.race_id, sub.finishtime;
        """.format(driver)





