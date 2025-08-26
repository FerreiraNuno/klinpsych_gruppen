#!/usr/bin/env python3
import csv
import sys
import os

VALID_GROUPS = {"A", "B", "C", "D"}

def parse_bool(s):
    if isinstance(s, bool):
        return s
    if s is None:
        return False
    v = str(s).strip().lower()
    if v in {"true", "wahr", "ja", "j", "1"}:
        return True
    if v in {"false", "falsch", "nein", "n", "0", ""}:
        return False
    return False

def read_clinics(path):
    if not os.path.exists(path):
        fail(f"Datei nicht gefunden: {path}")
    clinics = []
    clinic_index = {}
    required = ["klinik_id", "klinik_name", "stadt", "ist_giessen", "cap_A", "cap_B", "cap_C", "cap_D"]
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in required if c not in reader.fieldnames]
        if missing:
            fail("In 'kliniken.csv' fehlen Spalten: " + ", ".join(missing))
        rownum = 1
        for row in reader:
            rownum += 1
            cid = (row.get("klinik_id") or "").strip()
            if not cid:
                fail(f"'kliniken.csv': Leere klinik_id in Zeile {rownum}.")
            if cid in clinic_index:
                fail(f"'kliniken.csv': Doppelte klinik_id '{cid}' in Zeile {rownum}.")
            try:
                cap_A = int((row.get("cap_A") or "0").strip() or "0")
                cap_B = int((row.get("cap_B") or "0").strip() or "0")
                cap_C = int((row.get("cap_C") or "0").strip() or "0")
                cap_D = int((row.get("cap_D") or "0").strip() or "0")
            except ValueError:
                fail(f"'kliniken.cs': Kapazitäten müssen Ganzzahlen sein (Zeile {rownum}, klinik_id {cid}).")
            if min(cap_A, cap_B, cap_C, cap_D) < 0:
                fail(f"'kliniken.cs': Kapazitäten dürfen nicht negativ sein (klinik_id {cid}).")
            clinic = {
                "klinik_id": cid,
                "klinik_name": (row.get("klinik_name") or "").strip(),
                "stadt": (row.get("stadt") or "").strip(),
                "ist_giessen": parse_bool(row.get("ist_giessen")),
                "cap": {"A": cap_A, "B": cap_B, "C": cap_C, "D": cap_D},
                "order": len(clinics),
            }
            clinics.append(clinic)
            clinic_index[cid] = clinic
    if not clinics:
        fail("'kliniken.cs' enthält keine Daten.")
    return clinics, clinic_index

def normalize_group(g):
    if g is None:
        return ""
    return str(g).strip().upper()

def read_students(path, clinic_index, require_outside):
    if not os.path.exists(path):
        fail(f"Datei nicht gefunden: {path}")
    students = []
    idx_by_matnr = {}
    required = ["matrikelnummer", "name", "email", "gruppe_prio1", "gruppe_prio2", "klinik_prio1", "klinik_prio2", "klinik_prio3"]
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in required if c not in reader.fieldnames]
        if missing:
            fail("In 'studierende.csv' fehlen Spalten: " + ", ".join(missing))
        errors = []
        rownum = 1
        for row in reader:
            rownum += 1
            mraw = row.get("matrikelnummer")
            matnr = str(mraw).strip() if mraw is not None else ""
            if not matnr or not matnr.isdigit():
                errors.append(f"Zeile {rownum}: Ungültige Matrikelnummer '{mraw}'.")
                continue
            if matnr in idx_by_matnr:
                errors.append(f"Zeile {rownum}: Doppelte Matrikelnummer '{matnr}'.")
                continue
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip()
            g1 = normalize_group(row.get("gruppe_prio1"))
            g2 = normalize_group(row.get("gruppe_prio2"))
            if g1 not in VALID_GROUPS:
                errors.append(f"Zeile {rownum}: gruppe_prio1 muss A/B/C/D sein (gefunden: '{row.get('gruppe_prio1')}').")
                continue
            if g2 and g2 not in VALID_GROUPS:
                errors.append(f"Zeile {rownum}: gruppe_prio2 muss A/B/C/D oder leer sein (gefunden: '{row.get('gruppe_prio2')}').")
                continue
            c1 = (row.get("klinik_prio1") or "").strip()
            c2 = (row.get("klinik_prio2") or "").strip()
            c3 = (row.get("klinik_prio3") or "").strip()
            for c in [c1, c2, c3]:
                if c and c not in clinic_index:
                    errors.append(f"Zeile {rownum}: Unbekannte klinik_id '{c}' in Klinik-Präferenzen.")
            if require_outside:
                outside_ok = False
                for c in [c1, c2, c3]:
                    if c and c in clinic_index and not clinic_index[c]["ist_giessen"]:
                        outside_ok = True
                        break
                if not outside_ok:
                    errors.append(f"Zeile {rownum}: Es muss mindestens eine Klinik-Präferenz außerhalb Gießens angegeben sein.")
            student = {
                "matnr": matnr,
                "name": name,
                "email": email,
                "g1": g1,
                "g2": g2,
                "c1": c1,
                "c2": c2,
                "c3": c3,
            }
            idx_by_matnr[matnr] = len(students)
            students.append(student)
    if errors:
        fail_list("Eingabefehler in 'studierende.csv':", errors)
    if not students:
        fail("'studierende.csv' enthält keine Daten.")
    students.sort(key=lambda s: int(s["matnr"]))
    return students

def build_slots(clinics):
    slots = []
    for g in ["A", "B", "C", "D"]:
        for clinic in sorted(clinics, key=lambda x: x["order"]):
            cap = clinic["cap"][g]
            for i in range(cap):
                slots.append((g, clinic["klinik_id"]))
    return slots

def availability(slots):
    avail = {}
    for g, cid in slots:
        avail.setdefault((g, cid), 0)
        avail[(g, cid)] += 1
    return avail

def take_slot(avail, g, cid):
    k = (g, cid)
    if k in avail and avail[k] > 0:
        avail[k] -= 1
        if avail[k] == 0:
            del avail[k]
        return True
    return False

def uniq(seq):
    seen = set()
    out = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def assign(students, clinics, clinic_index):
    slots = build_slots(clinics)
    avail = availability(slots)
    total_slots = sum(v for v in avail.values())
    if total_slots < len(students):
        fail(f"Zu wenig Kapazität insgesamt: Plätze={total_slots}, Studierende={len(students)}.")
    zugeordnet = {}
    stats = {"gruppe_prio1": 0, "gruppe_prio2": 0, "klinik_prio1": 0, "klinik_prio2": 0, "klinik_prio3": 0}
    rounds = [
        lambda s: [(s["g1"], s["c1"])],
        lambda s: [(s["g1"], s["c2"])],
        lambda s: [(s["g1"], s["c3"])],
        lambda s: [(s["g2"], s["c1"])],
        lambda s: [(s["g2"], s["c2"])],
        lambda s: [(s["g2"], s["c3"])],
    ]
    for r in range(len(rounds)):
        for s in students:
            if s["matnr"] in zugeordnet:
                continue
            for g, c in uniq(rounds[r](s)):
                if g in VALID_GROUPS and c and take_slot(avail, g, c):
                    zugeordnet[s["matnr"]] = {"group": g, "clinic": c}
                    if r <= 2:
                        stats["gruppe_prio1"] += 1
                    elif r <= 5:
                        stats["gruppe_prio2"] += 1
                    if r in [0, 3]:
                        stats["klinik_prio1"] += 1
                    elif r in [1, 4]:
                        stats["klinik_prio2"] += 1
                    elif r in [2, 5]:
                        stats["klinik_prio3"] += 1
                    break
    for s in students:
        if s["matnr"] in zugeordnet:
            continue
        for c in uniq([s["c1"], s["c2"], s["c3"]]):
            pref_groups = uniq([s["g1"], s["g2"], "A", "B", "C", "D"])
            done = False
            for g in pref_groups:
                if g in VALID_GROUPS and take_slot(avail, g, c):
                    zugeordnet[s["matnr"]] = {"group": g, "clinic": c}
                    if c == s["c1"]:
                        stats["klinik_prio1"] += 1
                    elif c == s["c2"]:
                        stats["klinik_prio2"] += 1
                    elif c == s["c3"]:
                        stats["klinik_prio3"] += 1
                    done = True
                    break
            if done:
                break
    for s in students:
        if s["matnr"] in zugeordnet:
            continue
        placed = False
        for g in ["A", "B", "C", "D"]:
            for clinic in sorted(clinics, key=lambda x: x["order"]):
                cid = clinic["klinik_id"]
                if take_slot(avail, g, cid):
                    zugeordnet[s["matnr"]] = {"group": g, "clinic": cid}
                    placed = True
                    break
            if placed:
                break
        if not placed:
            fail("Interner Fehler: Kein freier Platz mehr gefunden.")
    return zugeordnet, stats

def write_assignments(path, students, zugeordnet, clinic_index):
    out_fields = [
        "matrikelnummer",
        "name",
        "email",
        "zugeordnet_gruppe",
        "zugeordnet_klinik_id",
        "zugeordnet_klinik_name",
        "zugeordnet_stadt",
        "ist_giessen",
        "met_gruppe_prio",
        "met_klinik_prio",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for s in students:
            a = zugeordnet.get(s["matnr"])
            g = a["group"]
            cid = a["clinic"]
            clinic = clinic_index[cid]
            met_group = "none"
            if g == s["g1"]:
                met_group = "1"
            elif g == s["g2"]:
                met_group = "2"
            met_clinic = "none"
            if cid == s["c1"]:
                met_clinic = "1"
            elif cid == s["c2"]:
                met_clinic = "2"
            elif cid == s["c3"]:
                met_clinic = "3"
            w.writerow({
                "matrikelnummer": s["matnr"],
                "name": s["name"],
                "email": s["email"],
                "zugeordnet_gruppe": g,
                "zugeordnet_klinik_id": cid,
                "zugeordnet_klinik_name": clinic["klinik_name"],
                "zugeordnet_stadt": clinic["stadt"],
                "ist_giessen": "true" if clinic["ist_giessen"] else "false",
                "met_gruppe_prio": met_group,
                "met_klinik_prio": met_clinic,
            })

def fail(msg):
    print(f"FEHLER: {msg}")
    sys.exit(1)

def fail_list(prefix, items):
    print(f"FEHLER: {prefix}")
    for it in items:
        print(f"- {it}")
    sys.exit(1)

def prompt_require_outside():
    print("--------------------------------")
    print("Soll erzwungen werden, dass jede Person mindestens eine Klinik-Präferenz außerhalb Gießens angibt? [j/n] (Standard: n)")
    print("Bitte Buchstaben 'j' oder 'n' eingeben und Enter drücken")
    try:
        ans = input().strip().lower()
    except EOFError:
        ans = ""
    if ans in {"j", "ja", "y", "yes"}:
        return True
    return False

def main():
    clinics_path = "kliniken.csv"
    students_path = "studierende.csv"
    print("Lese 'kliniken.cs' ...")
    clinics, clinic_index = read_clinics(clinics_path)
    print("Lese 'studierende.csv' ...")
    require_outside = prompt_require_outside()
    students = read_students(students_path, clinic_index, require_outside)
    print("--------------------------------")
    print("Erstelle Zuteilung ...")
    zugeordnet, stats = assign(students, clinics, clinic_index)
    out_path = "output.csv"
    write_assignments(out_path, students, zugeordnet, clinic_index)
    total = len(students)
    print("Fertig.")
    print(f"Ergebnis gespeichert in: {out_path}")
    print(f"Anzahl Studierende: {total}")
    print(f"Treffer Gruppen-Prio 1: {stats['gruppe_prio1']}")
    print(f"Treffer Gruppen-Prio 2: {stats['gruppe_prio2']}")
    print(f"Treffer Klinik-Prio 1: {stats['klinik_prio1']}")
    print(f"Treffer Klinik-Prio 2: {stats['klinik_prio2']}")
    print(f"Treffer Klinik-Prio 3: {stats['klinik_prio3']}")
    print("--------------------------------")
if __name__ == "__main__":
    main()
