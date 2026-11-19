"""지점 실적 인터랙티브 대시보드 (배포용).

11~12주차 예제를 '역동적이고 보기 좋은' 대시보드로 다시 꾸민 판입니다.
핵심 데이터 흐름은 그대로입니다: 위젯으로 고른 조건 → view(필터된 표) → 모든 숫자·차트가 같은 view를 씁니다.

달라진 점
- 어두운 그라데이션 테마 + 커스텀 KPI 카드(증감 표시)
- 탭으로 나눈 다양한 Plotly 차트: 콤보(막대+선), 도넛, 그라데이션 영역, 애니메이션 바 레이스,
  레이더(지점 비교), 게이지(이익률), 히트맵
- 글자는 전부 Plotly로 그려 서버에 한글 글꼴이 없어도 깨지지 않습니다(보는 사람의 브라우저가 그림).

배포: 이 파일, requirements.txt, sales.csv, .streamlit/config.toml을 저장소에 함께 올립니다.
내 컴퓨터에서 실행: python -m streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# app.py가 있는 폴더. 파일은 항상 이 폴더 기준으로 찾습니다(배포 서버의 작업 폴더와 다를 수 있음).
HERE = Path(__file__).parent

# ── 디자인 토큰 ────────────────────────────────────────────────────────────────
# 어두운 테마에 맞춰 밝힌 지점 색(색각 이상도 구분되는 파랑/주황 계열).
COLORS = {"A": "#4EA8FF", "B": "#FF8A4C"}
FILL = {"A": "rgba(78,168,255,0.00)", "B": "rgba(255,138,76,0.00)"}
FILL_TOP = {"A": "rgba(78,168,255,0.45)", "B": "rgba(255,138,76,0.45)"}
INK = "#E8EDF7"          # 기본 글자색
MUTED = "#8A94AD"        # 흐린 글자색
GRID = "rgba(255,255,255,0.06)"
FONT = "Pretendard, 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif"

st.set_page_config(page_title="지점 실적 대시보드", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")


# ── 전역 스타일(CSS) ───────────────────────────────────────────────────────────
def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

        html, body, [class*="css"] { font-family: Pretendard, 'Malgun Gothic', sans-serif; }

        /* 전체 배경: 은은하게 움직이는 그라데이션 */
        .stApp {
            background:
              radial-gradient(1200px 600px at 10% -10%, rgba(78,168,255,0.14), transparent 55%),
              radial-gradient(1000px 500px at 110% 10%, rgba(255,138,76,0.12), transparent 55%),
              linear-gradient(160deg, #0a0e1a 0%, #0d1322 45%, #0a0f1c 100%);
            background-attachment: fixed;
            color: #E8EDF7;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(18,24,41,0.95), rgba(12,17,30,0.95));
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        [data-testid="stSidebar"] * { color: #D7DEED; }

        /* 히어로 헤더 */
        .hero-title {
            font-size: 2.5rem; font-weight: 800; letter-spacing: -0.02em; margin: 0;
            background: linear-gradient(90deg, #8EC5FF 0%, #4EA8FF 40%, #FFB26B 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .hero-sub { color: #8A94AD; font-size: 0.95rem; margin-top: .35rem; }
        .pill {
            display:inline-block; padding: 3px 12px; border-radius: 999px; font-size:.75rem;
            background: rgba(78,168,255,0.14); color:#8EC5FF; border:1px solid rgba(78,168,255,0.35);
            margin-right:6px;
        }

        /* KPI 카드 */
        .kpi {
            position: relative; overflow: hidden; border-radius: 18px; padding: 18px 20px;
            background: linear-gradient(145deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015));
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 10px 30px rgba(0,0,0,0.35);
            backdrop-filter: blur(6px); transition: transform .18s ease, box-shadow .18s ease;
        }
        .kpi:hover { transform: translateY(-4px); box-shadow: 0 16px 40px rgba(0,0,0,0.5); }
        .kpi .k-accent { position:absolute; inset:0 auto 0 0; width:5px; border-radius: 18px 0 0 18px; }
        .kpi .k-label { color:#8A94AD; font-size:.8rem; font-weight:600; letter-spacing:.02em; }
        .kpi .k-value { font-size:1.9rem; font-weight:800; margin-top:4px; line-height:1.1; color:#F2F5FB; }
        .kpi .k-unit  { font-size:.9rem; font-weight:600; color:#A7B0C5; margin-left:4px; }
        .kpi .k-delta { font-size:.82rem; font-weight:700; margin-top:8px; }
        .k-up   { color:#49D18B; }
        .k-down { color:#FF6B6B; }
        .k-flat { color:#8A94AD; }

        /* 섹션 카드(차트 감싸기) */
        .block-card {
            border-radius:18px; padding: 6px 10px 2px;
            background: linear-gradient(145deg, rgba(255,255,255,0.035), rgba(255,255,255,0.01));
            border:1px solid rgba(255,255,255,0.07);
        }

        /* 탭 */
        .stTabs [data-baseweb="tab-list"] { gap: 6px; }
        .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,0.03); border-radius: 12px 12px 0 0;
            padding: 8px 18px; border:1px solid rgba(255,255,255,0.06); border-bottom:none;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(180deg, rgba(78,168,255,0.22), rgba(78,168,255,0.05));
            border-color: rgba(78,168,255,0.4);
        }

        h1,h2,h3,h4 { color:#EDF1FA; }
        [data-testid="stMetricValue"] { color:#F2F5FB; }
        div[data-testid="stDataFrame"] { border-radius:14px; overflow:hidden; }
        .section-h { font-size:1.05rem; font-weight:700; color:#DCE4F3; margin:2px 0 10px 2px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_fig(fig, height=360, legend=True):
    """모든 차트에 공통으로 입히는 어두운 테마."""
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=INK, size=13),
        margin=dict(l=10, r=14, t=56, b=10),
        title=dict(font=dict(size=16, color="#EDF1FA"), x=0.01, xanchor="left"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#141b2e", font_size=12, font_family=FONT),
        showlegend=legend,
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID,
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID,
                     tickfont=dict(color=MUTED))
    return fig


# 결과를 기억해 위젯을 바꿔도 CSV를 다시 읽지 않습니다.
@st.cache_data
def load_data():
    return pd.read_csv(HERE / "sales.csv")


inject_css()

# ── 데이터 ─────────────────────────────────────────────────────────────────────
try:
    data = load_data()
except FileNotFoundError:
    st.error("app.py와 같은 폴더에 sales.csv를 올려 주세요.")
    st.stop()

# ── 사이드바(조회 조건) ─────────────────────────────────────────────────────────
st.sidebar.markdown("### ⚙️ 조회 조건")
branches = st.sidebar.multiselect("지점", ["A", "B"], default=["A", "B"])
months = st.sidebar.slider("월 범위", 1, 12, (1, 12))
metric_label = st.sidebar.selectbox("표시 지표", ["매출", "영업이익"])
metric = {"매출": "sales", "영업이익": "profit"}[metric_label]
unit = "백만원"
cumulative = st.sidebar.toggle("추이·영역 차트를 누적으로 보기", value=False)
st.sidebar.caption("조건을 바꾸면 위의 숫자와 아래 모든 차트가 함께 바뀝니다.")

# 위젯 선택 → view → 숫자·차트·표가 모두 같은 view를 씁니다.
view = data.loc[data["branch"].isin(branches) & data["month"].between(months[0], months[1])].copy()
if view.empty:
    st.warning("표시할 데이터가 없습니다. 지점을 하나 이상 선택하세요.")
    st.stop()
view = view.sort_values(["branch", "month"])

# ── 파생 지표 계산 ──────────────────────────────────────────────────────────────
totals = view.groupby("branch", as_index=False)[["sales", "profit"]].sum()
totals["margin"] = totals["profit"] / totals["sales"] * 100

# 선택한 지표의 월별 합계(여러 지점을 합친 전체 추세)
monthly_all = view.groupby("month", as_index=False)[["sales", "profit"]].sum().sort_values("month")
monthly_all["margin"] = monthly_all["profit"] / monthly_all["sales"] * 100

sales_sum = view["sales"].sum()
profit_sum = view["profit"].sum()
margin_all = profit_sum / sales_sum * 100

# 성장률: 선택 지표의 (마지막 달 − 첫 달) ÷ 첫 달 × 100
first_v = monthly_all[metric].iloc[0]
last_v = monthly_all[metric].iloc[-1]
growth = (last_v - first_v) / first_v * 100 if first_v else 0.0

# 지점 간 격차(선택 지표 합계): 1위 − 2위
rank = totals.sort_values(metric, ascending=False).reset_index(drop=True)
lead_branch = rank["branch"].iloc[0]
gap = (rank[metric].iloc[0] - rank[metric].iloc[1]) if len(rank) > 1 else rank[metric].iloc[0]


# ── 히어로 헤더 ─────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin:2px 0 14px;">
      <div class="hero-title">어느 지점의 실적이 더 좋은가</div>
      <div class="hero-sub">
        <span class="pill">📅 {months[0]}~{months[1]}월</span>
        <span class="pill">🏢 {', '.join(branches)}지점</span>
        <span class="pill">📈 {metric_label}</span>
        수업용 가상 데이터(sales.csv) · 2026년 · 금액 단위 {unit}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── KPI 카드 ───────────────────────────────────────────────────────────────────
def delta_html(value, good_up=True, suffix="%"):
    arrow = "▲" if value > 0 else ("▼" if value < 0 else "■")
    cls = "k-flat" if value == 0 else (("k-up" if value > 0 else "k-down") if good_up
                                       else ("k-down" if value > 0 else "k-up"))
    return f'<div class="k-delta {cls}">{arrow} {abs(value):,.1f}{suffix}</div>'


def kpi_card(accent, label, value, unit_txt, delta_markup=""):
    return f"""
    <div class="kpi">
      <div class="k-accent" style="background:linear-gradient(180deg,{accent},transparent);"></div>
      <div class="k-label">{label}</div>
      <div class="k-value">{value}<span class="k-unit">{unit_txt}</span></div>
      {delta_markup}
    </div>
    """


k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(kpi_card("#4EA8FF", f"기간 {metric_label} 합계",
                         f"{view[metric].sum():,.0f}", unit,
                         delta_html(growth, good_up=True,
                                    suffix="% (첫→끝 달)")), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_card("#FF8A4C", "기간 영업이익 합계",
                         f"{profit_sum:,.0f}", unit,
                         f'<div class="k-delta k-flat">기간 매출 {sales_sum:,.0f} {unit}</div>'),
                unsafe_allow_html=True)
with k3:
    st.markdown(kpi_card("#49D18B", "기간 영업이익률",
                         f"{margin_all:,.1f}", "%",
                         f'<div class="k-delta k-flat">이익 ÷ 매출 합계</div>'),
                unsafe_allow_html=True)
with k4:
    lead_txt = (f'<div class="k-delta k-up">🥇 {lead_branch}지점 우위</div>'
                if len(branches) > 1 else
                '<div class="k-delta k-flat">단일 지점 선택</div>')
    st.markdown(kpi_card("#B692FF", f"지점 격차 ({metric_label})",
                         f"{gap:,.0f}", unit, lead_txt), unsafe_allow_html=True)

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

# ── 탭 레이아웃 ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 개요", "🌊 추이", "🎯 지점 비교", "🔍 상세·데이터"])

# ===== 탭 1: 개요 — 콤보 차트 + 도넛 =============================================
with tab1:
    col_l, col_r = st.columns([1.55, 1])

    with col_l:
        st.markdown('<div class="section-h">월별 실적 & 영업이익률 (콤보)</div>',
                    unsafe_allow_html=True)
        # 막대: 지점별 선택 지표, 선: 전체 영업이익률(보조축)
        combo = make_subplots(specs=[[{"secondary_y": True}]])
        for b in [x for x in ["A", "B"] if x in branches]:
            d = view[view["branch"] == b]
            combo.add_trace(
                go.Bar(x=d["month"], y=d[metric], name=f"{b} {metric_label}",
                       marker=dict(color=COLORS[b], line=dict(width=0)),
                       opacity=0.92, hovertemplate=f"{b} · %{{x}}월<br>{metric_label} %{{y:,}}"
                       + f" {unit}<extra></extra>"),
                secondary_y=False)
        combo.add_trace(
            go.Scatter(x=monthly_all["month"], y=monthly_all["margin"], name="영업이익률",
                       mode="lines+markers", line=dict(color="#49D18B", width=3, shape="spline"),
                       marker=dict(size=7, color="#49D18B"),
                       hovertemplate="%{x}월<br>영업이익률 %{y:.1f}%<extra></extra>"),
            secondary_y=True)
        combo.update_layout(barmode="group", bargap=0.25, title="")
        combo.update_xaxes(dtick=1, title_text="월")
        combo.update_yaxes(title_text=f"{metric_label} ({unit})", secondary_y=False, rangemode="tozero")
        combo.update_yaxes(title_text="영업이익률 (%)", secondary_y=True, rangemode="tozero",
                           showgrid=False)
        st.plotly_chart(style_fig(combo, height=400), width="stretch")

    with col_r:
        st.markdown(f'<div class="section-h">{metric_label} 비중</div>', unsafe_allow_html=True)
        donut = go.Figure(go.Pie(
            labels=totals["branch"], values=totals[metric], hole=0.62,
            marker=dict(colors=[COLORS[b] for b in totals["branch"]],
                        line=dict(color="#0d1322", width=3)),
            textinfo="label+percent", textfont=dict(size=15, color="#0b1020"),
            hovertemplate="%{label}지점<br>%{value:,} " + unit + "<br>%{percent}<extra></extra>",
            sort=False))
        donut.add_annotation(text=f"<b>{view[metric].sum():,.0f}</b><br><span style='font-size:12px;color:{MUTED}'>{unit}</span>",
                             showarrow=False, font=dict(size=22, color=INK))
        st.plotly_chart(style_fig(donut, height=400, legend=False), width="stretch")

# ===== 탭 2: 추이 — 그라데이션 영역 + 애니메이션 바 레이스 =========================
with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        mode_txt = "누적" if cumulative else "월별"
        st.markdown(f'<div class="section-h">{mode_txt} {metric_label} 추이 (그라데이션 영역)</div>',
                    unsafe_allow_html=True)
        area = go.Figure()
        for b in [x for x in ["A", "B"] if x in branches]:
            d = view[view["branch"] == b].copy()
            y = d[metric].cumsum() if cumulative else d[metric]
            area.add_trace(go.Scatter(
                x=d["month"], y=y, name=f"{b}지점", mode="lines+markers",
                line=dict(color=COLORS[b], width=3, shape="spline"),
                marker=dict(size=7, color=COLORS[b], line=dict(color="#0d1322", width=1)),
                fill="tozeroy",
                fillgradient=dict(type="vertical",
                                  colorscale=[[0.0, FILL[b]], [1.0, FILL_TOP[b]]]),
                hovertemplate=f"{b} · %{{x}}월<br>%{{y:,}} {unit}<extra></extra>"))
        area.update_xaxes(dtick=1, title_text="월")
        area.update_yaxes(title_text=f"{metric_label} ({unit})", rangemode="tozero")
        st.plotly_chart(style_fig(area, height=400), width="stretch")

    with col_b:
        st.markdown(f'<div class="section-h">누적 {metric_label} 바 레이스 ▶ 재생</div>',
                    unsafe_allow_html=True)
        # 월이 흐르면서 지점별 누적 합계가 자라나는 애니메이션
        race = view.copy()
        race["cum"] = race.groupby("branch")[metric].cumsum()
        order = [x for x in ["A", "B"] if x in branches]
        ymax = max(race["cum"].max() * 1.12, 1)
        bar_race = px.bar(
            race, x="cum", y="branch", color="branch", orientation="h",
            animation_frame="month", color_discrete_map=COLORS,
            category_orders={"branch": order}, range_x=[0, ymax], text="cum")
        bar_race.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                               textfont=dict(color=INK),
                               marker=dict(line=dict(width=0)), width=0.55)
        bar_race.update_layout(title="", xaxis_title=f"누적 {metric_label} ({unit})",
                               yaxis_title="")
        # 재생 버튼·슬라이더 스타일 보정
        if bar_race.layout.updatemenus:
            bar_race.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 650
            bar_race.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 400
            bar_race.layout.updatemenus[0].pad = dict(r=10, t=10)
        st.plotly_chart(style_fig(bar_race, height=400, legend=False), width="stretch")
        st.caption("▶ 버튼을 누르면 1월부터 선택 끝 달까지 누적 실적이 자라납니다.")

# ===== 탭 3: 지점 비교 — 레이더 + 게이지 =========================================
with tab3:
    col_rad, col_gauge = st.columns([1.1, 1])

    with col_rad:
        st.markdown('<div class="section-h">지점 종합 비교 (레이더)</div>', unsafe_allow_html=True)
        # 5개 축을 지점 간 최댓값 대비 0~100으로 정규화
        g = view.groupby("branch")
        comp = pd.DataFrame({
            "총매출": g["sales"].sum(),
            "총이익": g["profit"].sum(),
            "영업이익률": g["profit"].sum() / g["sales"].sum() * 100,
            "최고 월매출": g["sales"].max(),
            "월평균 매출": g["sales"].mean(),
        })
        norm = comp.div(comp.max(axis=0).replace(0, 1), axis=1) * 100
        axes = list(norm.columns)
        radar = go.Figure()
        for b in [x for x in ["A", "B"] if x in norm.index]:
            vals = norm.loc[b, axes].tolist()
            radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]], theta=axes + [axes[0]], name=f"{b}지점",
                fill="toself", line=dict(color=COLORS[b], width=2.5),
                fillcolor=FILL_TOP[b].replace("0.45", "0.18"),
                hovertemplate=f"{b} · %{{theta}}<br>지수 %{{r:.0f}}/100<extra></extra>"))
        radar.update_layout(
            title="",
            polar=dict(bgcolor="rgba(255,255,255,0.02)",
                       radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID,
                                       tickfont=dict(color=MUTED, size=10), angle=90),
                       angularaxis=dict(gridcolor=GRID, tickfont=dict(color=INK, size=12))))
        st.plotly_chart(style_fig(radar, height=420), width="stretch")
        st.caption("각 축은 선택 지점 중 최댓값을 100으로 둔 상대 지수입니다.")

    with col_gauge:
        st.markdown('<div class="section-h">지점별 영업이익률 게이지</div>', unsafe_allow_html=True)
        order = [x for x in ["A", "B"] if x in totals["branch"].values]
        gfig = make_subplots(rows=len(order), cols=1,
                             specs=[[{"type": "indicator"}] for _ in order],
                             vertical_spacing=0.18)
        gmax = max(totals["margin"].max() * 1.3, 10)
        for i, b in enumerate(order):
            m = float(totals.loc[totals["branch"] == b, "margin"].iloc[0])
            gfig.add_trace(go.Indicator(
                mode="gauge+number+delta", value=m,
                number=dict(suffix=" %", font=dict(size=26, color=INK)),
                delta=dict(reference=margin_all, suffix=" %p",
                           increasing=dict(color="#49D18B"), decreasing=dict(color="#FF6B6B")),
                title=dict(text=f"{b}지점", font=dict(size=14, color=MUTED)),
                gauge=dict(
                    axis=dict(range=[0, gmax], tickcolor=MUTED, tickfont=dict(color=MUTED, size=9)),
                    bar=dict(color=COLORS[b], thickness=0.72),
                    bgcolor="rgba(255,255,255,0.03)", borderwidth=0,
                    threshold=dict(line=dict(color="#E8EDF7", width=2), value=margin_all))),
                row=i + 1, col=1)
        gfig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           font=dict(family=FONT, color=INK),
                           height=420, margin=dict(l=20, r=20, t=30, b=10))
        st.plotly_chart(gfig, width="stretch")
        st.caption(f"흰 선·△ 표시는 전체 평균 이익률 {margin_all:.1f}% 대비 입니다.")

# ===== 탭 4: 상세 — 히트맵 + 표/다운로드 =========================================
with tab4:
    st.markdown(f'<div class="section-h">월 × 지점 {metric_label} 히트맵</div>', unsafe_allow_html=True)
    pivot = view.pivot_table(index="branch", columns="month", values=metric, aggfunc="sum")
    heat = px.imshow(pivot, text_auto=True, aspect="auto",
                     color_continuous_scale=["#0d1322", "#1E63D6", "#4EA8FF", "#FFB26B", "#FF6B35"],
                     labels=dict(x="월", y="지점", color=f"{metric_label}({unit})"))
    heat.update_xaxes(dtick=1, side="top")
    heat.update_traces(textfont=dict(size=12),
                       hovertemplate="%{y}지점 · %{x}월<br>%{z:,} " + unit + "<extra></extra>")
    heat.update_layout(title="", coloraxis_colorbar=dict(title=""))
    st.plotly_chart(style_fig(heat, height=300, legend=False), width="stretch")

    st.markdown('<div class="section-h">현재 선택한 데이터</div>', unsafe_allow_html=True)
    show = view.rename(columns={"month": "월", "branch": "지점", "sales": "매출", "profit": "영업이익"})
    show["영업이익률(%)"] = (show["영업이익"] / show["매출"] * 100).round(1)
    st.dataframe(show, hide_index=True, width="stretch",
                 column_config={
                     "매출": st.column_config.ProgressColumn(
                         "매출", format="%d", min_value=0, max_value=int(view["sales"].max())),
                 })
    st.download_button("⬇️ 현재 선택 CSV 저장",
                       data=view.to_csv(index=False).encode("utf-8-sig"),
                       file_name="selected_sales.csv", mime="text/csv")
    st.caption("한 행은 한 달·한 지점입니다. 이 자료만으로 실적 변화의 원인을 단정하지 않습니다.")
