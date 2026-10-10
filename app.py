from flask import Flask, render_template, request, jsonify
from datetime import datetime, date, timedelta
from pathlib import Path
import sqlite3, os

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('DATABASE_PATH', str(BASE / 'wild_within.db')))
if DB_PATH.is_dir(): DB_PATH = DB_PATH / 'wild_within.db'
app = Flask(__name__)

def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, activity_date TEXT NOT NULL, distance_km REAL NOT NULL, duration_seconds INTEGER NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS activities (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Wellness', target_minutes INTEGER NOT NULL DEFAULT 10, completed_date TEXT)''')
        con.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, body TEXT NOT NULL, distance_km REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS experiments (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, category TEXT NOT NULL, cue TEXT NOT NULL DEFAULT '', tiny_version TEXT NOT NULL DEFAULT '', hypothesis TEXT NOT NULL DEFAULT '', metric TEXT NOT NULL DEFAULT 'days completed', duration_days INTEGER NOT NULL DEFAULT 14, start_date TEXT NOT NULL, created_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)''')
        con.execute('''CREATE TABLE IF NOT EXISTS experiment_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id INTEGER NOT NULL, log_date TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, mood INTEGER, note TEXT NOT NULL DEFAULT '', UNIQUE(experiment_id, log_date))''')
        if con.execute('SELECT COUNT(*) FROM activities').fetchone()[0] == 0:
            con.executemany('INSERT INTO activities(title,category,target_minutes) VALUES(?,?,?)', [('Morning movement','Fitness',15),('Drink water mindfully','Nutrition',2),('Read 5 pages','Learning',10),('Evening reset','Mindfulness',5)])
        if con.execute('SELECT COUNT(*) FROM experiments').fetchone()[0] == 0:
            con.execute('INSERT INTO experiments(title,category,cue,tiny_version,hypothesis,metric,duration_days,start_date,created_at) VALUES(?,?,?,?,?,?,?,?,?)', ('The 5-minute start','Fitness','After I brush my teeth','Put on shoes and walk for 5 minutes','Making the first step tiny will make movement easier to begin.','days completed',14,date.today().isoformat(),datetime.now().isoformat(timespec='seconds')))
        if con.execute('SELECT COUNT(*) FROM posts').fetchone()[0] == 0:
            con.execute('INSERT INTO posts(username,body,distance_km,created_at) VALUES(?,?,?,?)', ('TrailFriend','First steps toward the summit. Progress is built one small repeat at a time.',1.5,datetime.now().isoformat(timespec='minutes')))

def habit_data(con):
    experiments = con.execute('SELECT * FROM experiments WHERE active=1 ORDER BY id DESC').fetchall()
    result=[]
    for e in experiments:
        logs=con.execute('SELECT * FROM experiment_logs WHERE experiment_id=? ORDER BY log_date DESC',(e['id'],)).fetchall()
        completed=sum(1 for l in logs if l['completed'])
        days=max(1,min(e['duration_days'],(date.today()-date.fromisoformat(e['start_date'])).days+1))
        result.append(dict(e)|{'logs':logs,'completed':completed,'days_elapsed':days,'rate':round(completed/days*100)})
    return result

@app.get('/')
def home():
    today=date.today().isoformat()
    with db() as con:
        activities=con.execute('SELECT * FROM activities ORDER BY id DESC').fetchall()
        posts=con.execute('SELECT * FROM posts ORDER BY id DESC LIMIT 8').fetchall()
        runs=con.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 8').fetchall()
        today_km=con.execute('SELECT COALESCE(SUM(distance_km),0) FROM runs WHERE activity_date=?',(today,)).fetchone()[0]
        month_km=con.execute('SELECT COALESCE(SUM(distance_km),0) FROM runs WHERE substr(activity_date,1,7)=?',(date.today().strftime('%Y-%m'),)).fetchone()[0]
        done=con.execute('SELECT COUNT(*) FROM activities WHERE completed_date=?',(today,)).fetchone()[0]
        total=len(activities)
        experiments=habit_data(con)
        logs=con.execute('SELECT log_date, COUNT(*) AS n FROM experiment_logs WHERE completed=1 AND log_date>=? GROUP BY log_date ORDER BY log_date',( (date.today()-timedelta(days=6)).isoformat(),)).fetchall()
    return render_template('index.html',activities=activities,posts=posts,runs=runs,today=today,today_km=round(today_km,2),month_km=round(month_km,2),done=done,total=total,experiments=experiments,week_logs={r['log_date']:r['n'] for r in logs},now=datetime.now())

@app.post('/api/activity')
def add_activity():
    d=request.get_json(silent=True) or {}; title=str(d.get('title','')).strip()[:80]; category=str(d.get('category','Wellness')).strip()[:30]
    try: minutes=int(d.get('minutes',10))
    except (TypeError,ValueError): return jsonify(error='Minutes must be a number'),400
    if not title or not 1<=minutes<=1440:return jsonify(error='Enter a name and duration from 1 to 1440 minutes.'),400
    with db() as con: con.execute('INSERT INTO activities(title,category,target_minutes) VALUES(?,?,?)',(title,category or 'Wellness',minutes))
    return jsonify(ok=True)

@app.post('/api/activity/<int:aid>/complete')
def complete_activity(aid):
    with db() as con:
        if not con.execute('SELECT id FROM activities WHERE id=?',(aid,)).fetchone():return jsonify(error='Activity not found'),404
        row=con.execute('SELECT completed_date FROM activities WHERE id=?',(aid,)).fetchone()
        con.execute('UPDATE activities SET completed_date=? WHERE id=?',(None if row['completed_date']==date.today().isoformat() else date.today().isoformat(),aid))
    return jsonify(ok=True)

@app.post('/api/experiment')
def add_experiment():
    d=request.get_json(silent=True) or {}; title=str(d.get('title','')).strip()[:100]; category=str(d.get('category','Wellness')).strip()[:30]
    try: days=int(d.get('duration_days',14))
    except (TypeError,ValueError): return jsonify(error='Duration must be a number'),400
    if not title or not 3<=days<=90:return jsonify(error='Give the experiment a name and choose 3–90 days.'),400
    with db() as con:
        cur=con.execute('INSERT INTO experiments(title,category,cue,tiny_version,hypothesis,metric,duration_days,start_date,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(title,category,str(d.get('cue','')).strip()[:180],str(d.get('tiny_version','')).strip()[:180],str(d.get('hypothesis','')).strip()[:300],str(d.get('metric','days completed')).strip()[:60],days,date.today().isoformat(),datetime.now().isoformat(timespec='seconds')))
        eid=cur.lastrowid
    return jsonify(ok=True,id=eid)

@app.post('/api/experiment/<int:eid>/log')
def log_experiment(eid):
    d=request.get_json(silent=True) or {}; completed=1 if d.get('completed') else 0; note=str(d.get('note','')).strip()[:500]
    try: mood=int(d.get('mood',0)); mood=mood if 1<=mood<=5 else None
    except (TypeError,ValueError): mood=None
    log_date=str(d.get('date',date.today().isoformat()))
    try: date.fromisoformat(log_date)
    except ValueError: return jsonify(error='Invalid date'),400
    with db() as con:
        if not con.execute('SELECT id FROM experiments WHERE id=?',(eid,)).fetchone():return jsonify(error='Experiment not found'),404
        con.execute('INSERT INTO experiment_logs(experiment_id,log_date,completed,mood,note) VALUES(?,?,?,?,?) ON CONFLICT(experiment_id,log_date) DO UPDATE SET completed=excluded.completed,mood=excluded.mood,note=excluded.note',(eid,log_date,completed,mood,note))
    return jsonify(ok=True)

@app.post('/api/run')
def save_run():
    d=request.get_json(silent=True) or {}
    try: distance=float(d.get('distance_km',0)); duration=int(d.get('duration_seconds',0)); source=str(d.get('source','gps'))[:20]
    except (TypeError,ValueError):return jsonify(error='Invalid run values'),400
    if not .01<=distance<=200 or not 0<=duration<=86400:return jsonify(error='Distance or duration is outside the allowed range'),400
    with db() as con:con.execute('INSERT INTO runs(activity_date,distance_km,duration_seconds,source,created_at) VALUES(?,?,?,?,?)',(date.today().isoformat(),distance,duration,source,datetime.now().isoformat(timespec='seconds')))
    return jsonify(ok=True,distance_km=round(distance,2),virtual_distance_km=round(distance,2),message=f'{distance:.2f} km added to your journey.')

@app.post('/api/post')
def create_post():
    d=request.get_json(silent=True) or {}; username=str(d.get('username','TrailSeeker')).strip()[:30] or 'TrailSeeker'; body=str(d.get('body','')).strip()[:500]
    try:distance=max(0,min(200,float(d.get('distance_km',0))))
    except (TypeError,ValueError):distance=0
    if not body:return jsonify(error='Write something before sharing.'),400
    with db() as con:con.execute('INSERT INTO posts(username,body,distance_km,created_at) VALUES(?,?,?,?)',(username,body,distance,datetime.now().isoformat(timespec='minutes')))
    return jsonify(ok=True)

@app.get('/health')
def health():return jsonify(status='ok',app='WILD WITHIN')

init_db()
if __name__=='__main__':app.run(host='127.0.0.1',port=5055,debug=False)
