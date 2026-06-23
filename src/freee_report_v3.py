# freee_report_v3.py : v2 ＋ AIコメントの数字を正す（計算はPython・言葉だけAI）

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import anthropic
from dotenv import load_dotenv

# ===== データ処理（v1と同じ）=====
df = pd.read_csv("freee_sample.csv")
df["発生日"] = pd.to_datetime(df["発生日"])
df["年月"] = df["発生日"].dt.to_period("M")
monthly = df.groupby(["年月", "収支区分"])["金額"].sum().unstack(fill_value=0)
monthly["利益"] = monthly["収入"] - monthly["支出"]
monthly["利益_前月比(%)"] = monthly["利益"].pct_change() * 100
print(monthly)

# ===== グラフ（v1と同じ）=====
plt.style.use("seaborn-v0_8")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
months = monthly.index.astype(str)
profits = monthly["利益"]
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(months, profits, color="#4C72B0")
latest_change = monthly["利益_前月比(%)"].iloc[-1]
ax.text(len(months) - 1, profits.iloc[-1],
        f"前月比 {latest_change:+.1f}%",
        ha="center", va="bottom", fontsize=12, color="crimson")
ax.set_title("月次の利益", fontsize=16, pad=20)
ax.set_ylabel("利益（円）")
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig("profit_chart.png", dpi=150)
print("グラフを profit_chart.png に保存しました")

# ===== AI診断コメント（v3：数字はPythonで確定、AIは言葉だけ）=====

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("APIキーが見つかりません。py_filesの.envにANTHROPIC_API_KEYがあるか確認してください。")

# ★v3：最新月の数字をPython側で確定・整形（万円換算もPythonがやる＝ここが盛れない肝）
latest_month  = str(monthly.index[-1])                         # "2026-05"
sales         = monthly["収入"].iloc[-1]                       # 最新月の売上
profit        = monthly["利益"].iloc[-1]                       # 最新月の利益
sales_change  = monthly["収入"].pct_change().iloc[-1] * 100    # 売上の前月比(%)
profit_change = monthly["利益_前月比(%)"].iloc[-1]             # 利益の前月比(%)

facts = (
    f"最新月: {latest_month}\n"
    f"売上: {sales/10000:.1f}万円（前月比 {sales_change:+.1f}%）\n"
    f"利益: {profit/10000:.1f}万円（前月比 {profit_change:+.1f}%）"
)

# ★v3：表を丸ごと渡すのをやめ、「計算済みの事実」を渡し、変換・再計算を禁止する
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
comment = response.content[0].text

print("\n----- AI診断コメント（v3）-----")
print(comment)