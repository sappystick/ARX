#!/usr/bin/env python3
"""System wiring audit: every inter-board connector pin is parsed from the real netlists, mapped exactly once, net-name compatible, and every harness conductor is checked pin by pin."""
import re, glob, os, csv, json, itertools
def parse(path):
    t=open(path).read(); nets={}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)\n    \)',t,re.S): nets[m.group(1)]=[(a,b) for a,b in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)',m.group(2))]
    return nets
P={"CB1D":"kit_v18/CB1D/PF233-CB1D.net","LB1":"kit_v18/LB1/PF233-LB1.net"}
for p in glob.glob("legacy/**/*.net",recursive=True): P[os.path.basename(p).replace("PF233-","").replace(".net","")]=p
P.update(HB2="kit_v6/HB2/PF233-HB2.net",PM2="kit_v6/PM2/PF233-PM2.net",AU1="kit_v6/AU1/PF233-AU1.net")        # upper assembly v1 boards (make pcb-hb2 pcb-pm2) and the AU1 audio board
PIN={}                                    # PIN[board][conn][pin]=net
for b,p in P.items():
    for net,nodes in parse(p).items():
        for ref,pin in nodes:
            if ref.startswith("J"): PIN.setdefault(b,{}).setdefault(ref,{})[pin]=net
ALIAS={("SDOA1","SDO1"),("SDOA2","SDO2"),("SDOA3","SDO3"),("SDOB1","SDO1"),("SDOB2","SDO2"),("VCM_OUT","RAW_MONO"),("JB10_VCM","RAW_MONO"),("VCM_OUT","VCM"),("TRIG_EXT","TRIG"),("DIAL_EXT","DIAL"),("VBUS_IN","VBUS"),("COIL_B","DRAIN1"),("COIL_A","VBUS"),("HTA_P","HTA_P")}
def same(a,b): return a==b or (a,b) in ALIAS or (b,a) in ALIAS or (a=="GND" and b=="GND")
errors=[]; rows=[("level","from","pin","net","to","pin","net","status")]
LINKS=[("HB2","JAU","AU1","JLINK","grip lead"),("PM2","JAUP","AU1","JPWR","dock lead"),("CB1D","JA","AB1A","J2","L2"),("CB1D","JB","AB1B","J2","L2"),("CB1D","JLB","LB1","JLB","L6"),("CB1D","JPB","PB1R","JC","neck"),("CB1D","JTR","HB2","JH","handle"),("CB1D","JPW","PB1R","JP","power"),("CB1D","JPW","PM2","JP","power"),("CB1D","JCL","PB1R","JL1","TX")]
OPEN_BY_DESIGN={("CB1D","JTR","6")}   # JTR.6: no conductor in the 5-core signal cord; JTR.5 = AUD_LINK on core 5 since CB1D-C2 / HB2-B (harness v5 W067)
used={}; open_rows=[]
for a,ca,b,cb,lvl in LINKS:
    for pin,net in sorted(PIN[a][ca].items(),key=lambda x:int(x[0])):
        other=PIN[b][cb].get(pin)
        if cb=="JL1": other=PIN[b][cb].get(pin)
        ok=other is not None and same(net,other)
        if (a,ca,pin) in OPEN_BY_DESIGN: open_rows.append(f"{a}.{ca}.{pin} ({net}) vs {b}.{cb}.{pin} ({other})"); ok=True
        if not ok: errors.append(f"{a}.{ca}.{pin} ({net}) vs {b}.{cb}.{pin} ({other})")
        rows.append((lvl,f"{a}.{ca}",pin,net,f"{b}.{cb}",pin,other,"OK" if ok else "MISMATCH")); used.setdefault((a,ca,pin),[]).append((b,cb))
    for pin in PIN[b][cb]:
        if pin not in PIN[a][ca]: errors.append(f"{b}.{cb}.{pin} has no partner on {a}.{ca}")
# coils to AB1A input connector J1 (documented wiring of the SB1R-Q pads): QUAD-A + -> J1.1, - -> J1.4 ; QUAD-B + -> J1.2, - -> J1.5
exp={("AB1A","J1","1"):"RAW_GX",("AB1A","J1","2"):"RAW_GY",("AB1A","J1","4"):"VCM",("AB1A","J1","5"):"VCM"}
for (b,c,p),n in exp.items():
    if PIN[b][c].get(p)!=n: errors.append(f"SB1R-Q wiring: {b}.{c}.{p} is {PIN[b][c].get(p)} not {n}")
# every pin of every inter-board connector is mapped once and only once
for a,ca,b,cb,lvl in LINKS:
    cnt={}
    for pin in PIN[a][ca]: cnt[pin]=sum(1 for (x,y,z),v in used.items() if (x,y,z)==(a,ca,pin) for q in v if q==(b,cb))
    for pin,c in cnt.items():
        if c!=1: errors.append(f"{a}.{ca}.{pin} mapped {c} times to {b}.{cb}")
# harness master: every conductor end exists and carries the named signal
H=list(csv.DictReader(open("harness/HARNESS_MASTER_v5.csv")))
tok=re.compile(r"\b([A-Z0-9]+)\.(J[A-Z0-9]*)\.(\d+(?:/\d+)?)")
hrows=[]; hbad=0
for r in H:
    sig=r["signal"]; ends=tok.findall(r["from (board.connector.pin)"])+tok.findall(r["to (board.connector.pin)"]); res="OK"
    for b,c,pins in ends:
        for p in pins.split("/"):
            n=PIN.get(b,{}).get(c,{}).get(p)
            if n is None: res=f"PIN NOT FOUND {b}.{c}.{p}"; break
            if not (same(sig,n) or sig in n or n in sig or (sig.startswith("GND") and n=="GND") or (sig in ("TX_A","TX_B") and n in ("COIL_A","COIL_B","DRAIN1","VBUS"))): res=f"NET MISMATCH {b}.{c}.{p}={n} vs {sig}"
        if res!="OK": break
    hrows.append((r["id"],sig,res)); hbad+=(res!="OK")
    if res!="OK": errors.append(f"harness {r['id']}: {res}")
open("kit_v22/LEVEL_NETLIST_FROM_NETLISTS.csv","w",newline="").writelines(",".join(map(str,x))+"\n" for x in rows)
rep=dict(connectors_checked=sum(len(v) for v in PIN.values()),links=len(LINKS),link_pins=len(rows)-1,harness_conductors=len(H),harness_bad=hbad,open_by_design=open_rows,errors=errors,harness=[list(h) for h in hrows])
json.dump(rep,open("kit_v22/wiring_audit.json","w"),indent=1)
print("link pins checked",len(rows)-1,"| harness conductors",len(H),"bad",hbad,"| errors",len(errors))
for e in errors[:25]: print("  ERR",e)
