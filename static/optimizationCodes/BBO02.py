# ============================================================
# IMPORTS
# ============================================================
import pandas as pd
import numpy as np
import random
import time
import os
import sys
import json
from collections import defaultdict
import math

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

# =====================================================
# PARSE DATASET
# =====================================================
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

    instructors = {}
    unique_instr_df = df[["instructor", "Name_clean"]].drop_duplicates()
    for _, row in unique_instr_df.iterrows():
        iid = str(row["instructor"])
        instructors[iid] = {
            "id": iid,
            "name": row["Name_clean"] if row["Name_clean"] != "" else iid
        }

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

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def get_course_key(row):
    subject = str(row.get("subject", "")).strip()
    catalog = str(row.get("catalog", "")).strip()
    if subject != "" and catalog != "":
        return subject + "_" + catalog
    course_name = str(row.get("course_name", "")).strip()
    if course_name != "":
        return course_name
    return str(row.get("class_id", ""))

def get_department_key(row):
    subject = str(row.get("subject", "")).strip()
    if subject != "":
        return subject
    return "UNKNOWN"

def get_room_capacity(room_id, rooms, default_capacity=0):
    room_id = str(room_id)
    if room_id in rooms:
        return float(rooms[room_id].get("capacity", default_capacity))
    return float(default_capacity)

# =====================================================
# INITIAL SOLUTION
# =====================================================
def smart_initial_solution(classes, rooms):
    solution_rows = []
    for cid, cls in classes.items():
        assigned_room = cls["original_room"]
        assigned_days = cls["original_days"]
        assigned_start = int(cls["original_start"])
        assigned_length = int(cls["original_length"])
        instructors_list = cls.get("instructors", ["UNKNOWN"])
        instructor_value = instructors_list[0] if len(instructors_list) > 0 else "UNKNOWN"

        solution_rows.append({
            "class_id": str(cid),
            "subject": cls.get("subject", ""),
            "catalog": cls.get("catalog", ""),
            "course_name": cls.get("course_name", ""),
            "assigned_room": str(assigned_room),
            "assigned_days": str(assigned_days),
            "assigned_start": int(assigned_start),
            "assigned_length": int(assigned_length),
            "instructor": str(instructor_value),
            "limit": cls.get("limit", 0),
            "tot_enrl": cls.get("tot_enrl", cls.get("limit", 0)),
            "campus": cls.get("campus", ""),
            "section": cls.get("section", "01")
        })
    return pd.DataFrame(solution_rows)

# =====================================================
# SOFT CONSTRAINTS
# =====================================================
def calculate_selected_soft_constraints(solution, rooms):
    rows = solution.copy().reset_index(drop=True)
    W_BTB, W_NHB1, W_NHB_GTE1, W_SAME_ROOM, W_DEPT_BALANCE = 1.0, 1.0, 1.0, 2.0, 2.0
    BTB, NHB1, NHB_GTE1, SAME_ROOM, DEPT_BALANCE = 0.0, 0, 0, 0, 0.0

    for _, row in rows.iterrows():
        start = row.get("assigned_start", None)
        if pd.notna(start) and int(start) < 540:
            NHB1 += 1

    for _, row in rows.iterrows():
        room_id = str(row.get("assigned_room", ""))
        enrollment = row.get("tot_enrl", row.get("limit", 0))
        limit_value = row.get("limit", 0)
        try: enrollment = float(enrollment)
        except: enrollment = 0
        try: limit_value = float(limit_value)
        except: limit_value = 0

        room_capacity = get_room_capacity(room_id, rooms, default_capacity=limit_value)
        if room_capacity > 0 and enrollment > 0:
            if (enrollment / room_capacity) >= 0.85:
                NHB_GTE1 += 1

    rows["course_key_temp"] = rows.apply(get_course_key, axis=1)
    for course_key, group in rows.groupby("course_key_temp"):
        unique_rooms = group["assigned_room"].dropna().astype(str).unique()
        if len(unique_rooms) > 1:
            SAME_ROOM += len(unique_rooms) - 1

    instructor_col = "instructor" if "instructor" in rows.columns else None
    if instructor_col is not None:
        for instructor_id, group in rows.groupby(instructor_col):
            instructor_id = str(instructor_id)
            if instructor_id == "" or instructor_id.lower() == "nan" or instructor_id.upper() == "UNKNOWN":
                continue
            group = group.copy()
            for day_index in range(7):
                day_classes = group[group["assigned_days"].astype(str).str[day_index:day_index+1] == "1"].copy()
                if len(day_classes) <= 1: continue
                day_classes = day_classes.sort_values("assigned_start")
                previous_end = None
                for _, row in day_classes.iterrows():
                    start = int(row["assigned_start"])
                    end = start + int(row["assigned_length"])
                    if previous_end is not None:
                        gap = start - previous_end
                        if gap > 0: BTB += gap / 60.0
                    previous_end = max(previous_end, end) if previous_end is not None else end

    rows["dept_key_temp"] = rows.apply(get_department_key, axis=1)
    for dept, group in rows.groupby("dept_key_temp"):
        morning_count, afternoon_count = 0, 0
        for _, row in group.iterrows():
            start = row.get("assigned_start", None)
            if pd.isna(start): continue
            if int(start) < 720: morning_count += 1
            else: afternoon_count += 1

        time_balance_penalty = abs(morning_count - afternoon_count)
        room_counts = group["assigned_room"].astype(str).value_counts()
        room_balance_penalty = float(room_counts.std()) if len(room_counts) > 1 else 0.0
        if np.isnan(room_balance_penalty): room_balance_penalty = 0.0
        DEPT_BALANCE += (time_balance_penalty + room_balance_penalty)

    P_BTB = W_BTB * BTB
    P_NHB1 = W_NHB1 * NHB1
    P_NHB_GTE1 = W_NHB_GTE1 * NHB_GTE1
    P_SAME_ROOM = W_SAME_ROOM * SAME_ROOM
    P_DEPT_BALANCE = W_DEPT_BALANCE * DEPT_BALANCE
    P_soft = P_BTB + P_NHB1 + P_NHB_GTE1 + P_SAME_ROOM + P_DEPT_BALANCE

    return P_soft, {"BTB": BTB, "NHB1": NHB1, "NHB_GTE1": NHB_GTE1, "SameRoom": SAME_ROOM, "DeptBalance": DEPT_BALANCE, "P_BTB": P_BTB, "P_NHB1": P_NHB1, "P_NHB_GTE1": P_NHB_GTE1, "P_SameRoom": P_SAME_ROOM, "P_DeptBalance": P_DEPT_BALANCE, "P_soft": P_soft}

# =====================================================
# FITNESS
# =====================================================
def calculate_fitness(solution, rooms):
    Soft_Penalty, soft_details = calculate_selected_soft_constraints(solution, rooms)
    PF = Soft_Penalty
    Fitness_UniTime = max(0, 100 - PF)
    Fitness_Display = 1 / (1 + PF)
    return Fitness_Display, {"PF": PF, "Fitness_Display": Fitness_Display, "Fitness_UniTime": Fitness_UniTime, "Soft_Penalty": Soft_Penalty, "BTB": soft_details["BTB"], "NHB1": soft_details["NHB1"], "NHB_GTE1": soft_details["NHB_GTE1"], "SameRoom": soft_details["SameRoom"], "DeptBalance": soft_details["DeptBalance"], "P_BTB": soft_details["P_BTB"], "P_NHB1": soft_details["P_NHB1"], "P_NHB_GTE1": soft_details["P_NHB_GTE1"], "P_SameRoom": soft_details["P_SameRoom"], "P_DeptBalance": soft_details["P_DeptBalance"]}

# =====================================================
# NEIGHBOR
# =====================================================
def generate_neighbor(solution, rooms, classes, mutation_rate=0.20):
    if solution.empty: return solution.copy()
    new = solution.copy()
    n_changes = max(1, int(len(new) * mutation_rate))
    idxs = random.sample(list(new.index), min(n_changes, len(new)))

    for idx in idxs:
        cid = str(new.loc[idx, "class_id"])
        if cid not in classes: continue
        cls = classes[cid]

        current_room = new.loc[idx, "assigned_room"]
        room_alternatives = [r["id"] for r in cls.get("room_options", []) if str(r["id"]) != str(current_room)]
        if len(room_alternatives) > 0:
            new.loc[idx, "assigned_room"] = str(random.choice(room_alternatives))

        time_options = cls.get("time_options", [])
        if len(time_options) > 1:
            current_days = new.loc[idx, "assigned_days"]
            current_start = new.loc[idx, "assigned_start"]
            current_length = new.loc[idx, "assigned_length"]
            time_alternatives = [t for t in time_options if not (str(t["days"]) == str(current_days) and int(t["start"]) == int(current_start))]
            if len(time_alternatives) > 0:
                selected_time = random.choice(time_alternatives)
                new.loc[idx, "assigned_days"] = str(selected_time["days"])
                new.loc[idx, "assigned_start"] = int(selected_time["start"])
                new.loc[idx, "assigned_length"] = int(selected_time["length"])
    return new

# =====================================================
# INITIAL POPULATION
# =====================================================
def create_initial_population_bbo(classes, rooms, population_size=25):
    population = []
    base_solution = smart_initial_solution(classes, rooms)
    population.append(base_solution.copy())
    for _ in range(population_size - 1):
        sol = smart_initial_solution(classes, rooms)
        sol = generate_neighbor(sol, rooms, classes, mutation_rate=0.40)
        population.append(sol.copy())
    return population


def evaluate_population_bbo(population, rooms):
    evaluated = []
    for sol in population:
        fitness, info = calculate_fitness(sol, rooms)
        evaluated.append({"solution": sol.copy(), "fitness": fitness, "info": info, "PF": info["PF"]})
    return sorted(evaluated, key=lambda x: x["PF"])


def bbo_migration(donor, receiver, migration_rate=0.30):
    new_solution = receiver.copy()
    n_migrate = max(1, int(len(new_solution) * migration_rate))
    migrate_indices = random.sample(list(new_solution.index), min(n_migrate, len(new_solution)))

    for idx in migrate_indices:
        if idx in donor.index:
            new_solution.loc[idx, "assigned_room"] = donor.loc[idx, "assigned_room"]
            new_solution.loc[idx, "assigned_days"] = donor.loc[idx, "assigned_days"]
            new_solution.loc[idx, "assigned_start"] = donor.loc[idx, "assigned_start"]
            new_solution.loc[idx, "assigned_length"] = donor.loc[idx, "assigned_length"]
    return new_solution


def local_search_bbo(solution, rooms, classes, attempts=10, mutation_rate=0.05):
    best_sol = solution.copy()
    best_fit, best_info = calculate_fitness(best_sol, rooms)
    for _ in range(attempts):
        candidate = generate_neighbor(best_sol, rooms, classes, mutation_rate=mutation_rate)
        cand_fit, cand_info = calculate_fitness(candidate, rooms)
        if cand_info["PF"] < best_info["PF"]:
            best_sol, best_info = candidate.copy(), cand_info.copy()
    return best_sol, best_fit, best_info


def adaptive_mutation_rate(generation, generations, max_mutation=0.35, min_mutation=0.05):
    return max_mutation - (generation / max(1, generations - 1)) * (max_mutation - min_mutation)

# =====================================================
# BBO MAIN ALGORITHM
# =====================================================
def bbo_algorithm(classes, rooms, constraints, population_size=15, generations=15, elite_size=2, migration_rate=0.35, max_mutation=0.30, min_mutation=0.05, local_search_attempts=2, random_immigrants=1):
    population = create_initial_population_bbo(classes, rooms, population_size=population_size)
    evaluated = evaluate_population_bbo(population, rooms)
    best_solution, best_info = evaluated[0]["solution"].copy(), evaluated[0]["info"].copy()

    for generation in range(generations):
        evaluated = evaluate_population_bbo(population, rooms)
        best_habitats = evaluated[:elite_size]
        current_best = evaluated[0]

        improved_solution, improved_fitness, improved_info = local_search_bbo(current_best["solution"], rooms, classes, attempts=local_search_attempts, mutation_rate=0.05)
        if improved_info["PF"] < current_best["info"]["PF"]:
            current_best = {"solution": improved_solution.copy(), "info": improved_info.copy(), "PF": improved_info["PF"]}

        if current_best["info"]["PF"] < best_info["PF"]:
            best_solution, best_info = current_best["solution"].copy(), current_best["info"].copy()

        mutation_rate = adaptive_mutation_rate(generation, generations, max_mutation=max_mutation, min_mutation=min_mutation)
        new_population = [elite["solution"].copy() for elite in best_habitats]
        new_population.append(best_solution.copy())

        while len(new_population) < population_size - random_immigrants:
            donor = random.choice(best_habitats)["solution"]
            weak_habitats = evaluated[elite_size:]
            receiver = random.choice(weak_habitats)["solution"] if len(weak_habitats) > 0 else random.choice(evaluated)["solution"]

            migrated_solution = bbo_migration(donor, receiver, migration_rate=migration_rate)
            mutated_solution = generate_neighbor(migrated_solution, rooms, classes, mutation_rate=mutation_rate)
            new_population.append(mutated_solution.copy())

        for _ in range(random_immigrants):
            immigrant = smart_initial_solution(classes, rooms)
            immigrant = generate_neighbor(immigrant, rooms, classes, mutation_rate=0.50)
            new_population.append(immigrant.copy())

        population = new_population[:population_size]

    _, final_best_info = calculate_fitness(best_solution, rooms)
    return best_solution, final_best_info


def minutes_to_university_time(min_val):
    if pd.isna(min_val):
        return "08:00"
    h = int(min_val) // 60
    m = int(min_val) % 60
    return f"{str(h).zfill(2)}:{str(m).zfill(2)}"

rooms, instructors, classes, constraints = parse_xml(DATASET_FILE)
best_solution, best_info = bbo_algorithm(classes, rooms, constraints)

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