#!/usr/bin/env python3
"""
Training Hub — generazione autonoma dashboard (pipeline cloud, no Mac/Cowork).

Fonti dati:
  - intervals.icu (attivita' completate Garmin+COROS + wellness)
  - TrainingPeaks (calendario allenamenti PIANIFICATI, letto direttamente via
    l'API interna tpapi.trainingpeaks.com con lo stesso meccanismo cookie->token
    usato dal connettore trainingpeaks-mcp gia' installato: niente tp2intervals,
    niente app/Docker da far girare sul Mac. L'unico intervento manuale e'
    aggiornare il secret TP_AUTH_COOKIE quando scade, da browser, quando serve)
  - Strava (solo un paio di dati "social": kudos/achievement dell'ultima attivita')

Logica:
  1. Legge dati grezzi dalle tre fonti.
  2. Calcola in modo DETERMINISTICO (nessuna IA) calorie/macro giorno per giorno,
     applicando le formule dello spec (BMR Mifflin-St Jeor, TSS/FTP per bici,
     kcal/kg/km per corsa, split pasti, dedup attivita' doppie stesso giorno).
  3. Passa i numeri gia' calcolati + regole/formato allo spec a un modello IA
     (Gemini gratis di default, Claude come alternativa a pagamento) che genera
     SOLO l'HTML finale (testo ricette, alternative alimenti, layout), perche'
     quella parte richiede giudizio, non e' meccanica.
  4. Scrive index.html nella working copy del repo (il commit+push lo fa il workflow).

Variabili d'ambiente richieste (impostate come GitHub Secrets):
  INTERVALS_API_KEY, INTERVALS_ATHLETE_ID   (athlete id tipo "i123456", senza prefisso "athlete/")
  GEMINI_API_KEY   (piano gratuito Google AI Studio — provider di default, zero costo)
Opzionali:
  TP_AUTH_COOKIE   (valore del cookie Production_tpAuth di TrainingPeaks; senza
                    questo il calendario pianificato resta vuoto, non blocca il resto)
  STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN   (solo per il dettaglio
                    "social" facoltativo; richiede un'app Strava, che ora serve
                    abbonamento Strava per essere registrata — si puo' saltare del tutto)
  AI_PROVIDER (default: "gemini"; alternativa: "anthropic")
  GEMINI_MODEL (default: gemini-2.5-flash)
  ANTHROPIC_API_KEY, ANTHROPIC_MODEL (default: claude-sonnet-4-5) — usati solo se
                    AI_PROVIDER=anthropic, oppure come fallback automatico se Gemini
                    fallisce e ANTHROPIC_API_KEY e' comunque presente
  ATHLETE_WEIGHT_KG, ATHLETE_HEIGHT_CM, ATHLETE_AGE, ATHLETE_SEX (default dallo spec)
"""

import os
import sys
import json
import re
from datetime import date, datetime, timedelta

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN")

INTERVALS_API_KEY = os.environ.get("INTERVALS_API_KEY")
INTERVALS_ATHLETE_ID = os.environ.get("INTERVALS_ATHLETE_ID")  # es. "i123456"

TP_AUTH_COOKIE = os.environ.get("TP_AUTH_COOKIE")  # valore del cookie Production_tpAuth

AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").strip().lower()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

WEIGHT_KG = float(os.environ.get("ATHLETE_WEIGHT_KG", "75.7"))
HEIGHT_CM = float(os.environ.get("ATHLETE_HEIGHT_CM", "183"))
AGE = int(os.environ.get("ATHLETE_AGE", "29"))
SEX = os.environ.get("ATHLETE_SEX", "m")  # m/f, usato per Mifflin-St Jeor
FTP_W = float(os.environ.get("ATHLETE_FTP_W", "261"))

REPO_ROOT = os.environ.get("REPO_ROOT", ".")
SPEC_PATH = os.path.join(REPO_ROOT, "dashboard-generation-spec.md")
OUTPUT_PATH = os.path.join(REPO_ROOT, "index.html")

WINDOW_PAST_DAYS = 2   # quanti giorni indietro includere (per contesto/dedup)
WINDOW_FUTURE_DAYS = 6  # dashboard mostra ~7 giorni: oggi + prossimi 6


def fail(msg):
    print(f"ERRORE: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Strava — solo un paio di metriche "social" leggere
# ---------------------------------------------------------------------------

def strava_access_token():
    if not (STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET and STRAVA_REFRESH_TOKEN):
        print("Strava non configurato, salto (facoltativo).")
        return None
    r = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": STRAVA_REFRESH_TOKEN,
        },
        timeout=30,
    )
    if r.status_code != 200:
        print(f"Attenzione: refresh token Strava fallito ({r.status_code}): {r.text[:300]}")
        return None
    return r.json().get("access_token")


def strava_social_snippet():
    token = strava_access_token()
    if not token:
        return None
    try:
        r = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={"per_page": 1},
            timeout=30,
        )
        r.raise_for_status()
        acts = r.json()
        if not acts:
            return None
        a = acts[0]
        return {
            "name": a.get("name"),
            "kudos_count": a.get("kudos_count"),
            "achievement_count": a.get("achievement_count"),
            "distance_km": round((a.get("distance") or 0) / 1000, 1),
            "type": a.get("type"),
        }
    except requests.RequestException as e:
        print(f"Attenzione: Strava social snippet non recuperato: {e}")
        return None


# ---------------------------------------------------------------------------
# TrainingPeaks — calendario PIANIFICATO, letto direttamente (no tp2intervals)
#
# Stesso meccanismo cookie->token del connettore trainingpeaks-mcp gia' in uso:
# il cookie di sessione Production_tpAuth viene scambiato per un access token
# OAuth di breve durata (~1h), che si puo' poi usare come Bearer token contro
# l'API interna di TrainingPeaks. Il cookie stesso dura piu' a lungo ma scade
# periodicamente: quando succede, questa funzione fallisce con un log chiaro
# e lo script prosegue comunque (TrainingPeaks non e' mai bloccante).
# Endpoint verificati contro il codice sorgente del connettore ufficiale:
#   GET  /users/v3/token                              (cookie -> access_token)
#   GET  /users/v3/user                                (-> personId = athlete id)
#   GET  /fitness/v6/athletes/{id}/workouts/{start}/{end}
# ---------------------------------------------------------------------------

TP_API_BASE = "https://tpapi.trainingpeaks.com"

TP_WORKOUT_TYPE_VALUE_TO_SPORT = {
    1: "Swim", 2: "Bike", 3: "Run", 4: "Brick", 5: "Crosstrain", 6: "Race",
    7: "DayOff", 8: "MtnBike", 9: "Strength", 10: "Custom", 11: "XCSki",
    12: "Rowing", 13: "Walk", 29: "Strength", 100: "Other",
}


def trainingpeaks_planned_workouts(today):
    """Ritorna { iso_date: [ {title, sport, duration_min, tss_planned,
    distance_km_planned, description}, ... ] } per i planned workout futuri,
    oppure {} se TP_AUTH_COOKIE non e' configurato o la sessione e' scaduta
    (mai bloccante: solo un log di warning)."""
    if not TP_AUTH_COOKIE:
        print("TrainingPeaks non configurato (TP_AUTH_COOKIE assente), salto (facoltativo).")
        return {}

    try:
        token_resp = requests.get(
            f"{TP_API_BASE}/users/v3/token",
            headers={"Cookie": f"Production_tpAuth={TP_AUTH_COOKIE}", "Accept": "application/json"},
            timeout=30,
        )
        if token_resp.status_code == 401:
            print("Attenzione: cookie TrainingPeaks scaduto. Aggiorna il secret TP_AUTH_COOKIE "
                  "(vedi claude/cloud-pipeline-setup.md). Salto il calendario TP per questo run.")
            return {}
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("token", {}).get("access_token")
        if not access_token:
            print("Attenzione: risposta token TrainingPeaks senza access_token, salto.")
            return {}

        auth_headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        user_resp = requests.get(f"{TP_API_BASE}/users/v3/user", headers=auth_headers, timeout=30)
        user_resp.raise_for_status()
        user_data = user_resp.json().get("user", {})
        athlete_id = user_data.get("personId")
        if not athlete_id:
            print("Attenzione: impossibile risolvere l'athlete id TrainingPeaks, salto.")
            return {}

        start_str = today.isoformat()
        end_str = (today + timedelta(days=WINDOW_FUTURE_DAYS)).isoformat()
        wk_resp = requests.get(
            f"{TP_API_BASE}/fitness/v6/athletes/{athlete_id}/workouts/{start_str}/{end_str}",
            headers=auth_headers, timeout=30,
        )
        wk_resp.raise_for_status()
        raw_workouts = wk_resp.json() or []

        by_day = {}
        for w in raw_workouts:
            completed = bool(w.get("completed")) or w.get("totalTime") is not None
            if completed:
                continue  # le sessioni completate arrivano gia' da intervals.icu
            day = str(w.get("workoutDay") or "")[:10]
            if not day:
                continue
            # NOTA: TrainingPeaks esprime la durata pianificata (totalTimePlanned)
            # in ORE decimali, non minuti/secondi (quirk noto della loro API).
            duration_hours = w.get("totalTimePlanned")
            duration_min = round(duration_hours * 60) if duration_hours else None
            sport = TP_WORKOUT_TYPE_VALUE_TO_SPORT.get(w.get("workoutTypeValueId"), "Other")
            by_day.setdefault(day, []).append({
                "title": w.get("title"),
                "sport": sport,
                "duration_min_planned": duration_min,
                "tss_planned": w.get("tssPlanned"),
                "distance_km_planned": round((w.get("distancePlanned") or 0) / 1000, 2) or None,
                "description": w.get("description"),
            })
        return by_day

    except requests.RequestException as e:
        print(f"Attenzione: lettura calendario TrainingPeaks fallita ({e}), proseguo senza.")
        return {}


# ---------------------------------------------------------------------------
# intervals.icu — attivita', wellness, calendario (include import TrainingPeaks)
# ---------------------------------------------------------------------------

def intervals_get(path, params=None):
    if not (INTERVALS_API_KEY and INTERVALS_ATHLETE_ID):
        fail("INTERVALS_API_KEY e INTERVALS_ATHLETE_ID sono obbligatori.")
    url = f"https://intervals.icu/api/v1/athlete/{INTERVALS_ATHLETE_ID}{path}"
    r = requests.get(url, params=params, auth=("API_KEY", INTERVALS_API_KEY), timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_intervals_data(today):
    oldest = (today - timedelta(days=WINDOW_PAST_DAYS)).isoformat()
    newest = (today + timedelta(days=WINDOW_FUTURE_DAYS)).isoformat()

    activities = intervals_get("/activities", {"oldest": oldest, "newest": newest})
    wellness = intervals_get("/wellness", {"oldest": oldest, "newest": newest})
    # /events copre sia i planned workouts creati su intervals.icu sia quelli
    # importati dal calendario TrainingPeaks via tp2intervals.
    events = intervals_get("/events", {"oldest": oldest, "newest": newest})

    return activities, wellness, events


# ---------------------------------------------------------------------------
# Calcolo deterministico calorie/macro (formule dallo spec, NON delegate all'IA)
# ---------------------------------------------------------------------------

def bmr_mifflin(weight_kg, height_cm, age, sex):
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex.lower().startswith("m") else base - 161


def dedupe_same_discipline(day_activities):
    """Se ci sono due sessioni della stessa disciplina lo stesso giorno,
    sono alternative (outdoor/indoor): tieni solo la piu' lunga per il calcolo
    calorico, segnala l'altra in altNote."""
    by_type = {}
    for a in day_activities:
        t = a.get("type", "Other")
        by_type.setdefault(t, []).append(a)

    main_activities = []
    alt_notes = []
    for t, acts in by_type.items():
        if len(acts) == 1:
            main_activities.append(acts[0])
        else:
            acts_sorted = sorted(acts, key=lambda a: a.get("moving_time", 0), reverse=True)
            main_activities.append(acts_sorted[0])
            for alt in acts_sorted[1:]:
                alt_notes.append(
                    f"{t}: presente anche una sessione alternativa "
                    f"({round((alt.get('moving_time') or 0) / 60)} min, "
                    f"probabile indoor/rulli) non conteggiata nel calcolo calorico."
                )
    return main_activities, alt_notes


def session_kcal(activity, weight_kg, ftp_w):
    t = (activity.get("type") or "").lower()
    moving_min = (activity.get("moving_time") or 0) / 60
    distance_km = (activity.get("distance") or 0) / 1000

    if "ride" in t or "bike" in t or "cycl" in t:
        tss = activity.get("icu_training_load") or activity.get("training_load") or 0
        return round((tss / 100) * ftp_w * 3600 / 1000)
    if "run" in t:
        return round(1.0 * weight_kg * distance_km)
    if "swim" in t or "strength" in t or "weight" in t:
        # stima moderata da durata, dichiarata come tale nel footer
        return round(moving_min * 7)
    # fallback generico moderato
    return round(moving_min * 6)


def macro_targets(day_kcal, weight_kg, has_strength, session_kcal_total, longest_session_min):
    protein_g_per_kg = 2.0 if has_strength else 1.8
    protein_g = round(protein_g_per_kg * weight_kg)

    # scala carbo 3.5 (rest) -> 8 (giorni lunghi/intensi) in base a kcal sessione
    if session_kcal_total <= 0:
        carb_g_per_kg = 3.5
    elif session_kcal_total < 500:
        carb_g_per_kg = 5.0
    elif session_kcal_total < 900:
        carb_g_per_kg = 6.5
    else:
        carb_g_per_kg = 8.0
    carb_g = round(carb_g_per_kg * weight_kg)

    kcal_from_protein = protein_g * 4
    kcal_from_carbs = carb_g * 4
    fat_kcal = max(day_kcal - kcal_from_protein - kcal_from_carbs, 0)
    fat_g = round(fat_kcal / 9)

    needs_fueling = longest_session_min > 60 or session_kcal_total > 700

    return {
        "kcal": round(day_kcal),
        "protein_g": protein_g,
        "carb_g": carb_g,
        "fat_g": fat_g,
        "needs_fueling": needs_fueling,
    }


def build_day_payload(iso_day, activities_today, planned_today, planned_today_tp, wellness_today, weight_kg, height_cm, age, sex, ftp_w):
    bmr = bmr_mifflin(weight_kg, height_cm, age, sex)
    main_acts, alt_notes = dedupe_same_discipline(activities_today)

    session_kcal_total = 0
    longest_min = 0
    has_strength = False
    act_summaries = []
    for a in main_acts:
        kcal = session_kcal(a, weight_kg, ftp_w)
        session_kcal_total += kcal
        mins = round((a.get("moving_time") or 0) / 60)
        longest_min = max(longest_min, mins)
        if "strength" in (a.get("type") or "").lower():
            has_strength = True
        act_summaries.append({
            "type": a.get("type"),
            "name": a.get("name"),
            "moving_min": mins,
            "distance_km": round((a.get("distance") or 0) / 1000, 2),
            "training_load": a.get("icu_training_load") or a.get("training_load"),
            "estimated_kcal": kcal,
        })

    day_kcal = bmr * 1.3 + session_kcal_total
    macros = macro_targets(day_kcal, weight_kg, has_strength, session_kcal_total, longest_min)

    return {
        "iso": iso_day,
        "bmr": round(bmr),
        "activities_completed": act_summaries,
        "alt_notes": alt_notes,
        "planned_workouts": planned_today,
        "planned_workouts_trainingpeaks": planned_today_tp,
        "wellness": wellness_today,
        "macro_targets": macros,
        "meal_split": {
            "colazione_pct": 22,
            "pranzo_pct": 33,
            "spuntino_pct": 12,
            "cena_pct": 33,
        },
    }


# ---------------------------------------------------------------------------
# Orchestrazione
# ---------------------------------------------------------------------------

def group_by_day(items, date_field_candidates):
    grouped = {}
    for item in items:
        d = None
        for f in date_field_candidates:
            if item.get(f):
                d = str(item[f])[:10]
                break
        if d:
            grouped.setdefault(d, []).append(item)
    return grouped


def main():
    today = date.today()
    print(f"Generazione dashboard per {today.isoformat()}")

    activities, wellness, events = fetch_intervals_data(today)
    social = strava_social_snippet()
    tp_planned_by_day = trainingpeaks_planned_workouts(today)

    acts_by_day = group_by_day(activities, ["start_date_local", "start_date"])
    wellness_by_day = {w.get("id") or w.get("date"): w for w in wellness}
    events_by_day = group_by_day(events, ["start_date_local", "start_date"])

    days_payload = []
    for offset in range(0, WINDOW_FUTURE_DAYS + 1):
        d = today + timedelta(days=offset)
        iso = d.isoformat()
        day = build_day_payload(
            iso_day=iso,
            activities_today=acts_by_day.get(iso, []),
            planned_today=events_by_day.get(iso, []),
            planned_today_tp=tp_planned_by_day.get(iso, []),
            wellness_today=wellness_by_day.get(iso, {}),
            weight_kg=WEIGHT_KG,
            height_cm=HEIGHT_CM,
            age=AGE,
            sex=SEX,
            ftp_w=FTP_W,
        )
        days_payload.append(day)

    if not os.path.exists(SPEC_PATH):
        fail(f"Spec non trovato in {SPEC_PATH}. Deve essere una copia sincronizzata "
             f"di claude/dashboard-generation-spec.md nel progetto Training Hub.")
    spec_text = open(SPEC_PATH, "r", encoding="utf-8").read()

    payload = {
        "today_iso": today.isoformat(),
        "athlete": {
            "weight_kg": WEIGHT_KG,
            "height_cm": HEIGHT_CM,
            "age": AGE,
            "sex": SEX,
            "ftp_w": FTP_W,
        },
        "days": days_payload,
        "strava_social": social,
    }

    html = generate_html(spec_text, payload)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Scritto {OUTPUT_PATH} ({len(html)} caratteri).")


def _build_prompts(spec_text, payload):
    system_prompt = (
        "Sei il generatore automatico della dashboard settimanale allenamento/nutrizione "
        "per Mirko De Soricellis, eseguito senza supervisione umana dentro una GitHub Action. "
        "Segui ESATTAMENTE lo spec markdown fornito qui sotto per regole nutrizionali, alimenti "
        "reali ammessi, formato HTML, palette colori, comportamento JS (navigazione giorni, "
        "pasti espandibili, dark mode).\n\n"
        "Per gli allenamenti PIANIFICATI nei prossimi giorni, usa il campo "
        "planned_workouts_trainingpeaks di ogni giorno (letto direttamente dal calendario "
        "TrainingPeaks) come fonte primaria; planned_workouts (da intervals.icu) e' un "
        "fallback/integrazione se presente. Se planned_workouts_trainingpeaks e' una lista "
        "vuota per un giorno, vuol dire che TrainingPeaks non ha (ancora) un piano per quel "
        "giorno o che il cookie di sessione era scaduto in questo run: non inventare un "
        "allenamento, mostra il giorno come 'nessun piano disponibile' se non c'e' nient'altro.\n\n"
        "IMPORTANTE: i target di calorie/macro per ciascun giorno ti vengono forniti GIA' "
        "CALCOLATI nel JSON (campo macro_targets di ogni giorno) — sono stati calcolati "
        "deterministicamente in Python con le formule dello spec. NON ricalcolarli e non "
        "cambiarli: usali come vincolo esatto e costruisci solo la composizione dei pasti "
        "(scelta tra gli alimenti reali elencati nello spec, grammature, testo) che rispetti "
        "quei numeri con tolleranza +-10-15%.\n\n"
        "Rispondi SOLO con il codice HTML completo e autosufficiente (CSS+JS inline), "
        "senza alcun testo, spiegazione o code fence prima o dopo.\n\n"
        "=== SPEC ===\n" + spec_text
    )
    user_prompt = (
        "Dati freschi (attivita' completate, planned workouts da TrainingPeaks/intervals.icu, "
        "wellness COROS/Garmin, target macro gia' calcolati) in JSON:\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    return system_prompt, user_prompt


def _clean_html_response(text):
    text = text.strip()
    text = re.sub(r"^```(?:html)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text


def generate_html(spec_text, payload):
    """Genera l'HTML della dashboard. Prova il provider configurato (Gemini
    gratis di default); se fallisce e ANTHROPIC_API_KEY e' comunque presente,
    ripiega automaticamente su Claude come rete di sicurezza."""
    system_prompt, user_prompt = _build_prompts(spec_text, payload)

    primary = AI_PROVIDER if AI_PROVIDER in ("gemini", "anthropic") else "gemini"
    providers_to_try = [primary] + [p for p in ("gemini", "anthropic") if p != primary]

    last_error = None
    for provider in providers_to_try:
        try:
            if provider == "gemini" and GEMINI_API_KEY:
                print("Genero l'HTML con Gemini (gratuito)...")
                return _generate_html_gemini(system_prompt, user_prompt)
            if provider == "anthropic" and ANTHROPIC_API_KEY:
                print("Genero l'HTML con Claude (Anthropic API, a pagamento)...")
                return _generate_html_anthropic(system_prompt, user_prompt)
        except Exception as e:  # noqa: BLE001 - vogliamo provare il fallback su qualsiasi errore
            print(f"Attenzione: provider '{provider}' fallito ({e}), provo l'alternativa se disponibile.")
            last_error = e

    fail(f"Nessun provider IA disponibile o funzionante (ultimo errore: {last_error}). "
         f"Configura GEMINI_API_KEY (gratis, consigliato) o ANTHROPIC_API_KEY.")


def _generate_html_gemini(system_prompt, user_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    r = requests.post(
        url,
        params={"key": GEMINI_API_KEY},
        json={
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"maxOutputTokens": 32000, "temperature": 0.4},
        },
        timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Chiamata Gemini fallita ({r.status_code}): {r.text[:500]}")

    data = r.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Risposta Gemini senza candidates: {json.dumps(data)[:500]}")

    finish_reason = candidates[0].get("finishReason")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    text = _clean_html_response(text)

    if finish_reason == "MAX_TOKENS" and "</html>" not in text.lower():
        raise RuntimeError("Risposta Gemini troncata (MAX_TOKENS) prima di chiudere l'HTML.")
    if "<html" not in text.lower():
        raise RuntimeError("La risposta di Gemini non sembra HTML valido.")
    return text


def _generate_html_anthropic(system_prompt, user_prompt):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 16000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Chiamata Anthropic fallita ({r.status_code}): {r.text[:500]}")

    data = r.json()
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    text = _clean_html_response(text)
    if "<html" not in text.lower():
        raise RuntimeError("La risposta di Claude non sembra HTML valido.")
    return text


if __name__ == "__main__":
    main()
