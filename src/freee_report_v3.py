# freee_report_v3.py : v1 ＋ AI診断コメント を v4と同じ「1枚カード」に（コメント1段）
#   ★AIへの指示プロンプトはv3のまま無変更（計算済みfactsを渡す版）

import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FuncFormatter
import anthropic
from dotenv import load_dotenv


def wrap_jp(text, width):
    tokens = re.findall(r"（[^）]*）|.", text)
    lines, cur = [], ""
    for t in tokens:
        if cur and len(cur) + len(t) > width:
            lines.append(cur); cur = t
        else:
            cur += t
    if cur:
        lines.append(cur)
    return "\n".join(lines)


# ===== データ処理（v1と同じ）=====
df = pd.read_csv("data/freee_sample.csv")
df["発生日"] = pd.to_datetime(df["発生日"])
df["年月"] = df["発生日"].dt.to_period("M")
monthly = df.groupby(["年月", "収支区分"])["金額"].sum().unstack(fill_value=0)
monthly["利益"] = monthly["収入"] - monthly["支出"]
monthly["利益_前月比(%)"] = monthly["利益"].pct_change() * 100
print(monthly)

latest_month  = str(monthly.index[-1])
sales         = monthly["収入"].iloc[-1]
profit        = monthly["利益"].iloc[-1]
sales_change  = monthly["収入"].pct_change().iloc[-1] * 100
profit_change = monthly["利益_前月比(%)"].iloc[-1]

facts = (
    f"最新月: {latest_month}\n"
    f"売上: {sales/10000:.1f}万円（前月比 {sales_change:+.1f}%）\n"
    f"利益: {profit/10000:.1f}万円（前月比 {profit_change:+.1f}%）"
)

# ===== AI診断コメント（★v3のプロンプトそのまま）=====
load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("APIキーが見つかりません。.envにANTHROPIC_API_KEYがあるか確認してください。")

prompt = f"""あなたは中小企業の経営者を支援する分析アシスタントです。
以下は、ある事業者の最新月の数字です（計算済み）。

{facts}

この数字を使って、経営者向けの診断コメントを1つ作ってください。
条件：
- 上の数字は計算済みです。変換も再計算もせず、そのまま引用してください。
- 数字を根拠に「だから何が言えるか（経営者への示唆）」を書く
- 100〜150字、敬体（です・ます）、1〜2文
コメント本文のみを出力してください。"""

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
)
comment = response.content[0].text.strip()
print("\n----- AI診断コメント（v3）-----")
print(comment)

# ===== v4と同じ「1枚カード」（KPI＋グラフ＋コメント1段）=====
plt.style.use("seaborn-v0_8")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
BLUE, RED = "#4C72B0", "#c0392b"

fig = plt.figure(figsize=(9, 10))
gs = gridspec.GridSpec(3, 1, height_ratios=[1.2, 3.0, 2.0], hspace=0.45)

axh = fig.add_subplot(gs[0]); axh.axis("off"); axh.set_xlim(0, 1); axh.set_ylim(0, 1)
axh.text(0, 1.02, f"月次レポート　{latest_month}", fontsize=20, fontweight="bold", va="top", color="#222")
for i, (lab, val, col) in enumerate([("収入", f"{sales/10000:.1f}万円", "#222"),
                                     ("利益", f"{profit/10000:.1f}万円", "#222"),
                                     ("前月比（利益）", f"{profit_change:+.1f}%", RED if profit_change < 0 else "#2e7d32")]):
    x = 0.02 + i * 0.34
    axh.text(x, 0.55, lab, fontsize=12, color="#666", va="top")
    axh.text(x, 0.30, val, fontsize=21, fontweight="bold", color=col, va="top")

months = monthly.index.astype(str); profits = monthly["利益"]
ax = fig.add_subplot(gs[1])
ax.bar(months, profits, color=BLUE)
ax.text(len(months) - 1, profits.iloc[-1], f"前月比 {profit_change:+.1f}%",
        ha="center", va="bottom", fontsize=12, color="crimson")
ax.set_title("月次の利益", fontsize=15, pad=12); ax.set_ylabel("利益（円）")
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}")); ax.grid(axis="y", alpha=0.3)

axc = fig.add_subplot(gs[2]); axc.axis("off"); axc.set_xlim(0, 1); axc.set_ylim(0, 1)
axc.text(0, 1.0, "［ AI診断コメント ］", fontsize=13, fontweight="bold", color=BLUE, va="top")
axc.text(0.02, 0.82, wrap_jp(comment, 38), fontsize=12.5, va="top", linespacing=1.7,
         bbox=dict(boxstyle="round,pad=0.7", facecolor="#f4f6fa", edgecolor=BLUE, linewidth=1.2))

fig.savefig("freee_report_v3.png", dpi=150, bbox_inches="tight", facecolor="white")
print("\n1枚レポートを freee_report_v3.png に保存しました")
