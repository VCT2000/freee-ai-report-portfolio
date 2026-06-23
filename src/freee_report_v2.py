# freee_report_v2.py : v1(CSV→月次利益→棒グラフ) ＋ AIによる診断コメント1行

import os                                 # ★v2追加：APIキーの存在確認用
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import anthropic                          # ★v2追加：Anthropic API
from dotenv import load_dotenv            # ★v2追加：.envからAPIキーを読む

# ===== データ処理（v1と同じ）=====
df = pd.read_csv("data/freee_sample.csv")
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

# ===== ★v2の新規：AI診断コメント =====

# .envのAPIキーを読み込む（py_filesまで遡って探す）
load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("APIキーが見つかりません。py_filesの.envにANTHROPIC_API_KEYがあるか確認してください。")

# 月次の表を文字列にして、AIへの指示文（プロンプト）に埋め込む
data_text = monthly.to_string()
prompt = f"""あなたは中小企業の経営者を支援する分析アシスタントです。
以下は、ある事業者の月次の収入・支出・利益と前月比です。

{data_text}

最新月について、経営者向けの診断コメントを1つ作ってください。
条件：
- 必ず具体的な数値を根拠にする
- 「だから何が言えるか（経営者への示唆）」を含める
- 100〜150字、敬体（です・ます）、1〜2文
コメント本文のみを出力してください。"""

# AIに渡して、返ってきた診断コメントを受け取る（モデルはPHASE3と同じ）
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
)
comment = response.content[0].text   # 返答のテキスト部分を取り出す

print("\n----- AI診断コメント -----")
print(comment)