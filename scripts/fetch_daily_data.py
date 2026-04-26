def main():
    t0    = time.time()
    today = datetime.date.today()

    print(f"\n{'='*55}")
    print(f"  AI 주식 분석 — PRODUCTION MODE — {today}")
    print(f"{'='*55}\n")

    # ML 모델
    print("🤖 ML 모델 로드...")
    ml_model = load_ml_model()
    print()

    # 전체 종목
    all_df = load_universe()

    # 🔥 1차 필터 (시총 상위 300)
    if "marcap" in all_df.columns and all_df["marcap"].sum() > 0:
        all_df = all_df.nlargest(300, "marcap")
    else:
        all_df = all_df.head(300)

    total = len(all_df)
    print(f"  분석 대상: {total}개 (상위 필터 완료)\n")

    # 🔥 크롤링 대상 (상위 100만)
    top100_codes = set(all_df.head(100)["code"].tolist())

    results = []
    failed  = 0

    print("📈 분석 시작...\n")

    for idx, row in all_df.iterrows():

        code = str(row["code"]).zfill(6)
        name = str(row["name"])

        if idx % 50 == 0:
            print(f"  진행률: {idx}/{total} ({idx/total*100:.1f}%)")

        data = fetch_ohlcv(code)
        if not data:
            failed += 1
            continue

        s = {
            "code": code,
            "name": name,
            "per":  float(row.get("per",0) or 0),
            "pbr":  float(row.get("pbr",0) or 0),
            "roe":  float(row.get("roe",0) or 0),
            "marcap": int(row.get("marcap",0) or 0),
            **data
        }

        # 🔥 상위만 크롤링
        do_supply     = code in top100_codes
        do_short_sell = code in top100_codes

        s["score"] = calc_score(
            s,
            ml_model,
            do_supply=do_supply,
            do_short_sell=do_short_sell
        )

        if elite_filter(s) and super_filter(s["closes"]):
            s["price"]      = s["closes"][-1]
            s["changeRate"] = round(
                safe_pct(s["closes"][-1], s["closes"][-2]), 2
            )
            results.append(s)

    print(f"\n  → 완료: 통과 {len(results)}개 / 실패 {failed}개")

    # 🔥 fallback
    if not results:
        print("  ⚠️ fallback 실행")
        temp = []
        for _, row in all_df.head(100).iterrows():
            code = str(row["code"]).zfill(6)
            data = fetch_ohlcv(code)
            if not data:
                continue

            s = {
                "code": code,
                "name": str(row["name"]),
                "per": 0, "pbr": 0, "roe": 0, "marcap": 0,
                **data
            }

            s["score"] = calc_score(s, ml_model, False, False)

            s["price"]      = s["closes"][-1]
            s["changeRate"] = round(
                safe_pct(s["closes"][-1], s["closes"][-2]), 2
            )

            temp.append(s)

        results = sorted(
            temp,
            key=lambda x: x["score"]["total"],
            reverse=True
        )[:TOP_N]

    # 정렬
    results = sorted(
        results,
        key=lambda x: x["score"]["total"],
        reverse=True
    )[:TOP_N]

    for i, s in enumerate(results, 1):
        s["rank"] = i

    # 저장
    os.makedirs("data", exist_ok=True)

    save = []
    for s in results:
        d = {k:v for k,v in s.items() if k not in ["closes","volumes"]}
        d["closes"]  = s["closes"][-60:]
        d["volumes"] = s["volumes"][-60:]
        save.append(d)

    output = {
        "date": str(today),
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalAnalyzed": total,
        "mlEnabled": ml_model.get("useML", False),
        "stocks": save,
    }

    with open("data/daily_stocks.json","w",encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print("\n🏆 TOP 10 완료")

    for s in results:
        print(f"{s['rank']}. {s['name']} ({s['code']}) "
              f"{s['score']['total']}점")

    print(f"\n⏱ 실행시간: {round((time.time()-t0)/60,1)}분\n")
