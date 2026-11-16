"""Pagella dei modelli del council (protocollo v4.1).

Legge council_registro.csv e council_contributi.csv dalla stessa cartella
e scrive "Council - Pagella dei modelli.md". Uso: python council_stats.py
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

# Da configurare
ORCHESTRATORE = "Claude"  # nome del modello che coordina, come scritto nei CSV
AREE = [
    "Contenuti pubblici",
    "Carriera",
    "Clienti",
    "Prodotto e tecnica",
    "Metodo e strumenti AI",
]

BASE = Path(__file__).resolve().parent
SOGLIA_COUNCIL = 10  # [soglia sperimentale] council distinti per modello e gruppo
MARGINE = 0.10  # differenza dalla media degli altri modelli per dire forte o debole
ADOTTATE = {"adottata", "adottata_con_modifiche"}
DECISE = ADOTTATE | {"scartata"}
FONTI_KO = {"fonte_inventata", "fonte_errata"}
FUNZIONI = {
    "verifica": "Verifica dei fatti",
    "ricerca": "Ricerca e fonti",
    "analisi": "Analisi quantitativa",
    "logica": "Logica e coerenza",
    "strategia": "Strategia e decisione",
    "scrittura": "Scrittura e lingua",
    "tecnica": "Tecnica e architettura",
    "visual": "Visual",
}
FONTI_MINUTI = {"misurato", "stimato", "mancante"}
CAMBI = {"", "con_evidenza", "senza_evidenza"}
BUDGET = {"V": 10, "D": 25}  # [obiettivo] minuti del decisore; se c'e una D vale 25

reg = pd.read_csv(BASE / "council_registro.csv", dtype=str, keep_default_na=False)
con = pd.read_csv(BASE / "council_contributi.csv", dtype=str, keep_default_na=False)

errori_lista = []
for v in sorted(set(reg["minuti_fonte"]) - FONTI_MINUTI):
    errori_lista.append(f"minuti_fonte fuori lista: {v}")
for v in sorted(set(con["cambio_posizione"]) - CAMBI):
    errori_lista.append(f"cambio_posizione fuori lista: {v}")
for a in sorted(set(reg["area"]) - set(AREE)):
    errori_lista.append(f"area fuori lista: {a}")
for f in sorted(set(con["funzione"]) - set(FUNZIONI)):
    errori_lista.append(f"funzione fuori lista: {f}")
for c in sorted(set(con["council_id"]) - set(reg["id"])):
    errori_lista.append(f"council senza riga nel registro: {c}")
if errori_lista:
    sys.exit("Correggi i CSV:\n- " + "\n- ".join(errori_lista))

con = con.merge(reg[["id", "area", "modalita", "difficolta"]],
                left_on="council_id", right_on="id", how="left")
con["funzione_nome"] = con["funzione"].map(FUNZIONI)

# Un'idea e unica se in quel council l'ha portata un solo modello.
con["unico"] = con.groupby(["council_id", "idea"])["modello"].transform("nunique").eq(1)


def quota(num, den):
    return num / den if den else None


def metriche(df, filtro):
    """filtro: condizioni sul gruppo, usate anche per contare gli errori noti."""
    councils = df["council_id"].unique()
    errori = df[df["tipo"] == "errore"]
    conf = (errori["verifica"] == "confermato").sum()
    fp = (errori["verifica"] == "falso_positivo").sum()
    base = con[con["council_id"].isin(councils)]
    for col, val in filtro.items():
        base = base[base[col] == val]
    noti = base[(base["tipo"] == "errore") & (base["verifica"] == "confermato")
                & (base["materiale"] == "si")][["council_id", "idea"]].drop_duplicates()
    trovati = errori[(errori["verifica"] == "confermato")
                     & (errori["materiale"] == "si")][["council_id", "idea"]].drop_duplicates()
    proposte = df[(df["tipo"] == "proposta") & df["decisione"].isin(DECISE)]
    adottate = proposte["decisione"].isin(ADOTTATE)
    return {
        "council": len(councils),
        "contributi": len(df),
        "precisione": quota(conf, conf + fp),
        "copertura": quota(len(trovati), len(noti)),
        "adozione": quota(adottate.sum(), len(proposte)),
        "unici": int((adottate & proposte["unico"]).sum()),
        "fonti10": quota(df["verifica"].isin(FONTI_KO).sum() * 10, len(councils)),
        "errate": int(((df["tipo"] == "affermazione") & (df["verifica"] == "errato")).sum()),
    }


def pct(x):
    return "n/d" if x is None else f"{x:.0%}"


def num(x):
    return "n/d" if x is None else f"{x:.1f}".replace(".", ",")


def calcola(colonne):
    risultati = {}
    for chiave, df in con.groupby(["modello"] + colonne):
        filtro = dict(zip(colonne, chiave[1:]))
        risultati[chiave] = metriche(df, filtro)
    return risultati


def tabella(risultati, intestazioni, solo_valutabili=False):
    righe = [
        "| Modello | " + " | ".join(intestazioni)
        + " | Council | Contributi | Stato | Precisione | Copertura relativa | Adozione"
        " | Unici adottati | Fonti errate ogni 10 council | Affermazioni errate |",
        "|---" * (len(intestazioni) + 10) + "|",
    ]
    for chiave, m in sorted(risultati.items()):
        valutabile = m["council"] >= SOGLIA_COUNCIL
        if solo_valutabili and not valutabile:
            continue
        stato = "valutabile" if valutabile else "campione insufficiente"
        righe.append(
            f"| {' | '.join(chiave)} | {m['council']} | {m['contributi']} | {stato}"
            f" | {pct(m['precisione'])} | {pct(m['copertura'])} | {pct(m['adozione'])}"
            f" | {m['unici']} | {num(m['fonti10'])} | {m['errate']} |"
        )
    if len(righe) == 2:
        return f"Nessun incrocio con almeno {SOGLIA_COUNCIL} council per modello [soglia sperimentale]."
    return "\n".join(righe)


def forze_debolezze(risultati, nome_gruppo):
    voci = []
    for chiave, m in risultati.items():
        if m["council"] < SOGLIA_COUNCIL:
            continue
        modello, gruppo = chiave[0], chiave[1:]
        altri = [v for k, v in risultati.items()
                 if k[1:] == gruppo and k[0] != modello and v["council"] >= SOGLIA_COUNCIL]
        for campo, nome, alto_meglio, soglia in [
            ("precisione", "precisione", True, MARGINE),
            ("copertura", "copertura", True, MARGINE),
            ("adozione", "adozione", True, MARGINE),
            ("fonti10", "fonti errate", False, 1.0),
        ]:
            valori = [a[campo] for a in altri if a[campo] is not None]
            if m[campo] is None or not valori:
                continue
            diff = m[campo] - sum(valori) / len(valori)
            if not alto_meglio:
                diff = -diff
            if diff >= soglia:
                voci.append(f"- {modello}, {', '.join(gruppo)}: punto forte su {nome}")
            elif diff <= -soglia:
                voci.append(f"- {modello}, {', '.join(gruppo)}: punto debole su {nome}")
    return voci or [f"- {nome_gruppo}: nessun giudizio, serve un campione di almeno {SOGLIA_COUNCIL} council per modello [soglia sperimentale]."]


ris_area = calcola(["area"])
ris_funz = calcola(["funzione_nome"])
ris_incr = calcola(["area", "funzione_nome"])
ris_diff = calcola(["difficolta"])

altri = con[(con["modello"] != ORCHESTRATORE) & (con["proposta_orchestratore"] == "scartare")]
override = altri["decisione"].isin(ADOTTATE).sum()
rivalutate = (altri["rivalutata"] == "si").sum()

decisioni = reg[reg["modalita"].str.contains("D")]
righe_d = ["| Council | Titolo | Data del riscontro | Esito |", "|---|---|---|---|"]
for _, r in decisioni.iterrows():
    righe_d.append(f"| {r['id']} | {r['titolo']} | {r['data_riscontro'] or 'da fissare'} | {r['esito'] or 'in attesa'} |")

righe_t = ["| Council | Modalità | Minuti | Fonte | Budget [obiettivo] | Stato |", "|---|---|---|---|---|---|"]
for _, r in reg.iterrows():
    budget = BUDGET["D"] if "D" in r["modalita"] else BUDGET["V"]
    if r["minuti_decisore"]:
        stato = "entro il budget" if float(r["minuti_decisore"]) <= budget else "oltre il budget"
    else:
        stato = "non misurato"
    righe_t.append(f"| {r['id']} | {r['modalita']} | {r['minuti_decisore'] or 'n/d'} | {r['minuti_fonte']} | {budget} | {stato} |")

righe_g = ["| Council | Giro | Idee nuove | Nuove e adottate | Errori confermati (righe) | Cambi senza evidenza |",
           "|---|---|---|---|---|---|"]
idee_viste = {}
for (cid, giro), df in con.groupby(["council_id", "giro"]):
    viste = idee_viste.setdefault(cid, set())
    nuove = set(df["idea"]) - viste
    adottate = set(df[df["idea"].isin(nuove) & df["decisione"].isin(ADOTTATE)]["idea"])
    errori = ((df["tipo"] == "errore") & (df["verifica"] == "confermato")).sum()
    cambi = (df["cambio_posizione"] == "senza_evidenza").sum()
    righe_g.append(f"| {cid} | {giro} | {len(nuove)} | {len(adottate)} | {errori} | {cambi} |")
    viste |= set(df["idea"])

oggi = date.today().isoformat()
testo = f"""# Council - Pagella dei modelli

Nota generata da `council_stats.py` il {oggi}: non modificarla a mano.

Council registrati: **{len(reg)}**. Contributi: **{len(con)}**. Giudizio di forza o debolezza solo con almeno **{SOGLIA_COUNCIL} council distinti** per modello e gruppo [soglia sperimentale].

## Punti forti e deboli
### Per area tematica
{chr(10).join(forze_debolezze(ris_area, "Aree"))}

### Per funzione
{chr(10).join(forze_debolezze(ris_funz, "Funzioni"))}

## Per area tematica
{tabella(ris_area, ["Area"])}

## Per funzione
{tabella(ris_funz, ["Funzione"])}

## Area per funzione (solo incroci con campione sufficiente)
{tabella(ris_incr, ["Area", "Funzione"], solo_valutabili=True)}

## Per difficoltà
{tabella(ris_diff, ["Difficoltà"])}

## Filtro dell'orchestratore ({ORCHESTRATORE})
- Proposte degli altri modelli che consigliava di scartare: **{len(altri)}**
- Adottate lo stesso dal decisore (override): **{override}**
- Scartate e poi date per giuste da un'evidenza successiva: **{rivalutate}**

## Esiti delle decisioni (modalità D)
{chr(10).join(righe_d)}

## Tempo del decisore
{chr(10).join(righe_t)}

## Valore dei giri
{chr(10).join(righe_g)}

Le righe di errore contano i modelli che lo hanno segnalato, non gli errori distinti. Un'idea è nuova se non compare nei giri precedenti dello stesso council.
"""

(BASE / "Council - Pagella dei modelli.md").write_text(testo, encoding="utf-8")
print(f"Pagella aggiornata: {len(reg)} council, {len(con)} contributi.")
