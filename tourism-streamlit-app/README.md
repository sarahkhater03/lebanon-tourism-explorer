# Lebanon Tourism Explorer

An interactive Streamlit page on where Lebanon's tourism infrastructure (hotels, restaurants and cafes) is located across 1,137 towns. Built for MSBA 325 by Sarah Khater, as a follow-up to my Plotly assignment.

**Live app:** https://lebanon-tourism-explorer.streamlit.app/

## What's on the page
- **Two linked controls:** a Governorate selectbox that sets which options appear in the District multiselect. Keep a single district to drill down from districts to individual towns.
- **Charts:** hotels ranked by district (or by town when drilled down), a restaurants-vs-cafes bubble scatter colored by hotel presence, and a Tourism Index distribution.
- **Insights and design justifications** are on the page itself.

## Data
`data/tourism_lebanon.csv` is the *Tourism-Lebanon-2023* dataset (Impact Open Data, linked by AUB CODEC). The app cleans up double-encoded place names (for example, `ZahlÃ©` becomes `Zahlé`) and maps each district to its governorate.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
