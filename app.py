import csv
import io
import sys
import streamlit as st

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

def fail(msg):
    raise ValueError(msg)

def fail_list(prefix, items):
    raise ValueError(prefix + "\n" + "\n".join(f"- {it}" for it in items))

def normalize_group(g):
    if g is None:
        return ""
    return str(g).strip().upper()

def read_clinics_file(file):
    if file is None:
        fail("Bitte 'kliniken.csv' hochladen.")
    text = file.read().decode("utf-8-sig")
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        fail("'kliniken.csv' hat keine Kopfzeile.")
    required_base = ["klinik_id", "klinik_name", "stadt", "ist_giessen"]
    missing_base = [c for c in required_base if c not in reader.fieldnames]
    if missing_base:
        fail("In 'kliniken.csv' fehlen Spalten: " + ", ".join(missing_base))
    cap_cols = [c for c in reader.fieldnames if c.startswith("cap_") and len(c) > 4]
    if not cap_cols:
        fail("'kliniken.csv' enthält keine Kapazitätsspalten. Erwartet: Spalten wie cap_A, cap_B, ...")
    groups_in_header = [c[4:].upper() for c in cap_cols]
    seen = set()
    groups = []
    for g in groups_in_header:
        if g and g not in seen:
            seen.add(g)
            groups.append(g)
    clinics = []
    clinic_index = {}
    rownum = 1
    for row in reader:
        rownum += 1
        cid = (row.get("klinik_id") or "").strip()
        if not cid:
            fail(f"'kliniken.csv': Leere klinik_id in Zeile {rownum}.")
        if cid in clinic_index:
            fail(f"'kliniken.csv': Doppelte klinik_id '{cid}' in Zeile {rownum}.")
        cap = {}
        try:
            for g, col in zip(groups, cap_cols):
                val = int((row.get(col) or "0").strip() or "0")
                if val < 0:
                    fail(f"'kliniken.csv': Kapazität {col} darf nicht negativ sein (klinik_id {cid}, Zeile {rownum}).")
                cap[g] = val
        except ValueError:
            fail(f"'kliniken.csv': Kapazitäten müssen Ganzzahlen sein (klinik_id {cid}, Zeile {rownum}).")
        clinic = {
            "klinik_id": cid,
            "klinik_name": (row.get("klinik_name") or "").strip(),
            "stadt": (row.get("stadt") or "").strip(),
            "ist_giessen": parse_bool(row.get("ist_giessen")),
            "cap": cap,
            "order": len(clinics),
        }
        clinics.append(clinic)
        clinic_index[cid] = clinic
    if not clinics:
        fail("'kliniken.csv' enthält keine Daten.")
    return clinics, clinic_index, groups

def read_students_file(file, clinic_index, require_outside, valid_groups):
    if file is None:
        fail("Bitte 'studierende.csv' hochladen.")
    text = file.read().decode("utf-8-sig")
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        fail("'studierende.csv' hat keine Kopfzeile.")
    required = ["matrikelnummer", "name", "email", "gruppe_prio1", "gruppe_prio2", "klinik_prio1", "klinik_prio2", "klinik_prio3"]
    missing = [c for c in required if c not in reader.fieldnames]
    if missing:
        fail("In 'studierende.csv' fehlen Spalten: " + ", ".join(missing))
    students = []
    idx_by_matnr = {}
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
        if g1 not in valid_groups:
            errors.append(f"Zeile {rownum}: gruppe_prio1 muss eine der vorhandenen Gruppen {sorted(valid_groups)} sein (gefunden: '{row.get('gruppe_prio1')}').")
            continue
        if g2 and g2 not in valid_groups:
            errors.append(f"Zeile {rownum}: gruppe_prio2 muss eine der vorhandenen Gruppen {sorted(valid_groups)} oder leer sein (gefunden: '{row.get('gruppe_prio2')}').")
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

def build_slots(clinics, groups):
    slots = []
    for g in groups:
        for clinic in sorted(clinics, key=lambda x: x["order"]):
            cap = clinic["cap"].get(g, 0)
            for _ in range(cap):
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

def assign(students, clinics, clinic_index, groups):
    slots = build_slots(clinics, groups)
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
                if g in groups and c and take_slot(avail, g, c):
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
            pref_groups = uniq([s["g1"], s["g2"], *groups])
            done = False
            for g in pref_groups:
                if g in groups and take_slot(avail, g, c):
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
        for g in groups:
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

def build_output_csv(students, zugeordnet, clinic_index):
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
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=out_fields)
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
    return buf.getvalue().encode("utf-8")

st.set_page_config(page_title="KliPPs Zuteilung", page_icon="🧩")
st.title("KliPPs Zuteilung")
st.write("""
    Willkommen zur KliPPs Zuteilungsseite! Diese Anwendung ermöglicht die Zuteilung von Studierenden zu Kliniken basierend auf deren Präferenzen und den Kapazitäten der Kliniken. 
    Bitte laden Sie die erforderlichen CSV-Dateien hoch, um die Zuteilung zu starten.
""")

st.download_button("Beispieldatei 'kliniken.csv' herunterladen", data=open('kliniken.csv', 'rb').read(), file_name='kliniken.csv', mime='text/csv')
st.download_button("Beispieldatei 'studierende.csv' herunterladen", data=open('studierende.csv', 'rb').read(), file_name='studierende.csv', mime='text/csv')

col1, col2 = st.columns(2)
with col1:
    file_clinics = st.file_uploader("kliniken.csv", type=["csv"], key="clinics")
with col2:
    file_students = st.file_uploader("studierende.csv", type=["csv"], key="students")

require_outside = st.toggle("Mindestens eine Klinik-Präferenz außerhalb Gießens erzwingen", value=False)
run = st.button("Zuteilung starten")

if run:
    try:
        clinics, clinic_index, groups = read_clinics_file(file_clinics)
        students = read_students_file(file_students, clinic_index, require_outside, set(groups))
        zugeordnet, stats = assign(students, clinics, clinic_index, groups)
        csv_bytes = build_output_csv(students, zugeordnet, clinic_index)
        st.success("Zuteilung abgeschlossen.")
        st.caption(f"Erkannte Gruppen: {', '.join(groups)}")
        st.metric("Anzahl Studierende", len(students))
        m1, m2 = st.columns(2)
        m1.metric("Treffer Gruppen-Prio 1", stats["gruppe_prio1"])
        m2.metric("Treffer Gruppen-Prio 2", stats["gruppe_prio2"])
        m3, m4, m5 = st.columns(3)
        m3.metric("Treffer Klinik-Prio 1", stats["klinik_prio1"])
        m4.metric("Treffer Klinik-Prio 2", stats["klinik_prio2"])
        m5.metric("Treffer Klinik-Prio 3", stats["klinik_prio3"])
        st.download_button("Ergebnis als CSV herunterladen", data=csv_bytes, file_name="zuteilung.csv", mime="text/csv")
    except ValueError as e:
        st.error(str(e))
    except Exception:
        st.error("Unerwarteter Fehler. Bitte Eingaben prüfen oder erneut versuchen.")
