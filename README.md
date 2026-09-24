# Rīgas cilvēku plūsmas karte

Interaktīva Streamlit aplikācija, kas savieno:
- `Riga_grid_1km.geojson` — Rīgas režģi
- `updated_load_static.csv` — cilvēku plūsmas datus

## Palaišana

1. Instalē Python 3.10+.
2. Atver termināli šajā mapē.
3. Izveido virtuālo vidi (ieteicams):

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

4. Instalē bibliotēkas:

```bash
pip install -r requirements.txt
```

5. Palaid:

```bash
streamlit run app.py
```

6. Atvērsies pārlūkprogramma ar interaktīvo karti.

## Failu struktūra

```text
projekts/
├── app.py
├── requirements.txt
├── README.md
├── Riga_grid_1km.geojson
└── updated_load_static.csv
```

## Funkcijas

- Datuma izvēle
- Stundas izvēle
- Unique passers / Passers pārslēgšana
- Kvadrantu krāsošana pēc datu intensitātes
- Kvadranta vērtības hover režīmā
- Detalizēts popup
- Skaitļu rādīšana pašos kvadrantos
- Pilnekrāna kartes režīms
