# KliPPs Zuteilung 🧩

Dieses Projekt automatisiert die **Zuteilung von Studierenden auf Gruppen und Kliniken** im Master KliPPs.  
Die Web-App ist online verfügbar unter: [klinpsych-gruppen.streamlit.app](https://klinpsych-gruppen.streamlit.app/)

---

## ✨ Funktionen
- Automatische faire Verteilung der Studierenden auf Gruppen und Kliniken  
- **Dynamische Gruppenerkennung** aus `kliniken.csv` (z. B. A–D, oder mehr)  
- Berücksichtigung von Präferenzen:
  - Gruppen-Prio 1 und 2
  - Klinik-Prio 1, 2, 3
- Option: „Mindestens eine Klinik-Präferenz außerhalb Gießens“ erzwingen  
- Ausgabe einer Ergebnisdatei (`zuteilung.csv`) mit allen Zuteilungen  
- Deutsche Fehlermeldungen für einfache Bedienung

---

## 📂 Benötigte Dateien

### `studierende.csv`
Spalten (Pflicht):
- `matrikelnummer`  
- `name`  
- `email`  
- `gruppe_prio1`, `gruppe_prio2` (müssen in `kliniken.csv` vorkommen)  
- `klinik_prio1`, `klinik_prio2`, `klinik_prio3` (IDs aus `kliniken.csv`)  

### `kliniken.csv`
Spalten (Pflicht):
- `klinik_id` (Nummer, z. B. `1`)  
- `klinik_name`  
- `stadt`  
- `ist_giessen` (`true`/`false`)  
- Kapazitäten pro Gruppe: `cap_A`, `cap_B`, `cap_C`, …  
👉 Die Gruppen werden automatisch aus den `cap_*`-Spalten erkannt.

---

## 🚀 Nutzung
1. Gehe zu [klinpsych-gruppen.streamlit.app](https://klinpsych-gruppen.streamlit.app/)  
2. Lade **Beispieldateien** herunter (siehe Buttons auf der Seite)  
3. Befülle die CSV-Dateien vollständig  
4. Lade `kliniken.csv` und `studierende.csv` hoch  
5. Starte die Zuteilung  
6. Lade das Ergebnis (`zuteilung.csv`) herunter  

---

## 🛠️ Lokale Entwicklung
Falls du die App selbst hosten oder testen möchtest:

### Voraussetzungen
- Python 3.9+  
- [Streamlit](https://streamlit.io/)  

### Installation
```bash
git clone <repo-url>
cd <repo-name>
pip install -r requirements.txt
