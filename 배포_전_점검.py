"""배포 전 점검: GitHub에 올리기 전에 내 컴퓨터에서 Streamlit 앱을 한 번 검사합니다.

app.py가 있는 폴더에 이 파일을 두고, 앱을 실행하던 Python으로 실행합니다.
    python 배포_전_점검.py            # 같은 폴더의 app.py 검사
    python 배포_전_점검.py 내앱.py     # 시작 파일 이름이 다를 때

검사 항목
1. 파일: 시작 파일과 requirements.txt가 같은 폴더에 있는지
2. 패키지: 앱이 import하는 외부 패키지가 requirements.txt에 모두 있는지
3. 경로: 내 컴퓨터에만 있는 절대 경로, 앱 폴더 밖 파일(../), 역슬래시 경로, 폴더에 없는 데이터 파일,
   대소문자만 다른 파일 이름(윈도·맥에서는 열리지만 리눅스 서버에서는 못 찾음)
4. 파일: GitHub 브라우저 올리기 한도(파일 하나에 25MB)를 넘는 파일, 올리면 안 되는 폴더·파일
5. 실행: Streamlit AppTest로 첫 화면과 위젯의 경계값(모두 지우기, 하나만 고르기, 선택지마다)을 실행
6. 한글: Matplotlib·Seaborn 그림은 배포 서버에서 한글이 깨질 수 있다는 안내

결과 표시: [통과] 문제 없음 · [확인] 직접 눈으로 볼 것(버전은 내 컴퓨터, 한글은 배포한 주소) · [고침] 올리기 전에 고칠 것.
[고침]이 하나라도 있으면 종료 코드 1입니다. 이 파일은 저장소에 올리지 않아도 됩니다.
"""
import ast
import logging
import os
import re
import sys
import warnings
from pathlib import Path

LIMIT_MB = 25                      # GitHub 브라우저 올리기: 파일 하나에 25MiB
DATA_EXT = r'\.(csv|tsv|txt|xlsx|xls|json|geojson|parquet|feather|zip|shp)$'
READERS = {'read_csv', 'read_excel', 'read_json', 'read_parquet', 'read_table', 'read_feather', 'read_file',
           'open', 'with_name', 'joinpath', 'Path', 'load_workbook', 'imread'}
PIP_NAME = {'sklearn': 'scikit-learn', 'PIL': 'pillow', 'bs4': 'beautifulsoup4', 'yaml': 'pyyaml',
            'dateutil': 'python-dateutil', 'mpl_toolkits': 'matplotlib', 'cv2': 'opencv-python',
            'docx': 'python-docx', 'pptx': 'python-pptx', 'dotenv': 'python-dotenv'}
# import하지 않아도 pandas가 부르는 추가 패키지
EXTRA = {'read_excel': 'openpyxl', 'to_excel': 'openpyxl', 'read_parquet': 'pyarrow', 'read_html': 'lxml'}
SKIP_DIRS = {'.venv', 'venv', '__pycache__', '.git', '.ipynb_checkpoints'}

results = []


def report(level, text):
    results.append(level)
    print(f'[{level}] {text}')


def norm(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def read_requirements(path):
    names = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.split('#', 1)[0].strip()
        if line and not line.startswith('-'):
            names.append(norm(re.split(r'[<>=!~;\[ ]', line, maxsplit=1)[0]))
    return names


def flatten_div(node):
    """Path(...) / "data" / "x.csv" 같은 식에서 글자 조각을 순서대로 모은다."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return flatten_div(node.left) + flatten_div(node.right)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return []


def path_strings(tree):
    """데이터를 읽는 자리에 쓴 경로 글자(read_csv("..."), Path(...) / "...")를 모은다."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
            if name in READERS and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                found.append(node.args[0].value)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            parts = flatten_div(node)
            if parts and not isinstance(getattr(node, 'parent', None), ast.BinOp):
                found.append('/'.join(parts))
    return found


def case_mismatch(folder, rel):
    """윈도·맥은 파일 이름의 대소문자를 구별하지 않아 exists()가 참이어도, 리눅스 서버에서는 못 찾는 이름.
    대소문자만 다른 파일이 폴더에 있으면 그 실제 이름(경로)을, 이름이 똑같거나 파일이 없으면 None을 돌려준다."""
    cur, real, changed = folder, [], False
    for part in Path(rel).parts:
        try:
            names = os.listdir(cur)
        except OSError:
            return None
        if part not in names:
            same = [n for n in names if n.lower() == part.lower()]
            if not same:
                return None
            part, changed = same[0], True
        real.append(part)
        cur = cur / part
    return '/'.join(real) if changed else None


def main():
    app = Path(sys.argv[1] if len(sys.argv) > 1 else 'app.py').resolve()
    folder = app.parent
    print(f'배포 전 점검: {app.name} (폴더 {folder.name})\n')
    # sys.stdlib_module_names와 Streamlit 1.64가 Python 3.10 이상을 쓴다(맥에 원래 있는 python3는 3.9)
    if sys.version_info < (3, 10):
        report('고침', f'Python 3.10 이상이 필요합니다(지금 {sys.version.split()[0]}). '
                     '앱을 실행하던 가상환경(.venv)의 Python으로 다시 실행하세요.')
        return finish()

    # 1. 파일
    if not app.exists():
        report('고침', f'{app.name} 파일이 없습니다. 앱 폴더에서 실행하거나 파일 이름을 적어 주세요.')
        return 1
    req = folder / 'requirements.txt'
    source = app.read_text(encoding='utf-8')
    try:
        tree = ast.parse(source)
    except SyntaxError as e:             # 콜론·괄호·들여쓰기를 빠뜨린 코드는 실행 전에 알린다
        report('고침', f'문법 오류: {e.msg} ({app.name} {e.lineno}번째 줄) → 콜론(:), 괄호, 들여쓰기를 보세요.')
        return finish()
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    # 2. 패키지
    stdlib = set(sys.stdlib_module_names)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module.split('.')[0])
    local = {p.stem for p in folder.glob('*.py')} | {p.name for p in folder.iterdir() if p.is_dir()}
    third = sorted(i for i in imports if i not in stdlib and i not in local and i != '__future__')
    needed = {norm(PIP_NAME.get(i, i)) for i in third}
    calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    needed |= {EXTRA[c] for c in calls if c in EXTRA}
    if not req.exists():
        report('고침', f'requirements.txt가 없습니다. 시작 파일과 같은 폴더에 만들고 {", ".join(sorted(needed))}를 한 줄에 하나씩 적으세요.')
    else:
        listed = read_requirements(req)
        missing = sorted(n for n in needed if n not in listed and n != 'streamlit')
        if missing:
            report('고침', f'requirements.txt에 없는 패키지: {", ".join(missing)} (서버에서 ModuleNotFoundError가 납니다)')
        else:
            report('통과', f'requirements.txt에 외부 패키지 {len(needed)}개가 모두 있습니다: {", ".join(sorted(needed))}')
        if 'streamlit' not in listed:
            report('확인', 'streamlit은 서버가 기본으로 설치하지만, 내 컴퓨터와 같은 버전을 쓰려면 streamlit==버전도 적어 두세요.')
        builtin = sorted(n for n in listed if n.replace('-', '_') in stdlib)
        if builtin:
            report('고침', f'기본 모듈은 requirements.txt에서 빼세요: {", ".join(builtin)}')
        pinned = [l.strip() for l in req.read_text(encoding='utf-8-sig').splitlines() if '==' in l]
        if pinned:
            report('확인', f'고정한 버전 {len(pinned)}개. 내 컴퓨터 버전과 같은지 python -m pip show 패키지이름으로 확인하세요.')

    # 3. 경로
    path_problem = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            if re.match(r'^(?:[A-Za-z]:[\\/]|/(?:Users|home|mnt|Volumes|private|tmp|var)/|~[\\/])', s):
                report('고침', f'내 컴퓨터에만 있는 경로: "{s}" → 앱 폴더 안의 파일로 옮기고 Path(__file__).parent 기준으로 읽으세요.')
                path_problem = True
    for s in dict.fromkeys(path_strings(tree)):
        if s.startswith('http'):
            continue
        if s.startswith('..'):
            report('고침', f'앱 폴더 밖 파일: "{s}" → 저장소에 올라가지 않습니다. 앱 폴더 안으로 옮기세요.')
            path_problem = True
        elif '\\' in s:
            report('고침', f'역슬래시 경로: "{s}" → 배포 서버(리눅스)에서는 / 로 써야 찾습니다.')
            path_problem = True
        elif re.search(DATA_EXT, s, re.I) and not re.match(r'^(?:[A-Za-z]:|/|~)', s) and case_mismatch(folder, s):
            report('고침', f'대소문자가 다른 파일 이름: 코드는 "{s}", 폴더에는 "{case_mismatch(folder, s)}" '
                         '→ 배포 서버(리눅스)는 대소문자를 구별합니다. 코드와 파일 이름을 똑같이 맞추세요.')
            path_problem = True
        elif re.search(DATA_EXT, s, re.I) and not re.match(r'^(?:[A-Za-z]:|/|~)', s) and not (folder / s).exists():
            report('고침', f'앱 폴더에 없는 파일: "{s}" → 이 파일을 앱 폴더에 두고 함께 올리세요.')
            path_problem = True
    data_reads = [s for s in path_strings(tree) if re.search(DATA_EXT, s, re.I)]
    if data_reads and '__file__' not in source:
        report('확인', '배포 서버의 작업 폴더는 저장소 맨 위입니다. app.py를 하위 폴더에 두면 이름만 쓴 경로를 못 찾습니다. '
                     'Path(__file__).parent / "파일이름"으로 읽으면 안전합니다.')
    elif not path_problem:
        report('통과', '경로: 내 컴퓨터 경로나 폴더 밖 파일이 없습니다.')

    # 4. 파일 크기와 올리지 않을 것
    big, secret = [], []
    for p in folder.rglob('*'):
        if any(part in SKIP_DIRS for part in p.relative_to(folder).parts):
            continue
        if p.is_file() and p.stat().st_size > LIMIT_MB * 1024 * 1024:
            big.append(f'{p.relative_to(folder)} ({p.stat().st_size / 1024 / 1024:.0f}MB)')
        if p.name in {'.env', 'secrets.toml'}:
            secret.append(str(p.relative_to(folder)))
    if big:
        report('고침', f'GitHub 브라우저로 올릴 수 없는 크기(파일 하나에 {LIMIT_MB}MB 넘음): {", ".join(big)} '
                     '→ 필요한 열과 기간만 남겨 줄이세요.')
    else:
        report('통과', f'파일 크기: 모두 {LIMIT_MB}MB 이하입니다.')
    if secret:
        report('확인', f'비밀 정보가 담길 수 있는 파일: {", ".join(secret)} → 공개 저장소에 올리지 마세요.')
    if (folder / '.venv').exists() or (folder / 'venv').exists():
        report('확인', '가상환경 폴더(.venv)는 올리지 않습니다. 서버는 requirements.txt로 다시 설치합니다.')

    # 5. 실행
    try:
        from streamlit import config as st_config
        from streamlit.testing.v1 import AppTest
    except ImportError:
        report('고침', '이 Python에 streamlit이 없습니다. 앱을 실행하던 가상환경에서 다시 실행하세요.')
        return finish()
    # 서버 없이 시험 실행할 때마다 나오는 Streamlit 안내 줄(missing ScriptRunContext)만 숨긴다
    logging.getLogger('streamlit.runtime.scriptrunner_utils.script_run_context').addFilter(
        lambda record: 'missing ScriptRunContext' not in record.getMessage())
    # 앱 오류는 아래 [고침] 줄에 오류 이름과 줄 번호로 줄여 적으므로, Streamlit이 터미널에 찍는 긴 오류 상자는 끈다
    try:
        st_config.set_option('logger.enableRich', False)
    except Exception:              # 이 설정이 없는 옛 Streamlit
        pass
    logging.getLogger('streamlit.error_util').addFilter(lambda record: 'Uncaught app execution' not in record.getMessage())
    warnings.filterwarnings('ignore', message='Glyph .* missing')

    def fresh():
        return AppTest.from_file(str(app), default_timeout=60).run()

    at = fresh()
    if at.exception:
        report('고침', f'첫 화면에서 오류: {describe(at.exception[0], app.name)}')
        return finish(source)
    if at.error:
        report('고침', f'첫 화면에 오류 안내가 뜹니다: {at.error[0].value}')
    charts = sum(len(at.get(t)) for t in ('plotly_chart', 'imgs', 'arrow_vega_lite_chart', 'vega_lite_chart',
                                           'deck_gl_json_chart', 'graphviz_chart'))
    kinds = ('multiselect', 'slider', 'selectbox', 'radio', 'checkbox', 'toggle', 'select_slider',
             'number_input', 'text_input', 'date_input')
    widgets = sum(len(getattr(at, k)) for k in kinds)
    report('통과', f'첫 화면 실행: 오류 없음 · 차트 {charts}개 · 입력 위젯 {widgets}개')
    if charts < 3:
        report('확인', f'첫 화면의 차트가 {charts}개입니다. 개인 프로젝트는 차트 3개 이상(조건을 바꿔야 나오는 차트는 세지 못합니다).')
    if widgets == 0:
        report('확인', '입력 위젯이 없습니다. 개인 프로젝트는 위젯으로 조건을 바꾸면 숫자와 차트가 함께 바뀌는 화면입니다.')

    failures, tried = [], 0
    for kind, make in scenarios(at):
        tried += 1
        test = fresh()
        try:
            make(test).run()
        except Exception as ex:          # 위젯 값을 넣는 단계의 오류도 앱 오류로 본다
            failures.append(f'{kind}: {type(ex).__name__}: {ex}')
            continue
        if test.exception:
            failures.append(f'{kind}: {describe(test.exception[0], app.name)}')
    if failures:
        for f in failures:
            report('고침', f'위젯 조작에서 오류 → {f}')
        report('확인', '빈 선택은 st.warning(...)으로 알리고 st.stop()으로 멈추면 오류 대신 안내가 나옵니다.')
    else:
        report('통과', f'위젯 경계값 {tried}가지(모두 지우기·하나만 고르기·선택지마다·범위 끝): 오류 없음')
    return finish(source)


def scenarios(at):
    """위젯마다 경계값을 넣는 동작 목록. 위젯은 순서(번호)로 다시 찾는다."""
    out = []
    for i, w in enumerate(at.multiselect[:3]):
        out.append((f'{w.label} 모두 지우기', lambda t, i=i: t.multiselect[i].set_value([])))
        if w.options:
            out.append((f'{w.label} 하나만', lambda t, i=i, o=w.options[0]: t.multiselect[i].set_value([o])))
    for kind in ('selectbox', 'radio'):
        for i, w in enumerate(getattr(at, kind)[:3]):
            for o in list(w.options)[:6]:
                out.append((f'{w.label} = {o}', lambda t, k=kind, i=i, o=o: getattr(t, k)[i].set_value(o)))
    for i, w in enumerate(at.slider[:3]):
        lo, hi = w.min, w.max
        if isinstance(w.value, (tuple, list)):
            cast = type(w.value[0])
            out.append((f'{w.label} 처음만', lambda t, i=i, v=(cast(lo), cast(lo)): t.slider[i].set_value(v)))
            out.append((f'{w.label} 끝만', lambda t, i=i, v=(cast(hi), cast(hi)): t.slider[i].set_value(v)))
        else:
            cast = type(w.value)
            out.append((f'{w.label} 최솟값', lambda t, i=i, v=cast(lo): t.slider[i].set_value(v)))
            out.append((f'{w.label} 최댓값', lambda t, i=i, v=cast(hi): t.slider[i].set_value(v)))
    for kind in ('checkbox', 'toggle'):
        for i, w in enumerate(getattr(at, kind)[:3]):
            out.append((f'{w.label} 바꾸기', lambda t, k=kind, i=i, v=not w.value: getattr(t, k)[i].set_value(v)))
    return out


def describe(exc, app_name):
    """앱 오류를 '오류 이름: 내용 (app.py n번째 줄)' 꼴로 줄인다."""
    kind = getattr(exc.proto, 'type', '')
    text = f'{kind}: {exc.value}' if kind else str(exc.value)
    for frame in reversed(list(exc.stack_trace or [])):
        m = re.search(re.escape(app_name) + r'", line (\d+)', frame)
        if m:
            return f'{text} ({app_name} {m.group(1)}번째 줄)'
    return text


def finish(source=''):
    # 6. 한글 글꼴
    if re.search(r'^\s*(import|from)\s+(matplotlib|seaborn)', source, re.M):
        try:
            import matplotlib.font_manager as fm
            names = {f.name for f in fm.fontManager.ttflist}
            here = [f for f in ('Malgun Gothic', 'AppleGothic', 'NanumGothic', 'Pretendard') if f in names]
        except ImportError:
            here = []
        report('확인', 'Matplotlib·Seaborn 그림은 서버가 만듭니다. 배포 서버에 한글 글꼴이 없으면 한글이 □로 나오니 '
                     f'배포한 주소에서 꼭 보세요(이 컴퓨터의 한글 글꼴: {", ".join(here) or "없음"}). '
                     'Plotly 차트는 보는 사람의 브라우저가 글자를 그립니다.')
    print()
    n = {k: results.count(k) for k in ('통과', '확인', '고침')}
    print(f'요약: 통과 {n["통과"]} · 확인 {n["확인"]} · 고침 {n["고침"]}')
    print('[고침]을 모두 고친 뒤 GitHub에 올리세요.' if n['고침'] else '올릴 준비가 됐습니다. 배포한 뒤 새 주소에서 [확인] 항목을 보세요.')
    return 1 if n['고침'] else 0


if __name__ == '__main__':
    sys.exit(main())
