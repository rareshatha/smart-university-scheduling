# ============================================================
# IMPORTS
# ============================================================
import pandas as pd
import numpy as np
import random
import math
import time
import sys
import os
import json
from collections import defaultdict

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in locals() else os.getcwd()

excel_filename = sys.argv[1] if len(sys.argv) > 1 else "Fall 2024 - 2421.xlsx"

possible_path_1 = os.path.normpath(os.path.join(base_dir, 'data', excel_filename))
possible_path_2 = os.path.normpath(os.path.join(base_dir, 'static', 'data', excel_filename))
possible_path_3 = os.path.normpath(os.path.join(os.path.dirname(base_dir), 'data', excel_filename))

if os.path.exists(possible_path_1):
    DATASET_FILE = possible_path_1
elif os.path.exists(possible_path_2):
    DATASET_FILE = possible_path_2
elif os.path.exists(possible_path_3):
    DATASET_FILE = possible_path_3
else:
    DATASET_FILE = possible_path_1

if not os.path.exists(DATASET_FILE):
    print(json.dumps([]))
    sys.exit(0)

try:
    xl = pd.ExcelFile(DATASET_FILE)
    SHEET_NAME = xl.sheet_names[0]
except Exception:
    print(json.dumps([]))
    sys.exit(0)


# ============================================================
# PARSE DATASET
# ============================================================
def parse_xml(file_path):
    df = pd.read_excel(file_path, sheet_name=SHEET_NAME)
    df.columns = [str(c).strip() for c in df.columns]

    if "Class Stat" in df.columns:
        df = df[df["Class Stat"].astype(str).str.upper() == "A"].copy()

    def build_days_pattern(row):
        days = []
        for col in ["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"]:
            val = str(row.get(col, "")).strip().upper()
            if val == "Y":
                days.append("1")
            else:
                days.append("0")
        return "".join(days)

    def university_time_to_minutes(x):
        if pd.isna(x):
            return np.nan
        if hasattr(x, "hour") and hasattr(x, "minute"):
            return int(x.hour * 60 + x.minute)

        s = str(x).strip().lower()
        is_pm = "pm" in s
        is_am = "am" in s
        s = s.replace("am", "").replace("pm", "").strip()

        if ":" in s:
            parts = s.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            if is_pm and hour != 12:
                hour += 12
            if is_am and hour == 12:
                hour = 0
            return int(hour * 60 + minute)

        try:
            val = float(s)
            if 0 <= val < 1:
                return int(round(val * 24 * 60))
            val = int(val)
            hour = val // 100
            minute = val % 100
            return int(hour * 60 + minute)
        except:
            return np.nan

    df["assigned_days"] = df.apply(build_days_pattern, axis=1)
    df["assigned_start"] = df["Mtg Start"].apply(university_time_to_minutes)
    df["assigned_end"] = df["Mtg End"].apply(university_time_to_minutes)
    
    df["assigned_start"] = df["assigned_start"].fillna(480).astype(int)
    df["assigned_end"] = df["assigned_end"].fillna(530).astype(int)
    df["assigned_length"] = df["assigned_end"] - df["assigned_start"]
    df["assigned_room"] = df["Facil ID"].fillna("ONLINE").astype(str).str.strip()

    df["ID_clean"] = df["ID"].fillna("").astype(str).str.strip()
    df["Name_clean"] = df["Name"].fillna("").astype(str).str.strip()

    df["instructor"] = np.where(
        df["ID_clean"] != "",
        df["ID_clean"],
        np.where(df["Name_clean"] != "", df["Name_clean"], "UNKNOWN")
    )
    df["class_id"] = df["Class Nbr"].astype(str).str.strip()

    # Rooms
    rooms = {}
    room_caps = (
        pd.to_numeric(df["Cap Enrl"], errors="coerce")
        .fillna(0)
        .groupby(df["assigned_room"])
        .max()
        .to_dict()
    )
    for room_id, cap in room_caps.items():
        room_id = str(room_id)
        if room_id == "ONLINE":
            rooms[room_id] = {"id": room_id, "capacity": 9999}
        else:
            rooms[room_id] = {"id": room_id, "capacity": int(cap) if cap > 0 else 9999}

    # Instructors
    instructors = {}
    unique_instr_df = df[["instructor", "Name_clean"]].drop_duplicates()
    for _, row in unique_instr_df.iterrows():
        iid = str(row["instructor"])
        instructors[iid] = {
            "id": iid,
            "name": row["Name_clean"] if row["Name_clean"] != "" else iid
        }

    # Time slots
    slot_df = df[["assigned_days", "assigned_start", "assigned_length"]].dropna().drop_duplicates()
    all_time_slots = []
    for _, row in slot_df.iterrows():
        if int(row["assigned_length"]) <= 0:
            continue
        all_time_slots.append({
            "days": str(row["assigned_days"]),
            "start": int(row["assigned_start"]),
            "length": int(row["assigned_length"]),
            "pref": 0.0
        })

    if len(all_time_slots) == 0:
        all_time_slots = [{"days": "1000000", "start": 480, "length": 50, "pref": 0.0}]

    # Classes
    classes = {}
    for _, row in df.iterrows():
        cid = str(row["class_id"])
        tot_enrl = pd.to_numeric(row.get("Tot Enrl", 0), errors="coerce")
        cap_enrl = pd.to_numeric(row.get("Cap Enrl", 0), errors="coerce")
        tot_enrl = 0 if pd.isna(tot_enrl) else int(tot_enrl)
        cap_enrl = 0 if pd.isna(cap_enrl) else int(cap_enrl)
        limit_value = cap_enrl if cap_enrl > 0 else (tot_enrl if tot_enrl > 0 else 30)

        candidate_rooms = []
        for rid, rinfo in rooms.items():
            if int(rinfo["capacity"]) >= limit_value:
                candidate_rooms.append({"id": rid, "pref": 0.0})
        if len(candidate_rooms) == 0:
            candidate_rooms = [{"id": "ONLINE", "pref": 0.0}]

        row_start = row["assigned_start"]
        row_length = row["assigned_length"]
        row_days = row["assigned_days"]

        candidate_times = []
        for t in all_time_slots:
            if int(t["length"]) == int(row_length):
                candidate_times.append({
                    "days": t["days"],
                    "start": int(t["start"]),
                    "length": int(t["length"]),
                    "pref": 0.0
                })

        if len(candidate_times) == 0:
            candidate_times = [
                {"days": str(row_days), "start": int(row_start), "length": int(row_length), "pref": 0.0}
            ]

        classes[cid] = {
            "id": cid,
            "subject": str(row.get("Subject", "")),
            "catalog": str(row.get("Catalog", "")),
            "section": str(row.get("Section", "")),
            "course_name": str(row.get("Descr", "")),
            "limit": limit_value,
            "room_options": candidate_rooms,
            "time_options": candidate_times,
            "instructors": [str(row["instructor"])],
            "tot_enrl": float(tot_enrl),
            "campus": str(row.get("Campus", "")),
            "original_room": str(row["assigned_room"]),
            "original_days": str(row["assigned_days"]),
            "original_start": int(row_start),
            "original_length": int(row_length),
            "Term": str(row.get("Term", ""))
        }

    constraints = []
    return rooms, instructors, classes, constraints


# ============================================================
# INITIAL SOLUTION
# ============================================================
def smart_initial_solution(classes, rooms):
    solution_rows = []
    for cid, cls in classes.items():
        instructor_value = cls["instructors"][0] if len(cls["instructors"]) > 0 else "UNKNOWN"
        solution_rows.append({
            "class_id": str(cid),
            "subject": cls.get("subject", ""),
            "catalog": cls.get("catalog", ""),
            "course_name": cls.get("course_name", ""),
            "assigned_room": str(cls["original_room"]),
            "assigned_days": str(cls["original_days"]),
            "assigned_start": int(cls["original_start"]),
            "assigned_length": int(cls["original_length"]),
            "instructor": str(instructor_value),
            "limit": cls.get("limit", 0),
            "tot_enrl": cls.get("tot_enrl", 0),
            "campus": cls.get("campus", ""),
            "section": cls.get("section", "01")
        })
    return pd.DataFrame(solution_rows)


# ============================================================
# FITNESS
# ============================================================
def calculate_fitness(solution, rooms):
    penalty = 0
    for _, row in solution.iterrows():
        room_id = str(row["assigned_room"])
        enrolled = float(row["tot_enrl"])
        limit_value = float(row["limit"])

        if room_id in rooms:
            room_capacity = float(rooms[room_id]["capacity"])
            if enrolled > room_capacity:
                penalty += (enrolled - room_capacity)
            utilization = (enrolled / room_capacity)
            if utilization >= 0.85:
                penalty += 1

    for _, row in solution.iterrows():
        start = int(row["assigned_start"])
        if start < 540:
            penalty += 1

    grouped = solution.groupby(["subject", "catalog"])
    for _, group in grouped:
        unique_rooms = group["assigned_room"].astype(str).unique()
        if len(unique_rooms) > 1:
            penalty += (len(unique_rooms) - 1) * 2

    fitness = 1 / (1 + penalty)
    info = {
        "PF": penalty,
        "Fitness_Display": fitness,
        "Fitness_UniTime": max(0, 100 - penalty)
    }
    return fitness, info


# ============================================================
# GENERATE NEIGHBOR
# ============================================================
def generate_neighbor(solution, rooms, classes, mutation_rate=0.20):
    new_solution = solution.copy()
    n_changes = max(1, int(len(new_solution) * mutation_rate))
    idxs = random.sample(list(new_solution.index), min(n_changes, len(new_solution)))

    for idx in idxs:
        cid = str(new_solution.loc[idx, "class_id"])
        if cid not in classes:
            continue
        cls = classes[cid]

        room_options = [r["id"] for r in cls["room_options"]]
        if len(room_options) > 0:
            new_solution.loc[idx, "assigned_room"] = random.choice(room_options)

        time_options = cls["time_options"]
        if len(time_options) > 0:
            t = random.choice(time_options)
            new_solution.loc[idx, "assigned_days"] = t["days"]
            new_solution.loc[idx, "assigned_start"] = t["start"]
            new_solution.loc[idx, "assigned_length"] = t["length"]

    return new_solution


# ============================================================
# SIMULATED ANNEALING
# ============================================================
def simulated_annealing(classes, rooms, constraints, initial_temperature=1000, cooling_rate=0.97, stopping_temperature=0.01, max_iterations=25):
    current_solution = smart_initial_solution(classes, rooms)
    current_fitness, current_info = calculate_fitness(current_solution, rooms)

    best_solution = current_solution.copy()
    best_info = current_info.copy()

    temperature = initial_temperature
    iteration = 0

    while temperature > stopping_temperature and iteration < max_iterations:
        mutation_rate = max(0.05, temperature / initial_temperature)
        neighbor = generate_neighbor(current_solution, rooms, classes, mutation_rate)
        neighbor_fitness, neighbor_info = calculate_fitness(neighbor, rooms)

        delta = neighbor_info["PF"] - current_info["PF"]
        accept = False

        if delta < 0:
            accept = True
        else:
            probability = math.exp(-delta / temperature)
            if random.random() < probability:
                accept = True

        if accept:
            current_solution = neighbor.copy()
            current_info = neighbor_info.copy()

        if current_info["PF"] < best_info["PF"]:
            best_solution = current_solution.copy()
            best_info = current_info.copy()

        temperature *= cooling_rate
        iteration += 1

    return best_solution, best_info


def minutes_to_university_time(min_val):
    if pd.isna(min_val):
        return "08:00"
    h = int(min_val) // 60
    m = int(min_val) % 60
    return f"{str(h).zfill(2)}:{str(m).zfill(2)}"


# Execution
rooms, instructors, classes, constraints = parse_xml(DATASET_FILE)
best_solution, best_info = simulated_annealing(classes, rooms, constraints)

output_records = []
for _, row in best_solution.iterrows():
    cid = str(row["class_id"])
    cls_origin = classes.get(cid, {})
    start_time_str = minutes_to_university_time(row["assigned_start"])
    end_time_str = minutes_to_university_time(int(row["assigned_start"]) + int(row["assigned_length"]))
    days_pattern = str(row["assigned_days"]).ljust(7, "0")
    
    record = {
        "Term": str(cls_origin.get("Term", SHEET_NAME)),
        "Subject": str(row["subject"]),
        "Catalog": str(row["catalog"]),
        "Section": str(row.get("section", "01")),
        "Descr": str(row["course_name"]),
        "ID": cid,
        "Name": str(cls_origin.get("instructor", [row["instructor"]])[0]),
        "InstID": str(row["instructor"]),
        "Facil ID": str(row["assigned_room"]),
        "Mtg Start": start_time_str,
        "Mtg End": end_time_str,
        "TotEnrl": int(float(row["tot_enrl"])),
        "Capacity": int(row["limit"]),
        "Component": "LEC",
        "Sun": "Y" if days_pattern[6] == "1" else "N",
        "Mon": "Y" if days_pattern[0] == "1" else "N",
        "Tues": "Y" if days_pattern[1] == "1" else "N",
        "Wed": "Y" if days_pattern[2] == "1" else "N",
        "Thurs": "Y" if days_pattern[3] == "1" else "N"
    }
    output_records.append(record)

print(json.dumps(output_records))