#!/usr/bin/env python3
"""Calendario stagionale de-trendizzato + t-test, selezione per affidabilita'.
Auto-contenuto: scarica i dati (Yahoo via curl), calcola, genera calendario.html
per la PROSSIMA settimana di borsa. Nessun input esterno."""
import json, subprocess, time, datetime as dt, math, os, html
import numpy as np, pandas as pd
from scipy import stats

OUT = os.path.dirname(os.path.abspath(__file__))

BASKET = [
 ("Apple","AAPL","USA"),("Microsoft","MSFT","USA"),("Amazon","AMZN","USA"),
 ("Alphabet","GOOGL","USA"),("Nvidia","NVDA","USA"),("JPMorgan","JPM","USA"),
 ("ExxonMobil","XOM","USA"),("Johnson&Johnson","JNJ","USA"),("Procter&Gamble","PG","USA"),
 ("Coca-Cola","KO","USA"),("Walmart","WMT","USA"),("Home Depot","HD","USA"),
 ("UnitedHealth","UNH","USA"),("Caterpillar","CAT","USA"),
 ("SAP","SAP.DE","Europa"),("Siemens","SIE.DE","Europa"),("LVMH","MC.PA","Europa"),
 ("L'Oreal","OR.PA","Europa"),("Nestle","NESN.SW","Europa"),("Novo Nordisk","NVO","Europa"),
 ("ASML","ASML","Europa"),("Shell","SHEL.L","Europa"),("Novartis","NVS","Europa"),
 ("TSMC","TSM","Asia"),("Toyota","TM","Asia"),("Samsung Elec","005930.KS","Asia"),
 ("Tencent","0700.HK","Asia"),("Infosys","INFY","Asia"),
 ("Enel","ENEL.MI","Italia"),("Eni","ENI.MI","Italia"),("Intesa Sanpaolo","ISP.MI","Italia"),
 ("Generali","G.MI","Italia"),("UniCredit","UCG.MI","Italia"),("Campari","CPR.MI","Italia"),
]

def fetch(tk):
    url=(f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}"
         f"?range=25y&interval=1d&includeAdjustedClose=true")
    o=subprocess.run(["curl","-s","--max-time","30","-H","User-Agent: Mozilla/5.0",url],
                     capture_output=True,text=True)
    j=json.loads(o.stdout); res=j["chart"]["result"][0]
    ts=res["timestamp"]; adj=res["indicators"]["adjclose"][0]["adjclose"]
    rec=[(time.strftime("%Y-%m-%d",time.gmtime(t)),a) for t,a in zip(ts,adj) if a is not None]
    df=pd.DataFrame(rec,columns=["date","adjclose"]); df["date"]=pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()

# --- date target: prossima settimana ---
today=dt.date.today()
nextmon=today+dt.timedelta(days=(7-today.weekday()) or 7)
TARGETS=[nextmon+dt.timedelta(days=i) for i in range(5)]
WD=["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì"]
LAST=nextmon.year-1
WINDOWS=[("10a",LAST-9,LAST,0.40,7),("15a",LAST-14,LAST,0.35,10),("20a",LAST-19,LAST,0.25,14)]
TOL=pd.Timedelta(days=4)
print(f"Settimana target {TARGETS[0]} -> {TARGETS[-1]}  (finestre fino {LAST})")

# --- scarica ---
series={}
for name,tk,area in BASKET:
    try:
        series[tk]=fetch(tk); series[tk]["ret"]=series[tk]["adjclose"].pct_change()
        time.sleep(0.5)
    except Exception as e:
        print("skip",tk,e)

def wmean(df,y0,y1):
    m=(df.index.year>=y0)&(df.index.year<=y1); return df["ret"][m].mean()
def excess(df,mo,dy,y0,y1):
    drift=wmean(df,y0,y1); ex=[]; idx=df.index
    for y in range(y0,y1+1):
        try: t=pd.Timestamp(y,mo,dy)
        except ValueError: continue
        p=idx.get_indexer([t],method="nearest")[0]
        if p<=0 or abs(idx[p]-t)>TOL: continue
        r=df["ret"].iloc[p]
        if pd.notna(r): ex.append(r-drift)
    return np.array(ex)
def wstats(df,mo,dy,y0,y1,mino):
    ex=excess(df,mo,dy,y0,y1)
    return None if len(ex)<mino else (float((ex>0).mean()),float(ex.mean()),len(ex))
def rel(df,mo,dy,y0,y1):
    ex=excess(df,mo,dy,y0,y1); n=len(ex)
    if n<3: return None
    m=float(ex.mean()); sd=float(ex.std(ddof=1))
    if sd==0: t,p=np.inf,0.0
    else: t=m/(sd/np.sqrt(n)); p=float(2*stats.t.sf(abs(t),n-1))
    return dict(p=p,std=sd,worst=float(ex.min()),t=float(t),n=n)

results={}
for tgt in TARGETS:
    rows=[]
    for name,tk,area in BASKET:
        if tk not in series: continue
        df=series[tk]; w={}; ok=True
        for lab,y0,y1,pw,mino in WINDOWS:
            s=wstats(df,tgt.month,tgt.day,y0,y1,mino)
            if s is None: ok=False; break
            w[lab]=s
        if not ok: continue
        R=rel(df,tgt.month,tgt.day,LAST-19,LAST)
        rows.append(dict(name=name,ticker=tk,area=area,
            wr10=w["10a"][0],ret10=w["10a"][1],n10=w["10a"][2],
            wr15=w["15a"][0],ret15=w["15a"][1],
            wr20=w["20a"][0],ret20=w["20a"][1],
            wwr=sum(pw*w[l][0] for l,_,_,pw,_ in WINDOWS),
            wret=sum(pw*w[l][1] for l,_,_,pw,_ in WINDOWS),
            pval=R["p"],std=R["std"],worst=R["worst"],tstat=R["t"],n20=R["n"]))
    d=pd.DataFrame(rows)
    d["poskey"]=(d["wret"]<=0).astype(int)
    d=d.sort_values(["poskey","pval"]).reset_index(drop=True)
    d["day_signal"]=bool(d.iloc[0]["wret"]>0 and d.iloc[0]["pval"]<0.05)
    results[tgt]=d

# --- HTML ---
def pct(x,s=False): return (f"{x*100:+.2f}%" if s else f"{x*100:.1f}%")
def cr(x): return "pos" if x>=0 else "neg"
def rtag(p): return ("Significativo","sig") if p<0.05 else (("Debole","weak") if p<0.10 else ("Non significativo","ns"))
def pf(p): return "&lt;0.001" if p<0.001 else f"{p:.3f}"
MESI=["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"]
sett=f"{TARGETS[0].day}–{TARGETS[-1].day} {MESI[TARGETS[-1].month-1]} {TARGETS[-1].year}"

cards=[]
for gi,tgt in enumerate(TARGETS):
    d=results[tgt]; top=d.iloc[0]; signal=bool(top["day_signal"])
    wr=""
    for lab,a,b in [("10 anni","wr10","ret10"),("15 anni","wr15","ret15"),("20 anni","wr20","ret20")]:
        wr+=f'<tr><th>{lab}</th><td class="num">{pct(top[a])}</td><td class="num {cr(top[b])}">{pct(top[b],1)}</td></tr>'
    rk=""
    for i,r in d.head(6).iterrows():
        strength=min(-math.log10(max(r["pval"],1e-4))/4.0,1.0)*100
        lead=" lead" if i==0 else ""; _,rc=rtag(r["pval"])
        rk+=(f'<li class="rk{lead}"><span class="rk-pos">{i+1}</span>'
             f'<span class="rk-name">{html.escape(r["name"])}<em>{html.escape(r["ticker"])}</em></span>'
             f'<span class="rk-metrics"><b>{pct(r["wwr"])}</b> WR · <b class="{cr(r["wret"])}">{pct(r["wret"],1)}</b> · '
             f'<span class="pdot {rc}">p&nbsp;{pf(r["pval"])}</span></span>'
             f'<span class="rk-bar"><i style="width:{max(6,strength):.0f}%"></i></span></li>')
    lab="Titolo selezionato" if signal else "Candidato meno debole"
    nos="" if signal else '<div class="nosig">⚠ Nessun segnale statisticamente affidabile per questo giorno (nessun titolo con p&lt;0.05). Il nome sotto è solo il meno debole: da non operare.</div>'
    cards.append(f'''<article class="card{'' if signal else ' card-nosig'}">
<header class="card-h"><div class="day"><span class="dow">{WD[gi]}</span><span class="date">{tgt.strftime("%d.%m.%Y")}</span></div>
<div class="pick"><span class="pick-lab">{lab}</span><span class="pick-name">{html.escape(top["name"])}</span>
<span class="pick-tk">{html.escape(top["ticker"])} · {html.escape(top["area"])}</span></div></header>{nos}
<div class="head-stats"><div class="hs"><span class="hs-v">{pct(top["wwr"])}</span><span class="hs-l">Win Rate vs media (pond.)</span></div>
<div class="hs"><span class="hs-v {cr(top["wret"])}">{pct(top["wret"],1)}</span><span class="hs-l">Extra-rendimento medio (pond.)</span></div>
<div class="hs"><span class="hs-v accentv">{top["tstat"]:+.2f}</span><span class="hs-l">Statistica t (20a)</span></div></div>
<div class="rel rel-{rtag(top["pval"])[1]}"><span class="rel-pill">{rtag(top["pval"])[0]}</span>
<span class="rel-item"><b>p&nbsp;{pf(top["pval"])}</b><i>t-test 20a (n={int(top["n20"])})</i></span>
<span class="rel-item"><b>{top["std"]*100:.2f}%</b><i>dev. std giornaliera</i></span>
<span class="rel-item"><b class="{cr(top["worst"])}">{pct(top["worst"],1)}</b><i>anno peggiore</i></span></div>
<div class="card-body"><div class="win-table"><div class="wt-cap">Profilo multi-orizzonte — {html.escape(top["ticker"])}</div>
<table><thead><tr><th>Finestra</th><th class="num">Win Rate</th><th class="num">Extra-rend.</th></tr></thead><tbody>{wr}</tbody></table></div>
<div class="rank"><div class="rk-cap">Classifica per affidabilità</div><ol>{rk}</ol></div></div></article>''')

CSS="""*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Helvetica Neue",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.5}
:root{--bg:#e9ebf0;--surface:#fff;--surface2:#f4f5f8;--ink:#141821;--muted:#5c6675;--faint:#8a93a2;--line:#dce0e8;--line2:#e7eaf0;--accent:#a8781f;--accent-soft:#f2e4c4;--pos:#137a54;--neg:#bd3646}
@media(prefers-color-scheme:dark){:root{--bg:#0c0f15;--surface:#141922;--surface2:#1a212c;--ink:#e7ebf2;--muted:#8d97a8;--faint:#6b7688;--line:#232b38;--line2:#1e2530;--accent:#d6a53c;--accent-soft:#3a3016;--pos:#38c78c;--neg:#e26374}}
:root[data-theme=dark]{--bg:#0c0f15;--surface:#141922;--surface2:#1a212c;--ink:#e7ebf2;--muted:#8d97a8;--faint:#6b7688;--line:#232b38;--line2:#1e2530;--accent:#d6a53c;--accent-soft:#3a3016;--pos:#38c78c;--neg:#e26374}
:root[data-theme=light]{--bg:#e9ebf0;--surface:#fff;--surface2:#f4f5f8;--ink:#141821;--muted:#5c6675;--faint:#8a93a2;--line:#dce0e8;--line2:#e7eaf0;--accent:#a8781f;--accent-soft:#f2e4c4;--pos:#137a54;--neg:#bd3646}
.num{font-family:ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}.pos{color:var(--pos)}.neg{color:var(--neg)}.accentv{color:var(--accent)}
.wrap{max-width:940px;margin:0 auto;padding:clamp(20px,4vw,48px) clamp(16px,4vw,40px) 64px}
.mast{border-bottom:2px solid var(--ink);padding-bottom:20px}.eyebrow{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);font-weight:700}
.mast h1{font-family:Georgia,serif;font-weight:600;font-size:clamp(28px,5vw,44px);line-height:1.05;margin:.28em 0 .12em;text-wrap:balance}
.mast .sub{color:var(--muted);font-size:15px;max-width:62ch}.meta-strip{display:flex;flex-wrap:wrap;gap:8px 10px;margin-top:18px}
.chip{font-size:11.5px;background:var(--surface2);border:1px solid var(--line);color:var(--muted);padding:5px 10px;border-radius:2px}.chip b{color:var(--ink)}
.cards{display:flex;flex-direction:column;gap:18px;margin-top:26px}.card{background:var(--surface);border:1px solid var(--line);border-radius:6px;overflow:hidden;box-shadow:0 6px 22px rgba(20,24,33,.06)}
.card-h{display:flex;justify-content:space-between;gap:16px;padding:16px 20px;border-bottom:1px solid var(--line2);background:var(--surface2)}
.dow{font-family:Georgia,serif;font-size:22px;font-weight:600}.date{font-size:12px;color:var(--faint);font-family:ui-monospace,monospace}
.pick{display:flex;flex-direction:column;text-align:right;justify-content:center;border-left:3px solid var(--accent);padding-left:16px}
.pick-lab{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700}.pick-name{font-size:19px;font-weight:650}.pick-tk{font-size:12px;color:var(--muted);font-family:ui-monospace,monospace}
.card-nosig .pick{border-left-color:var(--faint)}.card-nosig .pick-lab,.card-nosig .pick-name{color:var(--muted)}.card-nosig{opacity:.92}
.nosig{font-size:12px;color:var(--ink);background:var(--accent-soft);padding:9px 20px;border-bottom:1px solid var(--line2)}
.head-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line2)}.hs{background:var(--surface);padding:14px 20px;display:flex;flex-direction:column;gap:2px}
.hs-v{font-size:24px;font-weight:600;font-family:ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}.hs-l{font-size:11px;color:var(--muted)}
.rel{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:11px 20px;border-top:1px dashed var(--line);border-bottom:1px solid var(--line2);background:var(--surface2)}
.rel-pill{font-size:11px;font-weight:700;padding:3px 10px;border-radius:99px;border:1px solid currentColor}.rel-sig .rel-pill{color:var(--pos)}.rel-weak .rel-pill{color:var(--accent)}.rel-ns .rel-pill{color:var(--muted)}
.rel-item{display:flex;flex-direction:column;line-height:1.25}.rel-item b{font-family:ui-monospace,Menlo,monospace;font-size:14px;font-variant-numeric:tabular-nums}.rel-item i{font-style:normal;font-size:10px;color:var(--faint)}
.pdot{font-family:ui-monospace,monospace;font-size:11px}.pdot.sig{color:var(--pos);font-weight:600}.pdot.weak{color:var(--accent)}.pdot.ns{color:var(--faint)}
.card-body{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr)}@media(max-width:640px){.card-body{grid-template-columns:1fr}}
.win-table{padding:16px 20px;border-right:1px solid var(--line2)}.wt-cap,.rk-cap{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);font-weight:700;margin-bottom:10px}
.win-table table{width:100%;border-collapse:collapse;font-size:13.5px}.win-table thead th{font-size:11px;color:var(--faint);border-bottom:1px solid var(--line);padding-bottom:8px;text-align:right}.win-table thead th:first-child{text-align:left}
.win-table td{padding:6px 0;text-align:right}.win-table th{text-align:left;padding:6px 0}.win-table tbody th{font-weight:600}
.rank{padding:16px 20px}.rank ol{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px}
.rk{display:grid;grid-template-columns:18px 1fr auto;grid-template-areas:"pos name metrics" "pos bar bar";gap:2px 10px;align-items:center;padding:6px 8px;border-radius:4px}
.rk.lead{background:var(--accent-soft)}.rk-pos{grid-area:pos;font-family:ui-monospace,monospace;font-size:12px;color:var(--faint);text-align:center}.rk.lead .rk-pos{color:var(--accent);font-weight:700}
.rk-name{grid-area:name;font-size:13.5px;font-weight:550;display:flex;gap:7px;align-items:baseline}.rk-name em{font-style:normal;font-family:ui-monospace,monospace;font-size:11px;color:var(--faint)}
.rk-metrics{grid-area:metrics;font-size:12px;color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums}.rk-metrics b{color:var(--ink)}
.rk-bar{grid-area:bar;height:3px;background:var(--line2);border-radius:2px;overflow:hidden;margin-top:2px}.rk-bar i{display:block;height:100%;background:var(--muted)}.rk.lead .rk-bar i{background:var(--accent)}
.foot{margin-top:34px;padding-top:20px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);display:flex;flex-direction:column;gap:12px}.foot h3{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink);margin:0 0 4px}.foot p{margin:0;max-width:80ch}
.warn{border-left:3px solid var(--accent);padding:10px 14px;background:var(--surface2);border-radius:0 4px 4px 0}"""

page=f'''<title>Calendario Stagionale — Paniere Globale</title><style>{CSS}</style>
<div class="wrap"><div class="mast"><div class="eyebrow">Analisi Quantitativa · Selezione per Affidabilità</div>
<h1>Calendario Stagionale del Paniere Globale</h1>
<p class="sub">Per ogni giorno della prossima settimana, il titolo con il pattern stagionale statisticamente più solido — de-trendizzato e validato con t-test. I giorni senza segnale affidabile sono marcati.</p>
<div class="meta-strip"><span class="chip"><b>{len(series)}</b> titoli globali (USA · Europa · Italia · Asia)</span>
<span class="chip">De-trend + <b>t-test</b> 20a</span><span class="chip">Selezione: <b>miglior p-value</b> (extra-rend&gt;0)</span>
<span class="chip">Aggiornato <b>{today.strftime("%d/%m/%Y")}</b></span><span class="chip">Settimana <b>{sett}</b></span></div></div>
<div class="cards">{"".join(cards)}</div>
<div class="foot"><div><h3>Metodologia</h3><p>Per ogni titolo e giorno di calendario si prende il rendimento giornaliero (chiusura/chiusura, prezzi adjusted) del giorno di borsa più vicino (±4gg) negli ultimi 20 anni; si sottrae il rendimento medio del titolo nella finestra (de-trending) ottenendo il rendimento in eccesso. Il t-test (due code, campione 20a) misura se l'extra-rendimento è diverso da zero. Selezione = miglior p-value tra i titoli con extra-rendimento positivo. Fonte: Yahoo Finance.</p></div>
<div class="warn"><h3 style="color:var(--accent)">Avvertenza</h3><p>Studio statistico retrospettivo a fini informativi/educativi, <b>non</b> consulenza finanziaria. Campioni piccoli (fino a 20 osservazioni), forte rischio di test multiplo (34 titoli × 5 giorni ≈ 170 test: ~8 falsi positivi attesi a p&lt;0.05), survivorship bias del paniere. La stagionalità passata non predice i rendimenti futuri.</p></div></div></div>'''

path=os.path.join(OUT,"calendario.html")
open(path,"w").write(page)
print("scritto",path,len(page),"bytes | titoli:",len(series))
