import streamlit as st
import json
import os
import random
import glob

# --- KONFIGURACJA STRONY ---
# initial_sidebar_state="auto" sprawia, że na telefonie pasek jest schowany, 
# ale w lewym górnym rogu masz strzałkę/hamburger do jego rozwinięcia.
st.set_page_config(
    page_title="Strecke 7 - Trening", 
    layout="wide", 
    initial_sidebar_state="auto"
)

# CSS - Stylizacja
st.markdown("""
    <style>
    /* Ukrywamy stopkę Streamlit i przycisk Deploy, ale ZOSTAWIAMY pasek górny, 
       żebyś miał dostęp do menu na telefonie */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    
    /* Powiększenie czcionki w pytaniu */
    .big-font {
        font-size:24px !important;
        font-weight: bold;
    }
    
    /* Poprawka dla przycisków na mobilkach - żeby były większe */
    div.stButton > button:first-child {
        min-height: 50px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE POMOCNICZE ---

def get_exam_files():
    """Zwraca listę plików pytania*.json posortowaną alfabetycznie."""
    files = glob.glob("pytania*.json")
    files.sort()
    return files

@st.cache_data
def load_all_questions():
    """Ładuje pytania ze wszystkich plików do jednej wielkiej listy (dla wyszukiwarki)."""
    all_q = []
    files = get_exam_files()
    for fname in files:
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    item['source_file'] = fname
                    if 'id' in item:
                        item['global_id'] = f"{fname}_{item['id']}"
                    else:
                        item['global_id'] = f"{fname}_{random.randint(1000,9999)}"
                all_q.extend(data)
        except:
            continue
    return all_q

@st.cache_data
def load_questions_from_file(filename):
    """Ładuje pytania z konkretnego pliku."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for idx, item in enumerate(data):
                item['source_file'] = filename
                if 'id' not in item:
                    item['id'] = idx + 1
                item['global_id'] = f"{filename}_{item['id']}"
            return data
    except FileNotFoundError:
        st.error(f"⚠️ Nie znaleziono pliku: {filename}")
        return []
    except json.JSONDecodeError:
        st.error(f"⚠️ Błąd formatu w pliku: {filename}")
        return []

# --- STAN APLIKACJI (SESSION STATE) ---

if 'q_index' not in st.session_state:
    st.session_state['q_index'] = 0
if 'answered' not in st.session_state:
    st.session_state['answered'] = False
if 'score' not in st.session_state:
    st.session_state['score'] = 0
if 'attempts' not in st.session_state:
    st.session_state['attempts'] = 0
if 'mistakes' not in st.session_state:
    st.session_state['mistakes'] = set()

# --- LOGIKA FILTROWANIA ---

with st.sidebar:
    st.header("🎛️ Panel Sterowania")
    search_query = st.text_input("🔍 Szukaj w pytaniach:", placeholder="np. Maxau, km 300...")
    show_mistakes_only = st.checkbox("🚩 Pokaż tylko moje błędy", value=False)
    st.markdown("---")
    
    exam_files = get_exam_files()
    if not exam_files:
        st.error("Brak plików pytań!")
        st.stop()
        
    if not search_query:
        selected_file = st.selectbox("📂 Wybierz Zestaw:", exam_files, index=0)
    else:
        st.info(f"Szukam frazy: '{search_query}' we wszystkich plikach.")
        selected_file = None

final_questions = []

if search_query:
    all_qs = load_all_questions()
    query = search_query.lower()
    final_questions = [
        q for q in all_qs 
        if query in q['pytanie'].lower() 
        or any(query in odp.lower() for odp in q['odpowiedzi'])
    ]
    if not final_questions:
        st.warning(f"Brak wyników dla: '{search_query}'")
        st.stop()
else:
    final_questions = load_questions_from_file(selected_file)

if show_mistakes_only:
    mistake_questions = [q for q in final_questions if q['global_id'] in st.session_state['mistakes']]
    if not mistake_questions:
        if st.session_state['mistakes']:
            st.success("🎉 W tym zestawie/wyszukiwaniu nie masz błędów!")
        else:
            st.success("🎉 Nie popełniłeś jeszcze żadnych błędów!")
        st.stop()
    else:
        final_questions = mistake_questions
        st.warning(f"Powtarzasz {len(final_questions)} błędnych odpowiedzi.")

# Reset logiki przy zmianie kontekstu
current_ids_hash = str([q['global_id'] for q in final_questions])
if 'last_ids_hash' not in st.session_state:
    st.session_state['last_ids_hash'] = current_ids_hash

if st.session_state['last_ids_hash'] != current_ids_hash:
    st.session_state['q_index'] = 0
    st.session_state['answered'] = False
    st.session_state['last_result'] = None
    st.session_state['last_ids_hash'] = current_ids_hash
    st.rerun()

# --- FUNKCJE NAWIGACJI ---

def go_next():
    if st.session_state['q_index'] < len(final_questions) - 1:
        st.session_state['q_index'] += 1
        st.session_state['answered'] = False
        st.session_state['last_result'] = None

def go_prev():
    if st.session_state['q_index'] > 0:
        st.session_state['q_index'] -= 1
        st.session_state['answered'] = False
        st.session_state['last_result'] = None

def check_answer(selected, correct, q_global_id):
    st.session_state['answered'] = True
    st.session_state['attempts'] += 1
    if selected == correct:
        st.session_state['last_result'] = "correct"
        st.session_state['score'] += 1
        if q_global_id in st.session_state['mistakes']:
            st.session_state['mistakes'].remove(q_global_id)
            st.toast("Poprawiłeś błąd! Pytanie usunięte z listy powtórek.")
    else:
        st.session_state['last_result'] = "wrong"
        st.session_state['mistakes'].add(q_global_id)

# --- WYŚWIETLANIE PYTANIA ---

if st.session_state['q_index'] >= len(final_questions):
    st.session_state['q_index'] = 0

current_q = final_questions[st.session_state['q_index']]
total_q = len(final_questions)

if search_query:
    header_text = f"🔎 WYNIKI WYSZUKIWANIA | Pytanie {st.session_state['q_index'] + 1} / {total_q}"
elif show_mistakes_only:
    header_text = f"🚩 TRYB POPRAWY BŁĘDÓW | Pytanie {st.session_state['q_index'] + 1} / {total_q}"
else:
    file_label = current_q.get('source_file', '').replace('.json', '').replace('pytania', 'ZESTAW ').upper()
    header_text = f"{file_label} | Pytanie {st.session_state['q_index'] + 1} / {total_q}"

st.caption(header_text)
st.markdown(f"<p class='big-font'>{current_q['pytanie']}</p>", unsafe_allow_html=True)

# Layout: Na telefonie col1 i col2 ułożą się pionowo (najpierw zdjęcie, potem odpowiedzi)
col1, col2 = st.columns([1.2, 1])

with col1:
    if current_q.get('obrazek'):
        image_path = os.path.join("zdjecia", current_q['obrazek'])
        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
            with st.expander("🔍 Kliknij, aby powiększyć mapę"):
                st.image(image_path, use_container_width=True)
        else:
            st.warning(f"⚠️ Brak pliku: {current_q['obrazek']}")
    else:
        st.info("Brak załącznika graficznego.")

with col2:
    st.write("### Wybierz odpowiedź:")
    
    if not st.session_state['answered']:
        for opt in current_q['odpowiedzi']:
            btn_key = f"{current_q['global_id']}_{opt}"
            if st.button(opt, use_container_width=True, key=btn_key):
                check_answer(opt, current_q['poprawna'], current_q['global_id'])
                st.rerun()
    else:
        if st.session_state['last_result'] == "correct":
            st.success(f"✅ Brawo! **{current_q['poprawna']}**")
        else:
            st.error(f"❌ Źle. Prawidłowa to: **{current_q['poprawna']}**")
        
        st.markdown("---")
        
    # Nawigacja - pod przyciskami (teraz dostępne również na telefonie w jednej kolumnie)
    st.markdown("---")
    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if st.button("⬅️ Poprzednie", use_container_width=True, disabled=(st.session_state['q_index'] == 0)):
            go_prev()
            st.rerun()
    with nav_col2:
        if st.button("Następne ➡️", use_container_width=True, type="primary", disabled=(st.session_state['q_index'] == len(final_questions) - 1)):
            go_next()
            st.rerun()

# --- PASEK BOCZNY - STATYSTYKI ---
with st.sidebar:
    st.markdown("---")
    st.metric("Twoje Punkty (Sesja)", f"{st.session_state['score']} / {st.session_state['attempts']}")
    mistakes_count = len(st.session_state['mistakes'])
    if mistakes_count > 0:
        st.error(f"🚩 Ilość błędów do poprawy: {mistakes_count}")
    else:
        st.success("Czysto! Brak błędów do poprawy.")
    if st.button("Resetuj sesję"):
        st.session_state['score'] = 0
        st.session_state['attempts'] = 0
        st.session_state['mistakes'] = set()
        st.session_state['answered'] = False
        st.rerun()