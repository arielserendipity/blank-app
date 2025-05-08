# streamlit_app.py 파일의 전체 내용입니다.
# (components.html 사용, 페이지 2 제출 시 무조건 페이지 3 이동)

import streamlit as st
import streamlit.components.v1 as components # components.html 다시 사용
from streamlit_option_menu import option_menu
import json
import time
from datetime import datetime
import os
# import time # 필요 없음

# from graph_component import interactive_graph # 커스텀 컴포넌트 import 삭제

# --- 상수 정의 ---
TEACHER_PASSWORD = "2025"
STUDENT_DATA_DIR = "student_data"

# --- 폴더 생성 ---
if not os.path.exists(STUDENT_DATA_DIR):
    os.makedirs(STUDENT_DATA_DIR)

# --- 함수 정의 --- (save_student_data, get_gpt_feedback 은 호출되지 않으므로 그대로 둠)
def save_student_data(student_name, page, interaction, ai_response=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_student_name = "".join(c if c.isalnum() else "_" for c in student_name)
    filename = os.path.join(STUDENT_DATA_DIR, f"student_{safe_student_name}.json")
    data_entry = {"timestamp": timestamp, "page": page, "interaction": interaction}
    if ai_response: data_entry["ai_response"] = ai_response
    try:
        with open(filename, 'r', encoding='utf-8') as f: data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): data = []
    data.append(data_entry)
    try:
        with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e: st.error(f"데이터 저장 중 오류 발생: {e}")

def get_gpt_feedback(student_name, current_scores):
    # 이 함수는 아래 로직에서 호출되지 않지만, 혹시 모르니 남겨둡니다.
    if not current_scores: return f"{student_name} 학생, 아직 점수가 없어요."
    average_score = sum(current_scores) / len(current_scores)
    target_average = 60
    if abs(average_score - target_average) < 0.01:
        feedback = f"{student_name} 학생, 정확히 목표 평균 {target_average}점을 달성했네요! 아주 잘했어요! '다음 단계' 버튼을 눌러 진행하세요."
    elif average_score > target_average:
        feedback = f"{student_name} 학생, 현재 평균({average_score:.1f})이 목표({target_average})보다 높아요. 그래프를 조절하고 다시 제출해주세요."
    else:
        feedback = f"{student_name} 학생, 현재 평균({average_score:.1f})이 목표({target_average})보다 낮아요. 그래프를 조절하고 다시 제출해주세요."
    return feedback

# --- 페이지 상태 초기화 ---
default_states = {
    'page': 'main', 'student_name': '', 'target_average_page3': 5,
    'show_graph_page_3': False, 'feedback_page_2': None, 'scores_page_2': None,
}
for key, value in default_states.items():
    if key not in st.session_state: st.session_state[key] = value

# --- 페이지 함수 정의 ---

# 학생용 페이지 1: 이름 입력
def student_page_1():
    elapsed = time.time() - st.session_state.enter_time
    st.write(f"접속 시간: {elapsed:.2f}초")
    st.header("평균 학습 시작")
    st.write("환영합니다! 저는 평균 학습을 도와주는 김함정이라고 해요. 학생의 이름을 입력하고 평균을 학습하러 가볼까요?")
    name = st.text_input("이름을 입력하세요", key="student_name_input")
    if st.button("입장하기"):
        if name:
            st.session_state['student_name'] = name
            # save_student_data(name, 1, f"학생 이름 입력: {name}") # 저장 잠시 보류
            st.session_state.update({'feedback_page_2': None, 'scores_page_2': None, 'page': 'student_page_2'})
            st.rerun()
        else: st.warning("이름을 입력해주세요.")
    if st.button("이전"):
        st.session_state['page'] = 'main'
        st.rerun()

# 학생용 페이지 2: 목표 평균 맞추기 (components.html 사용, 무조건 페이지 3 이동)
def student_page_2():
    st.header("목표 평균 도전!")
    st.write(f"{st.session_state['student_name']} 학생, 아래 그래프의 막대를 조절하여 평균 60점을 만들어보세요. 다 만들었다면 아래 '다음 페이지로 이동' 버튼을 누르세요.") # 버튼 이름 변경
    st.info("막대를 위아래로 드래그하여 점수를 조절할 수 있습니다.")

    # HTML 파일 로드 및 표시 (components.html 사용)
    try:
        with open("graph_page_2.html", "r", encoding="utf-8") as f:
            html_graph_1 = f.read()
        # components.html 호출 (반환값, key 사용 안 함)
        components.html(html_graph_1, height=550)
    except FileNotFoundError:
        st.error("오류: graph_page_2.html 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
        return # 파일 없으면 함수 종료
    except Exception as e:
        st.error(f"HTML 컴포넌트 로딩 중 오류 발생: {e}")

    # --- Streamlit 버튼 추가 ---
    # 이 버튼을 누르면 무조건 페이지 3으로 이동합니다.
    navigate_pressed = st.button("다음 페이지로 이동 (테스트)") # 버튼 이름 변경

    if navigate_pressed:
        # 무조건 페이지 3으로 상태 변경 및 rerun
        st.session_state['page'] = 'student_page_3'
        # 페이지 2 관련 상태 초기화 (선택적)
        st.session_state['feedback_page_2'] = None
        st.session_state['scores_page_2'] = None
        st.rerun()

    if st.button("이전"):
        st.session_state['page'] = 'student_page_1'
        st.rerun()

    # --- 피드백 및 조건부 버튼 로직 삭제 ---
    # (위 버튼으로 바로 이동하므로 제거)


# 학생용 페이지 3: 나만의 평균 만들기 (변경 없음)
def student_page_3():
    st.header("나만의 평균 만들기")
    st.write(f"{st.session_state['student_name']} 학생, 앞에서는 평균이 60점으로 주어졌을 때 여러 점수 조합이 가능하다는 것을 확인했어요.")
    st.write("이제는 여러분이 **원하는 평균 점수 (1점 ~ 10점)**를 직접 만들고, 그렇게 만들기 위해 막대 그래프의 값들을 어떻게 조절할 수 있는지 탐색해 보세요!")
    is_input_disabled = st.session_state['show_graph_page_3']
    col1, col2 = st.columns([3, 1])
    with col1:
        target_avg_input = st.number_input("만들고 싶은 평균 점수를 입력하세요 (1~10)", min_value=1, max_value=10, step=1, value=st.session_state['target_average_page3'], disabled=is_input_disabled, key="target_avg_input_page3")
    with col2:
         st.write(""); st.write("")
         if st.button("평균 설정", disabled=is_input_disabled):
              st.session_state['target_average_page3'] = target_avg_input
              st.session_state['show_graph_page_3'] = True
              st.rerun()
    if st.session_state['show_graph_page_3']:
        st.success(f"목표 평균: **{st.session_state['target_average_page3']}** 점")
        st.info("이제 아래 그래프의 막대들을 드래그하여, 실제 평균이 목표 평균과 같아지도록 만들어 보세요! (힌트 버튼으로 현재 평균과 막대 상태 확인 가능)")
        try:
            with open("graph_page_3.html", "r", encoding="utf-8") as f: html_template = f.read()
            js_injection = f"""<script>window.pythonTargetAverage = {st.session_state['target_average_page3']}; console.log("Python Target Average:", window.pythonTargetAverage);</script>"""
            html_graph_2_modified = html_template.replace("</head>", f"{js_injection}</head>", 1)
            components.html(html_graph_2_modified, height=500) # components.html 사용
        except FileNotFoundError: st.error("오류: graph_page_3.html 파일을 찾을 수 없습니다."); return
        except Exception as e: st.error(f"HTML 처리 중 오류 발생: {e}"); return

        if st.button("다른 평균으로 변경하기"):
            st.session_state['show_graph_page_3'] = False
            st.rerun()
    if st.button("이전"):
        st.session_state['page'] = 'student_page_2'
        st.rerun()

# 교사용 페이지 (변경 없음)
def teacher_page():
    st.header("교사용 페이지")
    password = st.text_input("비밀번호를 입력하세요", type="password", key="teacher_pw")
    if password == TEACHER_PASSWORD:
        st.success("접속 성공!")
        st.subheader("학생 학습 데이터 조회")
        try: student_files = [f for f in os.listdir(STUDENT_DATA_DIR) if f.startswith("student_") and f.endswith(".json")]
        except FileNotFoundError: st.error(f"데이터 폴더({STUDENT_DATA_DIR})를 찾을 수 없습니다."); student_files = []
        if not student_files: st.info("아직 저장된 학생 데이터가 없습니다."); return
        selected_student_file = st.selectbox("조회할 학생 데이터를 선택하세요:", student_files)
        if selected_student_file:
            try:
                filepath = os.path.join(STUDENT_DATA_DIR, selected_student_file)
                with open(filepath, 'r', encoding='utf-8') as f: student_data = json.load(f)
                student_display_name = selected_student_file.replace('student_', '').replace('.json', '').replace('_', ' ')
                st.write(f"**{student_display_name}** 학생 데이터:")
                st.json(student_data)
            except Exception as e: st.error(f"데이터 로딩 중 오류 발생: {e}")
    elif password: st.error("비밀번호가 틀렸습니다.")
    if st.button("이전"):
        st.session_state['page'] = 'main'
        st.rerun()

# 메인 페이지 (변경 없음)
def main_page():
    if 'enter_time' not in st.session_state:
        st.session_state.enter_time = time.time()
    st.title("📊 평균 학습 웹 앱")
    st.write("학생 또는 교사로 접속하여 평균 개념을 학습하거나 학습 현황을 확인해보세요.")
    user_type = st.radio("접속 유형 선택:", ("학생용", "교사용"), key="user_type_radio", horizontal=True)
    if st.button("선택 완료"):
        if user_type == "학생용": st.session_state['page'] = 'student_page_1'
        elif user_type == "교사용": st.session_state['page'] = 'teacher_page'
        st.rerun()

# --- 페이지 라우팅 --- (변경 없음)
pages = {
    'main': main_page, 'student_page_1': student_page_1, 'student_page_2': student_page_2,
    'student_page_3': student_page_3, 'teacher_page': teacher_page,
}

with st.sidebar:
    menu = {
        "main": "홈",
        "student_page_1": "학생: 이름 입력",
        "student_page_2": "학생: 목표 평균",
        "student_page_3": "학생: 나만의 평균",
        "teacher_page": "교사용"
    }
    page_keys = list(menu.keys())
    page_labels = list(menu.values())
    selected = option_menu(
        "메뉴", page_labels,
        icons=['house', 'person', 'bar-chart', 'star', 'lock'],
        menu_icon="app-indicator", default_index=page_keys.index(st.session_state['page']) if st.session_state['page'] in page_keys else 0,
    )
    # 메뉴 선택 시 페이지 이동
    selected_key = page_keys[page_labels.index(selected)]
    if st.session_state['page'] != selected_key:
        st.session_state['page'] = selected_key
        st.rerun()
    
render_page = pages.get(st.session_state['page'], main_page)
render_page()