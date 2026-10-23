import math, json, pickle, numpy as np
mu0=4e-7*math.pi; out={}
# ---------------- 1. what has to fit in the bore (dual cavity, as built in the v6 cassette) ----------------
P_W,S_W,CH_H,WALL,SEP=14.4,14.4,7.0,1.1,1.2                      # power and signal ribbon chambers (12-way, 1.0 mm pitch => 12 mm ribbon)
dual_w=17.4; dual_h=2*CH_H+WALL*2+SEP                              # 17.4 x 17.4 as built
diag2=math.hypot(dual_w,dual_h)
tri_w,tri_h=17.4,3*CH_H+WALL*2+2*SEP+0.0; diag3=math.hypot(tri_w,tri_h)
out["cavity"]=dict(dual_envelope_mm=[dual_w,round(dual_h,1)],dual_diagonal_mm=round(diag2,1),min_bore_dual_mm=round(diag2+1.0,1),
   triple_envelope_mm=[tri_w,round(tri_h,1)],triple_diagonal_mm=round(diag3,1),min_bore_triple_mm=round(diag3+1.0,1),
   third_cavity_verdict="not needed: the only heavy conductors (20 A TX pair) stay in the 0.25 m between the head and the neck module; a 20 A silicone pair cannot bend round a 3.5 mm trolley loop (min radius about 15 mm), so it must never ride the telescoping part")
# ---------------- 2/3. tube cascade, nesting order, grades (stiffness of the whole shaft, head on the end) ----------------
def I(od,idd): return math.pi/64*((od*1e-3)**4-(idd*1e-3)**4)
mats={"E-glass/epoxy (GFRP)":(35e9,1.90,False),"carbon/epoxy (CFRP)":(90e9,1.55,True),"aluminium 6061-T6":(69e9,2.70,True)}
OV=0.08; LT=0.45; LOWER=0.40; NPMH=0.084; mhead=2.2
def stiff(order,upper_mat,lower_mat):
    # order: ("big_at_hand",) tube A (OD32/29) at the elbow, tube B (OD28.5/26) at the head end; or ("small_at_hand")
    A=(33.0,30.0); B=(28.5,26.0); t1,t2=(A,B) if order=="big_at_hand" else (B,A)
    xs=np.linspace(0,LT+LT-OV+NPMH+LOWER,2000); Eu,_,_=mats[upper_mat]; El,_,_=mats[lower_mat]; EI=np.zeros_like(xs)
    s1=(0,LT); s2=(LT-OV,2*LT-OV); npm=(2*LT-OV,2*LT-OV+NPMH); low=(npm[1],npm[1]+LOWER)
    EI+=np.where((xs>=s1[0])&(xs<=s1[1]),Eu*I(*t1),0.0)+np.where((xs>=s2[0])&(xs<=s2[1]),Eu*I(*t2),0.0)
    EI+=np.where((xs>=npm[0])&(xs<=npm[1]),El*I(32.0,29.0)*8,0.0)+np.where((xs>=low[0])&(xs<=low[1]),El*I(32.0,29.0),0.0)    # NPM housing counted as 8x a bare tube
    EI=np.maximum(EI,1.0); Lc=xs[-1]; defl=np.trapezoid((Lc-xs)**2/EI,xs); k=1/defl; f=math.sqrt(k/(mhead+0.24))/(2*math.pi)
    return round(k/1000,2),round(f,1),round(mhead*9.81*2*defl*1000,1)
rows=[]
for order in ("small_at_hand","big_at_hand"):
    for um,lm in (("E-glass/epoxy (GFRP)","E-glass/epoxy (GFRP)"),("carbon/epoxy (CFRP)","E-glass/epoxy (GFRP)"),("aluminium 6061-T6","E-glass/epoxy (GFRP)")):
        k,f,d=stiff(order,um,lm); rows.append(dict(nesting=order,telescoping_tubes=um,lower_fixed_tube=lm,stiffness_N_per_mm=k,sway_Hz=f,deflection_mm_at_2g=d))
def tmass(mat,od,idd,l): return round(math.pi/4*(od**2-idd**2)*l*mats[mat][1])
out["tube_grades"]=rows
out["tube_masses_g"]=dict(telescoping_pair_CFRP=tmass("carbon/epoxy (CFRP)",33,30,0.45)+tmass("carbon/epoxy (CFRP)",28.5,26,0.45),telescoping_pair_GFRP=tmass("E-glass/epoxy (GFRP)",33,30,0.45)+tmass("E-glass/epoxy (GFRP)",28.5,26,0.45),lower_fixed_GFRP_0p40m=tmass("E-glass/epoxy (GFRP)",32,29,LOWER))
out["tubes"]=[dict(name="tube A (hand end, biggest)",OD=33.0,ID=30.0,length_m=LT),dict(name="tube B (head end, slides in A)",OD=28.5,ID=26.0,length_m=LT),dict(name="lower fixed tube (neck module to hinge)",OD=32.0,ID=29.0,length_m=LOWER)]
ext=2*LT-OV; col=LT
out["telescoping"]=dict(collapsed_tube_length_m=col,extended_tube_length_m=round(ext,2),stroke_m=round(ext-col,2),trolley_travel_m=round((ext-col)/2,3),min_overlap_m=OV,radial_clearance_B_in_A_mm=round((30.0-28.5)/2,2),
   hinge_to_elbow_socket_collapsed_m=round(LOWER+NPMH+col+0.05,2),hinge_to_elbow_socket_extended_m=round(LOWER+NPMH+ext+0.05,2),ribbon_loop_radius_mm=3.5,cassette_track_mm=450,
   ribbon_length_each_m=round(LOWER+NPMH+ext+0.05+ (ext-col),2),ribbon_note="path from the neck-module tunnel to the elbow + the stroke as folded slack on the trolley")
# ---------------- 4. field along the shaft (why the first part must be non-conductive) ----------------
P=pickle.load(open('kit_v15/LOW/paths.pkl','rb')); PN,G,ZRX=3.6,0.8,3.2
TX=[np.c_[np.vstack([P[k][0],P[k][1]])[::4],np.full(len(np.vstack([P[k][0],P[k][1]])[::4]),ZRX+(6-k)*(PN+G)+PN-0.7)]*1e-3 for k in range(1,7)]
def B(pt):
    b=np.zeros(3)
    for p in TX:
        d=np.diff(p,axis=0); m=(p[:-1]+p[1:])/2; r=pt-m; rn=np.sqrt((r**2).sum(1)+1e-9)[:,None]; b+=mu0/(4*np.pi)*np.sum(np.cross(d,r)/rn**3,axis=0)
    return np.linalg.norm(b/6.0)
alpha=math.radians(47); hinge=np.array([-0.154,0,0.076]); u=np.array([-math.cos(alpha),0,math.sin(alpha)])
ref=B(np.array([0,0,-0.2]))*1e6
fr=[]
for s,lab in ((0.0,"hinge"),(0.15,"0.15 m"),(0.30,"0.30 m"),(0.40,"neck module bottom (chosen)"),(0.484,"neck module top"),(0.70,"tube B"),(0.95,"tube A"),(1.25,"elbow")):
    b=B(hinge+s*u)*1e6; fr.append(dict(where=lab,axial_m=s,B_uT_per_A=round(b,2),percent_of_200mm_target_field=round(100*b/ref,1)))
out["field_along_shaft"]=dict(reference_target_field_uT_per_A_at_200mm=round(ref,1),points=fr)
# ---------------- 5. TX leads (neck module to head, 0.25 m) coupling into the ribbons ----------------
L=0.25; M1=2e-7*L*math.log(11/10); M2=2e-7*L*math.log(19/18); dIdt=500/54e-6
out["tx_to_ribbon"]=dict(lead_length_m=L,added_inductance_uH_two_leads=round(0.5*L*2,2),pct_of_coil=round(100*0.5*L*2/54,2),induced_emf_V_worst_untwisted=round((M1-M2)*dIdt,3),
   note="a 1 mm ribbon conductor pair next to an untwisted TX pair 10 mm away; twisting reduces it further")
# ---------------- 6. thermal of the neck module (always-on boost) ----------------
out["neck_module_thermal"]=dict(dissipation_W=round(4.32+1.1+0.5,1),earlier_rise_K_for_6p8_W=18.5,scaled_rise_K=round(18.5*(4.32+1.1+0.5)/6.83,1),note="clamp 4.32 W (20 A, 400 Hz, 54 uH) + FET/shunt 1.1 + damping 0.5, scaled from the earlier module study")
# ---------------- 7. masses and balance (static torque about the grip, kg m) ----------------
head_parts={"six formers":786,"hub":125,"base plate":49,"cap":14,"hood carrier":58,"ferrite tiles":278,"skirt":61,"cups":23,"pins":1,"receive board SB1R (est)":200,"vault boards (est)":83,"litz copper + insulation (est)":330,"potting and gap fill (est)":216}
mh=sum(head_parts.values())/1000
out["head_mass_kg"]=dict(total=round(mh,2),parts=head_parts,note="'est' = estimate, not weighed")
def torque(alpha_deg=47,head=mh+0.35,batt=0.46,batt_x=-0.20,Lax=1.19):
    a=math.radians(alpha_deg); hx=Lax*math.cos(a)+0.154
    items=[(head,hx),(0.55+0.0,(Lax-LOWER-0.04)*math.cos(a)),(0.30,Lax*0.6*math.cos(a)),(0.18,0.55*Lax*math.cos(a)),(0.40,-0.03),(batt,batt_x),(0.06,-0.08)]   # head+yoke, neck module, tubes, lower tube, elbow+grip, battery, supercap
    return round(sum(m*x for m,x in items),2),round(hx,2)
base=torque()
out["balance"]=dict(baseline_kg_m=base[0],head_horizontal_distance_m=base[1],
 battery_horizontal_under_forearm=torque(batt_x=-0.20)[0],battery_at_45deg=torque(batt_x=-0.12)[0],
 option_steeper_shaft_55deg=torque(55)[0],option_light_formers_minus_0p3kg=torque(head=mh+0.35-0.30)[0],
 option_no_hood_minus_0p28kg=torque(head=mh+0.35-0.28)[0],option_battery_on_rear_boom_0p40m=torque(batt_x=-0.40)[0],
 option_all_together=torque(55,head=mh+0.35-0.30-0.28,batt_x=-0.40)[0],typical_detector_kg_m="1.3-1.7")
# ---------------- 8. ergonomics: lengths, angles, fold ----------------
rows=[]
for H,hg in ((1.55,0.84),(1.75,0.95),(1.95,1.06)):
    for a in (45,50):
        Lax=(hg-0.076)/math.sin(math.radians(a)); rows.append(dict(user_height_m=H,grip_height_m=hg,shaft_angle_deg=a,axial_hinge_to_elbow_socket_m=round(Lax,2)))
out["ergonomics"]=dict(rows=rows,telescope_covers_m=[round(LOWER+NPMH+col+0.05,2),round(LOWER+NPMH+ext+0.05,2)])
fold=dict(lower_tube_socket_OD_mm=39.6,hinge_height_mm=76,cap_top_mm=47.1); fold["clearance_over_cap_mm"]=round(76-19.8-47.1,1)
out["fold"]=fold
out["elbow"]=dict(bend_deg=47,note="the shaft socket is tilted 43 deg off the elbow axis so the grip bar is horizontal when the shaft is at 47 deg; the old 90 deg elbow assumed a vertical shaft",battery_drop_below_grip_mm={"0 deg":0,"20 deg":round(312*math.sin(math.radians(20))),"45 deg":round(312*math.sin(math.radians(45)))})
json.dump(out,open("kit_v19/shaft_calc_v20.json","w"),indent=1,default=float); print(json.dumps(out,default=float)[:6500])
