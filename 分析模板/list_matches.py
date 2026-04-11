import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('d:/work/workbuddy/足球预测/分析模板/matches_full_2026-03-15.json', encoding='utf-8') as f:
    data = json.load(f)

out = []
for m in data:
    oz_list = m.get('\u6b27\u8d54\u6570\u636e', {}).get('\u6b27\u8d54\u5217\u8868', [])
    if not oz_list:
        continue
    inits, reals = [], []
    for x in oz_list:
        try:
            ih_ = float(x.get('\u521d\u76d8\u80dc',0) or 0)
            id_ = float(x.get('\u521d\u76d8\u5e73',0) or 0)
            ia_ = float(x.get('\u521d\u76d8\u8d1f',0) or 0)
            rh_ = float(x.get('\u5373\u65f6\u80dc',0) or 0)
            rd_ = float(x.get('\u5373\u65f6\u5e73',0) or 0)
            ra_ = float(x.get('\u5373\u65f6\u8d1f',0) or 0)
            if ih_ and id_ and ia_ and rh_ and rd_ and ra_:
                inits.append((ih_, id_, ia_))
                reals.append((rh_, rd_, ra_))
        except:
            pass
    if not inits:
        continue
    n = len(inits)
    ih = [x[0] for x in inits]; rh = [x[0] for x in reals]
    idraw = [x[1] for x in inits]; rdraw = [x[1] for x in reals]
    ia = [x[2] for x in inits]; ra = [x[2] for x in reals]
    hc = [rh[i]-ih[i] for i in range(n)]
    dc = [rdraw[i]-idraw[i] for i in range(n)]
    ac = [ra[i]-ia[i] for i in range(n)]
    h_down = sum(1 for x in hc if x < 0)
    d_up   = sum(1 for x in dc if x > 0)
    a_up   = sum(1 for x in ac if x > 0)
    rh_avg = sum(rh)/n
    rd_avg = sum(rdraw)/n
    ra_avg = sum(ra)/n
    dc_avg = sum(dc)/n
    id_avg = sum(idraw)/n
    dc_pct = dc_avg / id_avg * 100 if id_avg else 0
    da = m.get('\u6570\u636e\u5206\u6790', {})
    out.append({
        '\u7f16\u53f7': m.get('\u7f16\u53f7',''),
        '\u8054\u8d5b': m.get('\u8054\u8d5b',''),
        '\u4e3b\u961f': m.get('\u4e3b\u961f',''),
        '\u5ba2\u961f': m.get('\u5ba2\u961f',''),
        '\u4e3b\u80dc\u4e0b\u964d\u5bb6\u6570': h_down,
        '\u5e73\u5c40\u4e0a\u5347\u5bb6\u6570': d_up,
        '\u5ba2\u80dc\u4e0a\u5347\u5bb6\u6570': a_up,
        '\u5373\u65f6\u4e3b\u80dc\u5747\u503c': round(rh_avg,2),
        '\u5373\u65f6\u5e73\u5c40\u5747\u503c': round(rd_avg,2),
        '\u5373\u65f6\u5ba2\u80dc\u5747\u503c': round(ra_avg,2),
        '\u5e73\u5c40\u53d8\u5316%': round(dc_pct,1),
        '\u6fb3\u95e8\u63a8\u8350': da.get('\u6fb3\u95e8\u63a8\u8350',''),
        '\u516c\u53f8\u6570': n,
    })

with open('d:/work/workbuddy/足球预测/分析模板/verify_out.json','w',encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

for row in out:
    en = row['\u7f16\u53f7']
    lq = row['\u8054\u8d5b']
    hm = row['\u4e3b\u961f']
    aw = row['\u5ba2\u961f']
    hd = row['\u4e3b\u80dc\u4e0b\u964d\u5bb6\u6570']
    du = row['\u5e73\u5c40\u4e0a\u5347\u5bb6\u6570']
    rh = row['\u5373\u65f6\u4e3b\u80dc\u5747\u503c']
    rd = row['\u5373\u65f6\u5e73\u5c40\u5747\u503c']
    ra = row['\u5373\u65f6\u5ba2\u80dc\u5747\u503c']
    dp = row['\u5e73\u5c40\u53d8\u5316%']
    mt = row['\u6fb3\u95e8\u63a8\u8350']
    nc = row['\u516c\u53f8\u6570']
    print(f"{en:8} {lq:12} {hm:8}vs{aw:8}  "
          f"主降{hd:2}家 平升{du:2}家 "
          f"即时[主{rh:.2f} 平{rd:.2f} 客{ra:.2f}] "
          f"平变{dp:+.1f}%  澳:{mt}  ({nc}家)")
