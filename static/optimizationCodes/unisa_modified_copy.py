import pandas as pd
import numpy as np
import random
import time
import os
import sys
import json
from collections import defaultdict
import math

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

excel_filename = sys.argv[1] if len(sys.argv) > 1 else "Fall 2024 - 2421.xlsx"
DATASET_FILE = os.path.normpath(os.path.join(base_dir, 'data', excel_filename))

if not os.path.exists(DATASET_FILE):
    print(json.dumps([]))
    sys.exit(0)

try:
    xl = pd.ExcelFile(DATASET_FILE)
    SHEET_NAME = xl.sheet_names[0]
except Exception:
    print(json.dumps([]))
    sys.exit(0)


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
            candidate_times = [{"days": str(row_days), "start": int(row_start), "length": int(row_length), "pref": 0.0}]

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

rooms, instructors, classes, constraints = parse_xml(DATASET_FILE)

def minutes_to_university_time(min_val):
    if pd.isna(min_val):
        return "08:00"
    h = int(min_val) // 60
    m = int(min_val) % 60
    return f"{str(h).zfill(2)}:{str(m).zfill(2)}"

def smart_initial_solution(classes, rooms):
    columns = [
        "class_id", "subject", "catalog", "section", "course_name",
        "assigned_room", "assigned_days", "assigned_start", "assigned_length",
        "instructor", "limit", "tot_enrl", "campus"
    ]

    def days_overlap(d1, d2):
        d1, d2 = str(d1).ljust(7, "0"), str(d2).ljust(7, "0")
        return any(d1[i] == "1" and d2[i] == "1" for i in range(7))

    def time_overlap(s1, l1, s2, l2):
        return max(s1, s2) < min(s1 + l1, s2 + l2)

    def has_conflict(rid, days, start, length, instr_list, room_usage, inst_usage):
        rc, ic = False, False
        for used in room_usage:
            if used["room"] == rid and rid != "ONLINE":
                if days_overlap(used["days"], days) and time_overlap(used["start"], used["length"], start, length):
                    rc = True
                    break
        for inst in instr_list:
            for used in inst_usage[inst]:
                if days_overlap(used["days"], days) and time_overlap(used["start"], used["length"], start, length):
                    ic = True
                    break
            if ic: break
        return rc, ic

    rows = []
    room_usage = []
    inst_usage = defaultdict(list)

    sorted_classes = sorted(classes.values(), key=lambda c: (len(c["time_options"]), -c["limit"]))

    for cls in sorted_classes:
        cid = cls["id"]
        candidate_rooms = cls["room_options"] if cls["room_options"] else [{"id": "ONLINE", "pref": 0.0}]
        candidate_times = cls["time_options"] if cls["time_options"] else [{"days": "1000000", "start": 480, "length": 50, "pref": 0.0}]

        chosen_room, chosen_time = None, None

        for t in candidate_times:
            if chosen_room: break
            for r in candidate_rooms:
                rid = r["id"]
                cap = rooms[rid]["capacity"] if rid in rooms else 9999
                if cap < cls["limit"]: continue
                rc, ic = has_conflict(rid, t["days"], int(t["start"]), int(t["length"]), cls["instructors"], room_usage, inst_usage)
                if not rc and not ic:
                    chosen_room, chosen_time = rid, t
                    break

        if chosen_room is None:
            for t in candidate_times:
                if chosen_room: break
                for r in candidate_rooms:
                    rid = r["id"]
                    rc, ic = has_conflict(rid, t["days"], int(t["start"]), int(t["length"]), cls["instructors"], room_usage, inst_usage)
                    if not rc and not ic:
                        chosen_room, chosen_time = rid, t
                        break

        if chosen_room is None:
            for t in candidate_times:
                if chosen_room: break
                for r in candidate_rooms:
                    rid = r["id"]
                    _, ic = has_conflict(rid, t["days"], int(t["start"]), int(t["length"]), cls["instructors"], room_usage, inst_usage)
                    if not ic:
                        chosen_room, chosen_time = rid, t
                        break

        if chosen_room is None:
            chosen_room = candidate_rooms[0]["id"]
            chosen_time = candidate_times[0]

        room_usage.append({"room": chosen_room, "days": chosen_time["days"], "start": int(chosen_time["start"]), "length": int(chosen_time["length"])})
        for inst in cls["instructors"]:
            inst_usage[inst].append({"days": chosen_time["days"], "start": int(chosen_time["start"]), "length": int(chosen_time["length"])})

        rows.append({
            "class_id": cid, "subject": cls.get("subject", ""), "catalog": cls.get("catalog", ""), "section": cls.get("section", ""),
            "course_name": cls.get("course_name", ""), "assigned_room": chosen_room, "assigned_days": chosen_time["days"],
            "assigned_start": int(chosen_time["start"]), "assigned_length": int(chosen_time["length"]),
            "instructor": cls["instructors"][0] if cls["instructors"] else "UNKNOWN", "limit": cls["limit"], "tot_enrl": cls.get("tot_enrl", 0), "campus": cls.get("campus", "")
        })

    sol = pd.DataFrame(rows, columns=columns)
    sol = repair_cap_viol(sol, rooms, classes)
    return sol

def calculate_fitness(solution, rooms, classes):
    HC_WEIGHT = 1000.0
    info = {"PF": 0.0, "Fitness_Display": 0.0, "HC1_RoomConflict": 0, "HC2_InstrConflict": 0, "HC3_CapViol": 0, "Total_HC": 0, "BTB": 0, "NHB1": 0, "NHB_GTE1": 0, "DeptBalance": 0.0, "Soft_Penalty": 0.0}

    def days_overlap(d1, d2):
        return any(str(d1).ljust(7,"0")[i] == '1' and str(d2).ljust(7,"0")[i] == '1' for i in range(7))

    def time_overlap(s1, l1, s2, l2):
        return max(s1, s2) < min(s1 + l1, s2 + l2)

    records = []
    for _, row in solution.iterrows():
        records.append({
            "cls_id": str(row["class_id"]), "room": str(row["assigned_room"]), "days": str(row["assigned_days"]),
            "start": int(row["assigned_start"]), "length": int(row["assigned_length"]), "instructor": str(row.get("instructor", "UNKNOWN")), "subject": str(row.get("subject", ""))
        })

    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            r1, r2 = records[i], records[j]
            if days_overlap(r1["days"], r2["days"]) and time_overlap(r1["start"], r1["length"], r2["start"], r2["length"]):
                if r1["room"] == r2["room"] and r1["room"] != "ONLINE":
                    info["HC1_RoomConflict"] += 1
                if r1["instructor"] == r2["instructor"] and r1["instructor"] not in ("UNKNOWN", ""):
                    info["HC2_InstrConflict"] += 1

    cap_viol = 0
    for rec in records:
        rid = rec["room"]
        if rid == "ONLINE": continue
        room_cap = rooms[rid]["capacity"] if rid in rooms else 9999
        cls_data = classes.get(rec["cls_id"], {})
        if float(cls_data.get("tot_enrl", 0)) > room_cap:
            cap_viol += 1

    info["HC3_CapViol"] = cap_viol
    info["Total_HC"] = info["HC1_RoomConflict"] + info["HC2_InstrConflict"] + info["HC3_CapViol"]

    inst_day_slots = defaultdict(list)
    for rec in records:
        days_str = str(rec["days"]).ljust(7, "0")
        for d_idx in range(7):
            if days_str[d_idx] == "1":
                inst_day_slots[(rec["instructor"], d_idx)].append((rec["start"], rec["length"]))

    for slots in inst_day_slots.values():
        slots_sorted = sorted(slots, key=lambda x: x[0])
        for k in range(len(slots_sorted) - 1):
            gap = slots_sorted[k + 1][0] - (slots_sorted[k][0] + slots_sorted[k][1])
            if gap == 0: info["BTB"] += 1
            if gap < 60: info["NHB1"] += 1
            if gap >= 0: info["NHB_GTE1"] += 1

    info["Soft_Penalty"] = float(info["BTB"] + info["NHB1"] + info["NHB_GTE1"])
    info["PF"] = (info["Total_HC"] * HC_WEIGHT) + info["Soft_Penalty"]
    info["Fitness_Display"] = 1.0 / (1.0 + info["PF"])
    return info["PF"], info

def _build_index(sol):
    room_idx = defaultdict(lambda: defaultdict(set))
    inst_idx = defaultdict(lambda: defaultdict(set))
    for idx, row in sol.iterrows():
        room, instr, days = str(row["assigned_room"]), str(row["instructor"]), str(row["assigned_days"]).ljust(7,"0")
        s, l = int(row["assigned_start"]), int(row["assigned_length"])
    for d in range(7):
            if days[d] != "1": continue
            for slot in range(s, s+l):
                if room != "ONLINE":
                    room_idx[room][(d, slot)].add(idx)  # تعديل السطر 371 هنا بالملي
                if instr not in ("UNKNOWN", ""):
                    inst_idx[instr][(d, slot)].add(idx)
                    
    return room_idx, inst_idx

def _slot_set(days, start, length):
    out = set()
    for d in range(7):
        if str(days).ljust(7,"0")[d] == "1":
            for slot in range(int(start), int(start)+int(length)): out.add((d,slot))
    return out

def _violating_pairs(sol):
    room_idx, inst_idx = _build_index(sol)
    seen, pairs = set(), []
    for mapping, kind in ((room_idx,"room"),(inst_idx,"inst")):
        for idxs in mapping.values():
            for idx_set in idxs.values():
                if len(idx_set) > 1:
                    lst = sorted(idx_set)
                    for a in range(len(lst)):
                        for b in range(a+1, len(lst)):
                            pair = (lst[a], lst[b], kind)
                            if pair not in seen: seen.add(pair); pairs.append(pair)
    return pairs

def _is_clean_idx(sol, idx, rid, instr, days, start, length, room_idx, inst_idx):
    keys = _slot_set(days, start, length)
    for key in keys:
        if rid != "ONLINE" and (room_idx[rid].get(key, set()) - {idx}): return False
        if instr not in ("UNKNOWN","") and (inst_idx[instr].get(key, set()) - {idx}): return False
    return True

def _remove_from_index(sol, idx, room_idx, inst_idx):
    room, instr, days = str(sol.loc[idx,"assigned_room"]), str(sol.loc[idx,"instructor"]), str(sol.loc[idx,"assigned_days"]).ljust(7,"0")
    s, l = int(sol.loc[idx,"assigned_start"]), int(sol.loc[idx,"assigned_length"])
    for d in range(7):
        if days[d] != "1": continue
        for slot in range(s, s+l):
            if room != "ONLINE": room_idx[room][(d,slot)].discard(idx)
            if instr not in ("UNKNOWN",""): inst_idx[instr][(d,slot)].discard(idx)

def _add_to_index(sol, idx, room_idx, inst_idx):
    room, instr, days = str(sol.loc[idx,"assigned_room"]), str(sol.loc[idx,"instructor"]), str(sol.loc[idx,"assigned_days"]).ljust(7,"0")
    s, l = int(sol.loc[idx,"assigned_start"]), int(sol.loc[idx,"assigned_length"])
    for d in range(7):
        if days[d] != "1": continue
        for slot in range(s, s+l):
            if room != "ONLINE": room_idx[room][(d,slot)].add(idx)
            if instr not in ("UNKNOWN",""): inst_idx[instr][(d,slot)].add(idx)

def repair_hc(solution, rooms, classes):
    sol = solution.copy()
    for _round in range(15):
        pairs = _violating_pairs(sol)
        if not pairs: break
        room_idx, inst_idx = _build_index(sol)
        for (ia, ib, kind) in pairs:
            for target_idx in (ib, ia):
                cid = str(sol.loc[target_idx,"class_id"])
                if cid not in classes: continue
                cls, instr = classes[cid], str(sol.loc[target_idx,"instructor"])
                t_opts, r_opts = list(cls.get("time_options",[])), list(cls.get("room_options",[{"id":"ONLINE"}]))
                random.shuffle(t_opts)
                placed = False
                for t in t_opts:
                    for r in r_opts:
                        rid = r["id"]
                        if (rooms[rid]["capacity"] if rid in rooms else 9999) < cls["limit"]: continue
                        if _is_clean_idx(sol, target_idx, rid, instr, t["days"], t["start"], t["length"], room_idx, inst_idx):
                            _remove_from_index(sol, target_idx, room_idx, inst_idx)
                            sol.loc[target_idx,"assigned_room"], sol.loc[target_idx,"assigned_days"] = rid, t["days"]
                            sol.loc[target_idx,"assigned_start"], sol.loc[target_idx,"assigned_length"] = int(t["start"]), int(t["length"])
                            _add_to_index(sol, target_idx, room_idx, inst_idx)
                            placed = True; break
                    if placed: break
                if placed: break
    return sol

def repair_cap_viol(solution, rooms, classes):
    sol = solution.copy()
    for idx, row in sol.iterrows():
        rid = str(row["assigned_room"])
        if rid == "ONLINE": continue
        room_cap = rooms[rid]["capacity"] if rid in rooms else 9999
        enrl = float(row.get("tot_enrl", 0))
        if enrl <= room_cap: continue
        cid = str(row["class_id"])
        if cid not in classes: continue
        candidate_rooms = sorted([r for r in classes[cid].get("room_options", []) if r["id"] != rid], key=lambda r: rooms[r["id"]]["capacity"] if r["id"] in rooms else 9999, reverse=True)
        placed = False
        for r in candidate_rooms:
            if (rooms[r["id"]]["capacity"] if r["id"] in rooms else 9999) >= enrl:
                sol.loc[idx, "assigned_room"] = r["id"]; placed = True; break
        if not placed: sol.loc[idx, "assigned_room"] = "ONLINE"
    return sol

def generate_neighbor(solution, rooms, classes, mutation_rate=0.30):
    if solution.empty: return solution.copy()
    new_sol = solution.copy()
    idxs = random.sample(list(new_sol.index), min(max(1, int(len(new_sol) * mutation_rate)), len(new_sol)))
    for idx in idxs:
        cid = str(new_sol.loc[idx,"class_id"])
        if cid not in classes: continue
        cls = classes[cid]
        if cls.get("time_options"):
            t = random.choice(cls["time_options"])
            new_sol.loc[idx,"assigned_days"], new_sol.loc[idx,"assigned_start"], new_sol.loc[idx,"assigned_length"] = t["days"], int(t["start"]), int(t["length"])
        if cls.get("room_options"):
            valid = [r["id"] for r in cls["room_options"] if (rooms[r["id"]]["capacity"] if r["id"] in rooms else 9999) >= cls["limit"]]
            if not valid: valid = [r["id"] for r in cls["room_options"]]
            if valid: new_sol.loc[idx,"assigned_room"] = random.choice(valid)
    new_sol = repair_hc(new_sol, rooms, classes)
    new_sol = repair_cap_viol(new_sol, rooms, classes)
    return new_sol

def simulated_annealing(classes, rooms, constraints, T0=1000.0, alpha=0.95, Tmin=0.1, iterations=15):
    current_solution = smart_initial_solution(classes, rooms)
    current_fitness, current_info = calculate_fitness(current_solution, rooms, classes)
    best_solution = current_solution.copy()
    best_info = current_info.copy()
    T = T0

    for iteration in range(iterations):
        rate = 0.35 - (iteration / iterations) * 0.30
        neighbor = generate_neighbor(current_solution, rooms, classes, mutation_rate=rate)
        if neighbor.equals(current_solution): continue
        neighbor_fitness, neighbor_info = calculate_fitness(neighbor, rooms, classes)
        delta = neighbor_info["PF"] - current_info["PF"]
        if delta < 0 or (T > 0 and random.random() < math.exp(-delta / T)):
            current_solution = neighbor.copy()
            current_info = neighbor_info.copy()
        if current_info["PF"] < best_info["PF"]:
            best_solution = current_solution.copy()
            best_info = current_info.copy()
        T *= alpha
        if T < Tmin: break
    return best_solution, best_info

best_sol, best_inf = simulated_annealing(classes, rooms, constraints)

output_records = []
for _, row in best_sol.iterrows():
    cid = str(row["class_id"])
    cls_origin = classes.get(cid, {})
    
    start_time_str = minutes_to_university_time(row["assigned_start"])
    end_time_str = minutes_to_university_time(int(row["assigned_start"]) + int(row["assigned_length"]))
    
    days_pattern = str(row["assigned_days"]).ljust(7, "0")
    
    record = {
        "Term": str(cls_origin.get("Term", SHEET_NAME)),
        "Subject": str(row["subject"]),
        "Catalog": str(row["catalog"]),
        "Section": str(row["section"]),
        "Descr": str(row["course_name"]),
        "ID": str(row["class_id"]),
        "Name": str(cls_origin.get("name", instructors.get(str(row["instructor"]), {}).get("name", row["instructor"]))),
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