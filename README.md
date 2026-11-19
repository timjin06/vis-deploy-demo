# 지점 실적 인터랙티브 대시보드

A·B 지점의 2026년 월별 매출·영업이익을 조건에 따라 탐색하는 Streamlit 대시보드입니다.

## 화면 구성
- **KPI 카드** — 기간 매출·영업이익·영업이익률·지점 격차 (증감 표시)
- **📈 개요** — 월별 실적 막대 + 영업이익률 선 콤보 차트, 지점 비중 도넛
- **🌊 추이** — 그라데이션 영역 차트, 누적 바 레이스(▶ 재생 애니메이션)
- **🎯 지점 비교** — 종합 레이더 차트, 영업이익률 게이지
- **🔍 상세·데이터** — 월×지점 히트맵, 데이터 표, CSV 다운로드

사이드바 위젯(지점·월 범위·지표·누적 토글)을 바꾸면 모든 숫자와 차트가 함께 바뀝니다.
글자는 전부 Plotly로 그려 서버에 한글 글꼴이 없어도 깨지지 않습니다.

## 실행
```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

## 배포
이 저장소를 Streamlit Community Cloud에 연결하고 Main file path에 `app.py`를 지정합니다.
올리기 전 점검: `python 배포_전_점검.py`

## 파일
- `app.py` — 대시보드 본체
- `sales.csv` — 수업용 가상 데이터(월·지점·매출·영업이익)
- `.streamlit/config.toml` — 다크 테마 설정
- `requirements.txt` — 의존성(streamlit, pandas, plotly)
