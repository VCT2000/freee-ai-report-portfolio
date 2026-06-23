# freee_report_v4.py（完成版）
# v3 → v4 の変更点（3つ）:
#   (1) グラフとAIコメントを「1枚の画像」にまとめて出力する
#   (2) 月次確認コメント = 数字から分かることは断定OK / 原因は断定しない
#   (3) 未提供データ（固定費など）は別枠「追加確認候補」として扱う（コメントには混ぜない）

import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FuncFormatter
import anthropic
from dotenv import load_dotenv


# 日本語コメント用の折り返し：「（…）」のかたまりは途中で切らずに幅widthで詰める
def wrap_jp(text, width):
    # （…）を1かたまり、それ以外は1文字ずつのトークンに分解
    tokens = re.findall(r"（[^）]*）|.", text)
    lines, cur = [], ""
    for t in tokens:
        if cur and len(cur) + len(t) > width:   # 入りきらなければ改行
            lines.append(cur)
            cur = t
        else:
            cur += t
    if cur:
        lines.append(cur)
    return "\n".join(lines)


# ===== 1. データ処理 =====
df = pd.read_csv("data/freee_sample.csv")
df["発生日"] = pd.to_datetime(df["発生日"])
df["年月"] = df["発生日"].dt.to_period("M")
monthly = df.groupby(["年月", "収支区分"])["金額"].sum().unstack(fill_value=0)
monthly["費用"] = monthly["支出"]                      # 利益=収入-費用 の「費用」＝支出合計
monthly["利益"] = monthly["収入"] - monthly["費用"]
for col in ["収入", "費用", "利益"]:                    # 各項目の前月比をまとめて計算（数字はコード側で確定）
    monthly[f"{col}_前月比(%)"] = monthly[col].pct_change() * 100
print(monthly[["収入", "費用", "利益"]])

# ===== 2. 最新月の数字を取り出す（AIに「事実」として渡す）=====
latest      = str(monthly.index[-1])
income      = monthly["収入"].iloc[-1]
expense     = monthly["費用"].iloc[-1]
profit      = monthly["利益"].iloc[-1]
income_chg  = monthly["収入_前月比(%)"].iloc[-1]
expense_chg = monthly["費用_前月比(%)"].iloc[-1]
profit_chg  = monthly["利益_前月比(%)"].iloc[-1]

# 費用も計算済みなので「収入・費用・利益」の3つを事実として渡せる
facts = (
    f"最新月: {latest}\n"
    f"収入: {income/10000:.1f}万円（前月比 {income_chg:+.1f}%）\n"
    f"費用: {expense/10000:.1f}万円（前月比 {expense_chg:+.1f}%）\n"
    f"利益: {profit/10000:.1f}万円（前月比 {profit_chg:+.1f}%）"
)

# ===== 3. 月次確認コメント（数字は断定OK・原因は断定しない）=====
load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("APIキーが見つかりません。.envにANTHROPIC_API_KEYがあるか確認してください。")

prompt = f"""あなたは中小企業の経営者を支援する分析アシスタントです。
以下は、ある事業者の最新月の数字です（すべて計算済み）。

{facts}

この数字だけを使って、経営者向けの確認コメントを1つ作ってください。
条件：
- 上の数字は計算済みです。変換も再計算もせず、そのまま引用してください。
- 上にある項目（収入・費用・利益とその前月比）について、数字から読み取れること・
  項目どうしの大小関係・変化の比較は、断定して書いてかまいません。
- ただし「なぜそうなったか」という原因は断定しないこと。上に無い要素
  （固定費・原価率・客数・単価・季節要因など、収入や費用の"内訳"や"背景"）には、
  推測でも断定でも触れないでください。
- 「〜を確認してください」などの提案は書かないでください（別の欄で扱います）。
- 100〜150字、敬体（です・ます）、1〜2文。

コメント本文のみを出力してください。"""

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
)
comment = response.content[0].text.strip()
print("\n----- 月次確認コメント（v4）-----")
print(comment)

# ===== 4. 追加確認候補（Python側で固定＝AIに作らせない＝原因の捏造を防ぐ）=====
# これは「原因」ではなく「次に見ると要因が分かる項目」。だから断定にならない。
checks = [
    "費用の内訳（固定費・原価率など）が前月とどう動いたか",
    "収入の変化が「客数」と「単価」のどちらによるものか",
    "前年同月・季節性と比べて今月はどうか",
]

# ===== 5. グラフ＋コメント＋追加確認候補を「1枚」にまとめて保存 =====
plt.style.use("seaborn-v0_8")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
BLUE, RED = "#4C72B0", "#c0392b"

fig = plt.figure(figsize=(9, 12.5))
gs = gridspec.GridSpec(4, 1, height_ratios=[1.2, 3.0, 1.8, 1.9], hspace=0.5)

# (a) ヘッダー：タイトル＋KPI
axh = fig.add_subplot(gs[0]); axh.axis("off"); axh.set_xlim(0, 1); axh.set_ylim(0, 1)
axh.text(0, 1.02, f"月次レポート　{latest}", fontsize=20, fontweight="bold", va="top", color="#222")
kpis = [("収入", f"{income/10000:.1f}万円", "#222"),
        ("利益", f"{profit/10000:.1f}万円", "#222"),
        ("前月比（利益）", f"{profit_chg:+.1f}%", RED if profit_chg < 0 else "#2e7d32")]
for i, (lab, val, col) in enumerate(kpis):
    x = 0.02 + i * 0.34
    axh.text(x, 0.55, lab, fontsize=12, color="#666", va="top")
    axh.text(x, 0.32, val, fontsize=21, fontweight="bold", color=col, va="top")

# (b) グラフ：月次の利益
months = monthly.index.astype(str); profits = monthly["利益"]
ax = fig.add_subplot(gs[1])
ax.bar(months, profits, color=BLUE)
ax.text(len(months) - 1, profits.iloc[-1], f"前月比 {profit_chg:+.1f}%",
        ha="center", va="bottom", fontsize=12, color="crimson")
ax.set_title("月次の利益", fontsize=15, pad=12)
ax.set_ylabel("利益（円）")
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.grid(axis="y", alpha=0.3)

# (c) 月次確認コメント（青枠＝数字から言えること）
axc = fig.add_subplot(gs[2]); axc.axis("off"); axc.set_xlim(0, 1); axc.set_ylim(0, 1)
axc.text(0, 1.0, "［ 月次確認コメント ］", fontsize=13, fontweight="bold", color=BLUE, va="top")
axc.text(0.02, 0.80, wrap_jp(comment, 38),
         fontsize=12.5, va="top", linespacing=1.7,
         bbox=dict(boxstyle="round,pad=0.7", facecolor="#f4f6fa", edgecolor=BLUE, linewidth=1.2))

# (d) 追加確認候補（グレー枠＝原因ではない・別枠）
axk = fig.add_subplot(gs[3]); axk.axis("off"); axk.set_xlim(0, 1); axk.set_ylim(0, 1)
axk.text(0, 1.0, "［ 追加確認候補（原因ではなく、次に見ると要因が分かる項目）］",
         fontsize=12.5, fontweight="bold", color="#555", va="top")
axk.text(0.02, 0.74, "\n".join(f"・{c}" for c in checks),
         fontsize=12, va="top", linespacing=1.9, color="#333",
         bbox=dict(boxstyle="round,pad=0.7", facecolor="#f7f7f7", edgecolor="#bbb", linewidth=1.1))

fig.savefig("freee_report_v4.png", dpi=150, bbox_inches="tight", facecolor="white")
print("\n1枚レポートを freee_report_v4.png に保存しました")
