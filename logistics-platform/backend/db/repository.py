"""Data-access functions: SQL in, plain dicts out."""

LOC_COLS = ("code", "name", "country", "kind", "lat", "lon", "packages")
ROUTE_COLS = ("src", "dst", "mode", "distance_km", "cost_usd", "time_hours", "weekly_trips", "note")


def _d(row):
    return dict(row) if row else None


def list_networks(conn):
    rows = conn.execute(
        "SELECT n.*, (SELECT COUNT(*) FROM locations WHERE network_id=n.id) AS locations, "
        "(SELECT COUNT(*) FROM routes WHERE network_id=n.id) AS routes FROM networks n ORDER BY n.id")
    return [dict(r) for r in rows]


def get_network(conn, network_id):
    return _d(conn.execute("SELECT * FROM networks WHERE id=?", (network_id,)).fetchone())


def get_network_by_key(conn, key):
    return _d(conn.execute("SELECT * FROM networks WHERE key=?", (key,)).fetchone())


def create_network(conn, key, name, description, scenario, builtin, default_metric):
    cur = conn.execute(
        "INSERT INTO networks (key,name,description,scenario,builtin,default_metric) VALUES (?,?,?,?,?,?)",
        (key, name, description, scenario, int(builtin), default_metric))
    return cur.lastrowid


def delete_network(conn, network_id):
    conn.execute("DELETE FROM networks WHERE id=?", (network_id,))
    conn.execute("DELETE FROM runs WHERE network_id=?", (network_id,))


def clear_network(conn, network_id):
    conn.execute("DELETE FROM locations WHERE network_id=?", (network_id,))
    conn.execute("DELETE FROM routes WHERE network_id=?", (network_id,))
    conn.execute("DELETE FROM runs WHERE network_id=?", (network_id,))


def list_locations(conn, network_id):
    return [dict(r) for r in conn.execute(
        "SELECT id,network_id,code,name,country,kind,lat,lon,packages FROM locations "
        "WHERE network_id=? ORDER BY code", (network_id,))]


def get_location(conn, loc_id):
    return _d(conn.execute("SELECT * FROM locations WHERE id=?", (loc_id,)).fetchone())


def insert_locations(conn, network_id, locs):
    conn.executemany(
        f"INSERT INTO locations (network_id,{','.join(LOC_COLS)}) VALUES (?,{','.join('?' * len(LOC_COLS))})",
        [(network_id, *[l[c] for c in LOC_COLS]) for l in locs])


def update_location(conn, loc_id, fields):
    sets = ",".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE locations SET {sets} WHERE id=?", (*fields.values(), loc_id))


def delete_location(conn, loc):
    conn.execute("DELETE FROM routes WHERE network_id=? AND (src=? OR dst=?)",
                 (loc["network_id"], loc["code"], loc["code"]))
    conn.execute("DELETE FROM locations WHERE id=?", (loc["id"],))


def list_routes(conn, network_id):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM routes WHERE network_id=? ORDER BY src,dst", (network_id,))]


def get_route(conn, route_id):
    return _d(conn.execute("SELECT * FROM routes WHERE id=?", (route_id,)).fetchone())


def get_route_pair(conn, network_id, src, dst):
    return _d(conn.execute("SELECT * FROM routes WHERE network_id=? AND src=? AND dst=?",
                           (network_id, src, dst)).fetchone())


def insert_routes(conn, network_id, routes):
    conn.executemany(
        f"INSERT INTO routes (network_id,{','.join(ROUTE_COLS)}) VALUES (?,{','.join('?' * len(ROUTE_COLS))})",
        [(network_id, *[r.get(c, "" if c == "note" else None) for c in ROUTE_COLS]) for r in routes])


def update_route(conn, route_id, fields):
    sets = ",".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE routes SET {sets} WHERE id=?", (*fields.values(), route_id))


def delete_route(conn, route_id):
    conn.execute("DELETE FROM routes WHERE id=?", (route_id,))


def log_run(conn, network_id, algorithm, metric, source, target, status, total, stats):
    conn.execute(
        "INSERT INTO runs (network_id,algorithm,metric,source,target,status,total,time_ms,relaxations,iterations)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (network_id, algorithm, metric, source, target, status, total,
         stats.get("time_ms"), stats.get("relaxations"), stats.get("iterations")))


def run_summary(conn, network_id):
    rows = conn.execute(
        "SELECT algorithm, COUNT(*) AS runs, AVG(time_ms) AS avg_time_ms, AVG(relaxations) AS avg_relaxations,"
        " AVG(iterations) AS avg_iterations, SUM(status='negative_cycle') AS cycle_detections"
        " FROM runs WHERE network_id=? GROUP BY algorithm", (network_id,))
    recent = conn.execute("SELECT * FROM runs WHERE network_id=? ORDER BY id DESC LIMIT 12", (network_id,))
    return [dict(r) for r in rows], [dict(r) for r in recent]
