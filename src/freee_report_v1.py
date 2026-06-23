# freee_report_v1.py : CSV読込 → 月次の収入/支出/利益 → 前月比 → 棒グラフ(前月比注記)

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# freeeの取引CSVを読み込む
df = pd.read_csv("freee_sample.csv")

# 発生日を日付として扱い、月単位（2026-04 など）の「年月」列を用意する
# → これがないと月ごとの集計ができない
df["発生日"] = pd.to_datetime(df["発生日"])
df["年月"] = df["発生日"].dt.to_period("M")

# 年月 × 収支区分 で合計 → 行=年月・列=収入/支出 に変形（PHASE5の groupby+unstack）
monthly = df.groupby(["年月", "収支区分"])["金額"].sum().unstack(fill_value=0)

monthly["利益"] = monthly["収入"] - monthly["支出"]

# 前月からの利益の変化率。先頭の月は比較対象がなく NaN になる（仕様どおり）
monthly["利益_前月比(%)"] = monthly["利益"].pct_change() * 100

print(monthly)

# スタイルと日本語フォント（フォント指定は style.use の後に置くのがコツ＝PHASE5の教訓）
plt.style.use("seaborn-v0_8")
plt.rcParams["font.family"] = "Noto Sans CJK JP"

# 軸に使う値を取り出す（年月はPeriod型なので文字列に変換）
months = monthly.index.astype(str)
profits = monthly["利益"]

# 棒グラフ本体
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(months, profits, color="#4C72B0")

# 最新月の棒の上に「前月比」を書き込む（経営者が一番見たい一言）
latest_change = monthly["利益_前月比(%)"].iloc[-1]   # iloc[-1] = 一番下の行 = 最新月
ax.text(
    len(months) - 1, profits.iloc[-1],
    f"前月比 {latest_change:+.1f}%",
    ha="center", va="bottom", fontsize=12, color="crimson",
)

# 仕上げ：タイトル・軸ラベル・桁区切り・薄いグリッド
ax.set_title("月次の利益", fontsize=16, pad=20)
ax.set_ylabel("利益（円）")
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.grid(axis="y", alpha=0.3)

# WSLは画面表示できないので、必ず画像ファイルに保存（plt.show は使わない）
fig.tight_layout()
fig.savefig("profit_chart.png", dpi=150)
print("グラフを profit_chart.png に保存しました")