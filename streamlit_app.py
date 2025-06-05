import streamlit as st
from draggable_barchart import draggable_barchart
from draggable_barchart2 import draggable_barchart2

st.set_page_config(layout="wide")
import json, time, os
import pandas as pd
from datetime import datetime
from openai import OpenAI

from streamlit_extras.stylable_container import stylable_container

# --- 상수 및 환경설정 ---
TEACHER_PASSWORD = "2025"
STUDENT_DATA_DIR = "student_data"
INACTIVITY_THRESHOLD_SECONDS = 60

PAGE2_PROBLEM1_GOAL_CONCEPT = "평균이 60이 되는 자료 집합이 다양하다. 평균을 기준으로 초과한 부분과 부족한 부분의 길이(또는 넓이)가 같다."
PAGE2_PROBLEM1_FEEDBACK_LOOP = {
    1: "평균은 모든 자룟값을 모두 더하고 자료의 개수로 나눈 것이에요!",
    2: "각 그래프 막대의 자료의 값이 얼마인지 알아볼까요?",
    3: "그래프의 높낮이를 움직이면서 자료의 총합은 어떻게 변화하나요? '힌트 보기'를 사용해서 그래프가 어떻게 변화하는지 관찰하세요.",
}
PAGE4_PROBLEM3_GOAL_CONCEPT = "자료의 값과 평균 사이의 차이의 총합이 항상 0이 되도록 자료의 값을 조절하면 예측한 평균을 달성할 수 있다는 점을 인지하는 것"
PAGE4_PROBLEM3_SCAFFOLDING_PROMPT = """당신은 학생이 평균 개념을 깊이 이해하도록 돕는 AI 튜터입니다. 학생은 자신이 설정한 평균을 달성하기 위해 그래프 자료의 값을 조절하는 활동을 했습니다. 이 과정에서 자신이 사용한 전략에 대해 설명하라는 질문에 답변했습니다. 학생의 답변이 목표 개념인 "{goal_concept}"과 얼마나 관련 있는지 평가해주세요. 목표 개념을 직접적으로 언급하거나 답을 알려주지 말고, 학생의 현재 이해 수준에서 다음 단계로 나아갈 수 있도록 유도하는 질문이나 발문을 생성해주세요. 학생의 답변이 목표 개념과 거리가 멀다면 기본적인 개념(자료의 총합과 개수)으로 돌아가는 발문을, 조금이라도 관련 있다면 편차의 합 등 심화 개념으로 나아가도록 발문을 시도해주세요. 응답은 'FEEDBACK:' 접두사로 시작해주세요."""
CUMULATIVE_FEEDBACK_4 = "각각의 색이 무엇을 의미하는 지 생각해보세요."
CUMULATIVE_FEEDBACK_5 = "추가 힌트를 드릴게요! 각각의 색의 넓이를 비교해보세요!"

# 아래는 2-3, 2-4 루프/팝업 피드백 추가
PAGE4_PROBLEM3_FEEDBACK_LOOP = {
    1: "평균과 각 자료의 값의 차이를 생각해보면 좋겠어요.",
    2: "평균과 각 자료의 값의 차이의 합이 0이 되는 순간을 찾으셨나요?",
    3: "막대를 조정하면서 평균과 각 자료의 값의 차이 합을 계속 0으로 맞추는 경험이 있었나요?",
}
PAGE4_PROBLEM4_FEEDBACK_LOOP = {
    1: "과제를 해결하면서 알게 된 사실을 생각해보세요!?",
    2: "평균은 자료를 대표하는 값이에요. 평균이 항상 자료 중간에 있나요?",
    3: "평균의 함정은 언제 발생할까요? 너무 큰 값이나 작은 값이 있는 경우를를 생각해보세요.",
}
CUMULATIVE_FEEDBACK_4_4 = "평균이 자료를 대표할 때 갖는 특징에 대해 다시 한 번 천천히 생각해보세요."
CUMULATIVE_FEEDBACK_5_4 = "선생님이 앞서 설명해주신 강 건너기 이야기에 대해 생각해보고, 자료의 값들과 평균이 어떠한 관계가 있는지 생각해보세요!"

if not os.path.exists(STUDENT_DATA_DIR):
    os.makedirs(STUDENT_DATA_DIR)

# --- OPENAI 키 ---
try:
    api_key = st.secrets["openai_api_key"]
    if not api_key:
        st.error("OpenAI API 키가 .streamlit/secrets.toml 파일에 설정되지 않았습니다.")
        st.stop()
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error("OpenAI 키 오류: "+str(e)); st.stop()

# --- 상태 초기화 ---
default_states = {
    'page': 'main',
    'student_name': '',
    'target_average_page3': 5,
    'show_graph_page_3': False,
    'page2_problem_index': 1,
    'p2p1_answer': '',
    'p2p1_feedback': None,
    'p2p1_feedback_history': [],
    'p2p1_correct': False,
    'p2p1_attempts': 0,
    'page2_show_cumulative_popup4': False,
    'page2_show_cumulative_popup5': False,
    'page4_show_cumulative_popup4': False,
    'page4_show_cumulative_popup5': False,
    'last_interaction_time': time.time(),
    'page3_avg_input': 5,
    'page4_problem_index': 1,
    'p4p1_feedback': None, 'p4p1_feedback_history': [], 'p4p1_correct': False, 'p4p1_attempts': 0,
    'p4p2_feedback': None, 'p4p2_feedback_history': [], 'p4p2_correct': False, 'p4p2_attempts': 0,
    'p4p3_answer': '', 'p4p3_feedback': None, 'p4p3_feedback_history': [], 'p4p3_correct': False, 'p4p3_attempts': 0,
    'p4p4_answer': '', 'p4p4_feedback': None, 'p4p4_feedback_history': [], 'p4p4_correct': False, 'p4p4_attempts': 0,
    'chat_log_page2': [],
    'chat_log_page4_p3': [],
    'chat_log_page4_p4': [],
}

for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.markdown(
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css"/>',
    unsafe_allow_html=True,
)

def skip_button():
    with stylable_container(
        key="container_with_border",
        css_styles=r"""
            button {
                border: none;
                background-color: transparent;
            }
            .skip-button {
            margin-top: 10px;
            }
            """,
    ):
        return st.button("☎", key="skip_button")

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.markdown("## 📊 평균 학습 메뉴")
    student_nav = st.button("학생용", use_container_width=True, key="nav_student")
    teacher_nav = st.button("교사용", use_container_width=True, key="nav_teacher")
    if student_nav:
        st.session_state['page'] = 'student_page_1'
        st.rerun()
    if teacher_nav:
        st.session_state['page'] = 'teacher_page'
        st.rerun()
    
    if skip_button():
        if st.session_state['skip']:
            st.session_state[st.session_state['skip'][0]] = st.session_state['skip'][1]
            del st.session_state['skip']
        st.rerun()

# --- 데이터 저장 ---
def save_student_data(student_name, page, problem, student_answer, is_correct, attempt, feedback_history, cumulative_popup_shown, chatbot_interactions):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_student_name = "".join(c if c.isalnum() else "_" for c in student_name)
    filename = os.path.join(STUDENT_DATA_DIR, f"student_{safe_student_name}.json")
    entry = {
        "timestamp": timestamp,
        "page": page,
        "problem": problem,
        "student_answer": student_answer,
        "is_correct": is_correct,
        "attempt": attempt,
        "feedback_history": feedback_history,
        "cumulative_popup_shown": cumulative_popup_shown,
        "chatbot_interactions": chatbot_interactions,
    }
    try:
        with open(filename, "r", encoding="utf-8") as f: data = json.load(f)
    except Exception: data = []
    data.append(entry)
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

def update_page_state_on_entry():
    st.session_state['last_interaction_time'] = time.time()
    st.session_state['page2_show_cumulative_popup4'] = (st.session_state.get('p2p1_attempts',0) >= 4)
    st.session_state['page2_show_cumulative_popup5'] = (st.session_state.get('p2p1_attempts',0) >= 5)
    page4_total = st.session_state.get('p4p1_attempts',0) + st.session_state.get('p4p2_attempts',0) + st.session_state.get('p4p3_attempts',0) + st.session_state.get('p4p4_attempts',0)
    st.session_state['page4_show_cumulative_popup4'] = (page4_total >= 4)
    st.session_state['page4_show_cumulative_popup5'] = (page4_total >= 5)

# 수정된 팝업 함수: 2-1, 2-2는 팝업/누적 X
def setup_columns_and_display_popups(current_page):
    graph_col, task_col, popup_col = None, None, None
    # 페이지4 과제별로 팝업 제어
    if current_page == 'student_page_4_myavg_tasks':
        current_problem_index = st.session_state.get('page4_problem_index', 1)
        if current_problem_index in [1, 2]:
            graph_col, task_col = st.columns([1, 1])
            return graph_col, task_col, popup_col
    if current_page in ['student_page_2_graph60', 'student_page_3_myavg_setup', 'student_page_4_myavg_tasks']:
        if current_page == 'student_page_3_myavg_setup':
            main_col, popup_col = st.columns([0.7, 0.3])
            with popup_col:
                elapsed_time = time.time() - st.session_state.last_interaction_time
                if elapsed_time > INACTIVITY_THRESHOLD_SECONDS:
                    st.info('고민하고 있는건가요? 평균을 직접 입력해보세요!', icon="💡")
            return main_col, None, popup_col
        graph_col, task_col, popup_col = st.columns([0.4,0.4,0.2])
        with popup_col:
            elapsed_time = time.time() - st.session_state.last_interaction_time
            if elapsed_time > INACTIVITY_THRESHOLD_SECONDS:
                st.info('고민하고 있는건가요? 그래프의 높낮이를 움직이면서 어떤 변화가 있는지 살펴보세요.', icon="💡")
            if current_page == 'student_page_2_graph60':
                if st.session_state.get('page2_show_cumulative_popup5', False):
                    st.warning(CUMULATIVE_FEEDBACK_5, icon="🚨")
                elif st.session_state.get('page2_show_cumulative_popup4', False):
                    st.warning(CUMULATIVE_FEEDBACK_4, icon="⚠️")
            if current_page == 'student_page_4_myavg_tasks':
                # 2-3, 2-4만 누적 피드백!
                current_problem_index = st.session_state.get('page4_problem_index', 1)
                if current_problem_index == 3:
                    if st.session_state.get('p4p3_attempts',0) >= 5:
                        st.warning(CUMULATIVE_FEEDBACK_5, icon="🚨")
                    elif st.session_state.get('p4p3_attempts',0) >= 4:
                        st.warning(CUMULATIVE_FEEDBACK_4, icon="⚠️")
                elif current_problem_index == 4:
                    if st.session_state.get('p4p4_attempts',0) >= 3:
                        st.warning(CUMULATIVE_FEEDBACK_5_4, icon="🚨")
                    elif st.session_state.get('p4p4_attempts',0) >= 2:
                        st.warning(CUMULATIVE_FEEDBACK_4_4, icon="⚠️")
        return graph_col, task_col, popup_col
    else:
        return None, None, None

# --- GPT 평가 함수 ---
def evaluate_page2_problem1_with_gpt(student_answer, goal_concept):
    system_message = f"""당신은 학생이 평균 개념 학습을 돕는 AI 튜터입니다. 학생은 그래프 조작 후 "{goal_concept}" 개념과 관련하여 알게된 사실을 설명했습니다. 학생의 답변이 목표 개념을 달성했는지 평가해주세요. 구체적으로 목표가 무엇인지 언급하면 안됩니다. 학생이 자연스럽게 평균이 60이어도 다양한 자료 집합을 가질 수 있음을 알게해주도록 촉진해주는 발문을 해주세요. 
평가 결과는 반드시 'CORRECT:' 또는 'INCORRECT:' 접두사로 시작해주세요. 그 뒤에 학생의 답변에 대한 짧고 격려하는 피드백을 추가해주세요. 피드백은 반드시 공백 포함 160자 이내로만 작성해주세요. 초등학생이 교육대상이므로 어렵거나 추상적인 표현 대신, 초등학생도 이해하기 쉬운 다정한 언어로 설명해주세요. 예를 들어, '평균선을 기준으로 높은 부분과 낮은 부분이 같아.', '보라색과 초록색의 넓이가 같아' 등의 응답도 학습 목표를 달성했다고 봅니다. """
    user_message = f"""학생의 답변: {student_answer}"""
    messages = [{"role":"system","content":system_message},{"role":"user","content":user_message}]
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            max_tokens=120,
            temperature=0.5,
        )
        gpt_text = response.choices[0].message.content.strip()
        gpt_text = gpt_text[:200]
        if gpt_text.lower().startswith("correct:"):
            return True, gpt_text[len("correct:"):].strip()
        elif gpt_text.lower().startswith("incorrect:"):
            return False, gpt_text[len("incorrect:"):].strip()
        else:
            return False, "답변을 이해하기 어렵습니다. 다시 설명해주시겠어요?"
    except Exception as e:
        st.error(f"GPT API 오류: {e}")
        return False, "GPT 오류"

def evaluate_page4_problem3_with_gpt(student_answer, goal_concept, scaffolding_prompt):
    system_message = f"""당신은 학생이 평균 개념 학습을 돕는 AI 튜터입니다. 학생은 자신이 설정한 평균을 달성하기 위해 그래프를 조작하였고, 그에 따른 학생의 전략을 물어보는 과제입니다.  그래프 조작 후 "{PAGE4_PROBLEM3_GOAL_CONCEPT}" 개념과 관련하여 알게된 사실을 설명했습니다. 학생의 답변이 목표 개념을 달성했는지 평가해주세요. 구체적으로 목표가 무엇인지 언급하면 안됩니다. 학생이 자연스럽게 하나의 평균에도 다양한 자료 집합을 가질 수 있음을 알게해주도록 촉진해주는 발문을 해주세요. 
평가 결과는 반드시 'CORRECT:' 또는 'INCORRECT:' 접두사로 시작해주세요. 그 뒤에 학생의 답변에 대한 짧고 격려하는 피드백을 추가해주세요. 피드백은 반드시 공백 포함 160자 이내로만 작성해주세요. 초등학생이 교육대상이므로 어렵거나 추상적인 표현 대신, 초등학생도 이해하기 쉬운 다정한 언어로 설명해주세요. 예를 들어, '평균선을 기준으로 높은 부분과 낮은 부분이 같아.', '자료의 값들을 다 더하면 평균*5야' 등의 응답도 학습 목표를 달성했다고 봅니다. """
    user_message = f"""학생의 답변: {student_answer}"""
    messages = [{"role":"system","content":system_message},{"role":"user","content":user_message}]
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            max_tokens=120,
            temperature=0.5,
        )
        gpt_text = response.choices[0].message.content.strip()
        gpt_text = gpt_text[:200]  # 200자 이내로 자르기 (필요하다면)
        if gpt_text.lower().startswith("correct:"):
            return True, gpt_text[len("correct:"):].strip()
        elif gpt_text.lower().startswith("incorrect:"):
            return False, gpt_text[len("incorrect:"):].strip()
        elif gpt_text.lower().startswith("feedback:"):
            # 이전 코드 호환, feedback 접두사로 온 경우도 INCORRECT로 처리
            return False, gpt_text[len("feedback:"):].strip()
        else:
            return False, "답변을 이해하기 어렵습니다. 다시 설명해주시겠어요?"
    except Exception as e:
        st.error(f"GPT API 오류: {e}")
        return False, "GPT 오류"


def evaluate_page4_problem4_with_gpt(student_answer):
    system_message = """당신은 학생이 평균 개념을 깊이 이해하도록 돕는 AI 튜터입니다. 학생은 평균의 특징이나 '평균의 함정'에 대해 자신이 알게된 사실을 설명했습니다. 학생 답변 내용과 관련된 평균의 추가적인 특징이나 흥미로운 점에 대해 짧게 언급하며 탐구를 유도해주세요. 정답/오답 판단보다는 학생의 생각을 확장하는 데 집중해주세요. 학생에게 유도할 평균의 특징은 다음과 같습니다. 
    A. 평균은 극단값들 사이에 위치한다.
B. 평균으로부터의 편차들의 합은  0이다.
C. 평균은 평균 이외의 값들에 의해 영향을 받는다.
D. 평균은 반드시 합산된 값들 중 하나와 같지 않을 수도 있다.
E. 평균은 물리적 현실에서 대응되는 값이 없을 수도 있는 분수일 수 있다.
F. 평균을 계산할 때  만약  0이라는 값이 나타나면 반드시 고려해야 한다.
G. 평균값은 평균화된(were averaged) 값들을 대표한다. 그렇지만 '편차', '합산', '대응'등 과 같은 용어를 직접적으로 사용해서는 안됩니다. 최대한 초등학생이 이해하기 쉽도록 설명해주세요.
답은 'FEEDBACK:' 접두사로 시작해주세요."""
    user_message = f"""학생의 답변: {student_answer}"""
    messages = [{"role": "system", "content": system_message}, {"role": "user", "content": user_message}]
    try:
        response = client.chat.completions.create(
            model="gpt-4.1", messages=messages, max_tokens=200, temperature=0.8,
        )
        gpt_text = response.choices[0].message.content.strip()
        if gpt_text.lower().startswith("feedback:"):
            return True, gpt_text[len("feedback:"):].strip()
        else:
            return True, "평균에 대해 좋은 생각을 공유해주었어요!"
    except Exception as e:
        st.error(f"GPT API 오류: {e}")
        return True, "GPT 오류"

# --- 학생 페이지 1 ---
def student_page_1():
    update_page_state_on_entry()
    st.header("평균 학습 시작")
    name = st.text_input("이름을 입력하세요", key="student_name_input")
    if st.button("입장하기", key="btn_enter_student1"):
        if name:
            st.session_state['student_name'] = name
            st.session_state['page'] = 'student_page_2_graph60'
            st.rerun()
        else:
            st.warning("이름을 입력해주세요.")
    if st.button("뒤로 가기", key="back_student1"):
        st.session_state['page'] = 'main'
        st.rerun()
    if 'p2_mini_question_step' not in st.session_state:
        st.session_state.p2_mini_question_step = 1 # 현재 진행할 미니 질문 번호
        st.session_state.p2_mini_q1_answer = None
        st.session_state.p2_mini_q1_reason = ""
        st.session_state.p2_mini_q1_reason_submitted = False
        st.session_state.p2_mini_q1_feedback = None
        st.session_state.p2_mini_q2_answer = None
        st.session_state.p2_mini_q2_reason = ""
        st.session_state.p2_mini_q2_reason_submitted = False
        st.session_state.p2_mini_q2_feedback = None
        st.session_state.p2_mini_q3_answer = None
        st.session_state.p2_mini_q3_reason = ""
        st.session_state.p2_mini_q3_reason_submitted = False
        st.session_state.p2_mini_q3_feedback = None
        st.session_state.p2_mini_q4_answer = None # 숫자 입력 받을 예정
        st.session_state.p2_mini_q4_feedback = None
        st.session_state.p2_mini_questions_completed = False

# --- 학생 페이지 2 (목표 평균 60, 과제 1, 챗봇, 피드백, 저장) ---
def student_page_2_graph60():
    update_page_state_on_entry()
    st.header("함정이는 다섯 번의 수학 시험에 정확히 평균 60점을 받고 싶어합니다.")
    st.info("함정이의 수학 시험 점수 평균이 60점이 되려면 다섯 번의 시험 점수가 어떻게 되어야 할지, 즉 막대를 위아래로 조정하며 탐구해봅시다.")
    graph_col, task_col, popup_col = setup_columns_and_display_popups('student_page_2_graph60')
    
    with graph_col:
        if st.session_state.get('page2_show_cumulative_popup5', False):
            if len(st.session_state['chat_log_page2']) == 0:
                st.session_state['chat_log_page2'] = [
                    {"role": "assistant", "content": "그래프의 높낮이를 조절하면서 어떤 변화가 있는지 살펴보고, 도움이 필요한 부분이 있다면 질문해주세요."},
                ]
        if 'graph_prev_values' not in st.session_state:
            st.session_state['graph_prev_values'] = (0, 0, 0, 0, 0)
        result = tuple(draggable_barchart("graph_page_2", labels=["1회", "2회", "3회", "4회", "5회"], hint=st.session_state.get('p2_graph_hint', False)))
        if result != st.session_state['graph_prev_values']:
            st.session_state['graph_prev_values'] = result

    with task_col:
        # --- 추가된 미니 질문 섹션 ---
        current_step = st.session_state.p2_mini_question_step
        # 질문 1: 0점 맞아도 평균 60점 가능?
        if current_step == 1:
            st.subheader("예제 1/4")
            q1_answer = st.radio(
                "함정이가 실수로 한 번의 수학 시험에서 0점을 맞아도, 정확히 평균 60점이 될 수 있는 방법이 있나요?",
                ("예", "아니오"), 
                key="p2_mini_q1_radio", 
                index=None, # 선택되지 않은 상태로 시작
                horizontal=True
            )
            if st.button("예제 1 답변 제출", key="btn_p2_q1_submit"):
                st.session_state.p2_mini_q1_answer = q1_answer
                save_student_data(
                    student_name=st.session_state['student_name'],
                    page=2,
                    problem="예제1-답변", # 문제 식별자 변경
                    student_answer=q1_answer,
                    is_correct=(q1_answer == "예"), # 정답 여부
                    attempt=1, # 첫 시도로 간주 (또는 시도 횟수 관리 변수 사용)
                    feedback_history=[st.session_state.p2_mini_q1_feedback if st.session_state.p2_mini_q1_feedback else "정답" if q1_answer == "예" else "오답"],
                    cumulative_popup_shown=[], # 미니 질문에는 팝업 없음
                    chatbot_interactions=[] # 미니 질문에는 챗봇 없음
                )
                if q1_answer == "예":
                    st.session_state.p2_mini_q1_feedback = None # 정답이므로 피드백 없음
                    st.session_state.p2_mini_question_step = 1.5 # 이유 질문으로 이동
                else:
                    st.session_state.p2_mini_q1_feedback = "오답입니다. 막대 중 하나를 0점으로 조정했을 때 어떤 변화가 생기는지 그래프에서 직접 살펴보세요. 다른 점수들을 높여서 평균 60점을 만들 수 있을까요?"
                st.rerun()
            
            if st.session_state.p2_mini_q1_feedback:
                st.warning(st.session_state.p2_mini_q1_feedback)

        elif current_step == 1.5: # 질문 1 이유
            st.subheader("예제 1/4 - 이유")
            st.info("정답입니다! 한 번 0점을 맞아도 평균 60점이 될 수 있습니다.")
            q1_reason = st.text_input(
                "그렇게 생각한 이유는 무엇인가요?", 
                key="p2_mini_q1_reason_input",
                value=st.session_state.p2_mini_q1_reason
            )
            if st.button("이유 제출", key="btn_p2_q1_reason_submit"):
                st.session_state.p2_mini_q1_reason = q1_reason # 입력된 이유를 세션에 저장
                # 이유가 비어있는지 확인 (양쪽 공백 제거 후)
                if not q1_reason.strip(): # .strip()으로 앞뒤 공백 제거 후 비어있는지 체크
                    st.error("이유를 입력해주세요. 이유를 입력해야 다음 질문으로 넘어갈 수 있습니다.")
                    # st.rerun() # 에러 메시지 표시 후 현재 상태 유지 (선택적)
                else:
                    save_student_data(
                        student_name=st.session_state['student_name'],
                        page=2,
                        problem="예제1-이유", # 문제 식별자 변경
                        student_answer=q1_reason,
                        is_correct=True, # 이유는 정오 판단 없이 저장 (또는 GPT 평가 후 결정)
                        attempt=1,
                        feedback_history=[], # 이유에는 별도 피드백 루프 없음 (필요시 추가)
                        cumulative_popup_shown=[],
                        chatbot_interactions=[]
                    )
                    st.session_state.p2_mini_q1_reason_submitted = True
                    st.session_state.p2_mini_question_step = 2 # 다음 질문으로
                    st.success("좋아요! 다음 질문으로 넘어갑니다.")
                    st.rerun() # 성공 시 다음 단계로 UI 업데이트
        
        # 질문 2: 100점 맞아도 평균 60점 가능?
        if current_step == 2:
            st.subheader("예제 2/4")
            q2_answer = st.radio(
                "함정이가 한 번의 시험에서 100점을 맞아도, 정확히 평균 60점이 될 수 있는 방법이 있나요?",
                ("예", "아니오"), 
                key="p2_mini_q2_radio", 
                index=None,
                horizontal=True
            )
            if st.button("예제 2 답변 제출", key="btn_p2_q2_submit"):
                st.session_state.p2_mini_q2_answer = q2_answer
                save_student_data(
                    student_name=st.session_state['student_name'],
                    page=2,
                    problem="예제2-답변",
                    student_answer=q2_answer,
                    is_correct=(q2_answer == "예"),
                    attempt=1,
                    feedback_history=[st.session_state.p2_mini_q2_feedback if st.session_state.p2_mini_q2_feedback else "정답" if q2_answer == "예" else "오답"],
                    cumulative_popup_shown=[],
                    chatbot_interactions=[]
                )
                if q2_answer == "예":
                    st.session_state.p2_mini_q2_feedback = None
                    st.session_state.p2_mini_question_step = 2.5 
                else:
                    st.session_state.p2_mini_q2_feedback = "오답입니다. 막대 중 하나를 100점으로 조정했을 때 어떤 변화가 생기는지 그래프에서 직접 살펴보세요. 다른 점수들을 낮춰서 평균 60점을 만들 수 있을까요?"
                st.rerun()

            if st.session_state.p2_mini_q2_feedback:
                st.warning(st.session_state.p2_mini_q2_feedback)
        
        elif current_step == 2.5: # 질문 2 이유
            st.subheader("예제 2/4 - 이유")
            st.info("정답입니다! 한 번 100점을 맞아도 평균 60점이 될 수 있습니다.")
            q2_reason = st.text_input(
                "그렇게 생각한 이유는 무엇인가요?", 
                key="p2_mini_q2_reason_input",
                value=st.session_state.p2_mini_q2_reason
            )
            if st.button("이유 제출", key="btn_p2_q2_reason_submit"):
                st.session_state.p2_mini_q2_reason = q2_reason
                if not q2_reason.strip():
                    st.error("이유를 입력해주세요. 이유를 입력해야 다음 질문으로 넘어갈 수 있습니다.")
                else:
                    save_student_data(
                        student_name=st.session_state['student_name'],
                        page=2,
                        problem="예제2-이유",
                        student_answer=q2_reason,
                        is_correct=True,
                        attempt=1,
                        feedback_history=[],
                        cumulative_popup_shown=[],
                        chatbot_interactions=[]
                    )
                    st.session_state.p2_mini_q2_reason_submitted = True
                    st.session_state.p2_mini_question_step = 3
                    st.success("훌륭해요! 다음 질문으로 넘어갑니다.")
                    st.rerun()

        # 질문 3: 0점과 100점 동시 가능?
        if current_step == 3:
            st.subheader("예제 3/4")
            q3_answer = st.radio(
                "함정이가 한 번의 시험에서 0점, 다른 한 번의 시험에서 100점을 맞아도, 정확히 평균 60점이 될 수 있는 방법이 있나요?",
                ("예", "아니오"), 
                key="p2_mini_q3_radio", 
                index=None,
                horizontal=True
            )
            if st.button("예제 3 답변 제출", key="btn_p2_q3_submit"):
                st.session_state.p2_mini_q3_answer = q3_answer
                save_student_data(
                    student_name=st.session_state['student_name'],
                    page=2,
                    problem="예제3-답변",
                    student_answer=q3_answer,
                    is_correct=(q3_answer == "예"),
                    attempt=1,
                    feedback_history=[st.session_state.p2_mini_q3_feedback if st.session_state.p2_mini_q3_feedback else "정답" if q3_answer == "예" else "오답"],
                    cumulative_popup_shown=[],
                    chatbot_interactions=[]
                )
                if q3_answer == "예":
                    st.session_state.p2_mini_q3_feedback = None
                    st.session_state.p2_mini_question_step = 3.5
                else:
                    st.session_state.p2_mini_q3_feedback = "오답입니다. 막대 중 하나를 0점, 다른 하나를 100점으로 조정해보세요. 나머지 점수들로 평균 60점을 만들 수 있을지 생각해보세요."
                st.rerun()
            
            if st.session_state.p2_mini_q3_feedback:
                st.warning(st.session_state.p2_mini_q3_feedback)

        elif current_step == 3.5: # 질문 3 이유
            st.subheader("예제 3/4 - 이유")
            st.info("정답입니다! 0점과 100점을 동시에 맞아도 평균 60점이 될 수 있습니다.")
            q3_reason = st.text_input(
                "그렇게 생각한 이유는 무엇인가요?", 
                key="p2_mini_q3_reason_input",
                value=st.session_state.p2_mini_q3_reason
            )
            if st.button("이유 제출", key="btn_p2_q3_reason_submit"):
                st.session_state.p2_mini_q3_reason = q3_reason
                if not q3_reason.strip():
                    st.error("이유를 입력해주세요. 이유를 입력해야 다음 질문으로 넘어갈 수 있습니다.")
                else:
                    save_student_data(
                        student_name=st.session_state['student_name'],
                        page=2,
                        problem="예제1-이유", # 문제 식별자 변경
                        student_answer=q3_reason,
                        is_correct=True, # 이유는 정오 판단 없이 저장 (또는 GPT 평가 후 결정)
                        attempt=1,
                        feedback_history=[], # 이유에는 별도 피드백 루프 없음 (필요시 추가)
                        cumulative_popup_shown=[],
                        chatbot_interactions=[]
                    )
                    st.session_state.p2_mini_q3_reason_submitted = True
                    st.session_state.p2_mini_question_step = 4
                    st.success("정확합니다! 마지막 질문입니다.")
                    st.rerun()

        # 질문 4: 총점은?
        if current_step == 4:
            st.subheader("예제 4/4")
            q4_answer = st.number_input(
                "함정이가 다섯 번의 수학 시험을 통해 정확히 평균 60점을 받으려면 다섯 번의 수학 시험 점수의 합은 얼마여야 할까요? (단위: 점)",
                min_value=0, 
                step=1,
                key="p2_mini_q4_num_input",
                value=st.session_state.get("p2_mini_q4_answer") # 이전 입력값 유지
            )
            if st.button("예제 4 답변 제출", key="btn_p2_q4_submit"):
                st.session_state.p2_mini_q4_answer = q4_answer
                save_student_data(
                    student_name=st.session_state['student_name'],
                    page=2,
                    problem="예제4-답변",
                    student_answer=str(q4_answer), # 숫자 답변을 문자열로 변환하여 저장
                    is_correct=(q4_answer == 300),
                    attempt=1,
                    feedback_history=[st.session_state.p2_mini_q4_feedback if st.session_state.p2_mini_q4_feedback else "정답" if q4_answer == 300 else "오답"],
                    cumulative_popup_shown=[],
                    chatbot_interactions=[]
                )
                if q4_answer == 300:
                    st.session_state.p2_mini_q4_feedback = None
                    st.session_state.p2_mini_question_step = 5 # 모든 미니 질문 완료
                    st.session_state.p2_mini_questions_completed = True
                    st.success("정답입니다! 이제 원래 과제를 해결해봅시다.")
                else:
                    st.session_state.p2_mini_q4_feedback = "아쉬워요. 평균을 구하는 방법은 '주어진 자료의 값들을 모두 더하고, 자료의 개수로 나누는 것'이에요. 그렇다면 평균이 60점이고 자료가 5개일 때, 총합은 얼마일까요?"
                st.rerun()
            
            if st.session_state.p2_mini_q4_feedback:
                st.warning(st.session_state.p2_mini_q4_feedback)        
        if st.session_state.get('p2_mini_questions_completed', False):
            st.subheader("과제 1")
            st.write("함정이의 수학 점수 평균이 정확히 60점이 될 때, 다섯 번의 시험 점수는 어떻게 이루어져있었나요? 막대의 높낮이를 움직이면서 **알게된 사실**은 무엇인가요?")
            is_input_disabled = st.session_state.get('p2p1_correct', False)
            student_answer = st.text_area("여기에 알게된 사실을 작성하세요:", height=150, key="p2p1_answer_input", value=st.session_state.get('p2p1_answer', ''), disabled=is_input_disabled)
            if st.session_state.get('p2p1_attempts',0) >= 3:
                if st.button("힌트 보기", key="btn_hint_p2p1"):
                    st.session_state['p2_graph_hint'] = True
            if st.button("답변 제출", key="btn_submit_p2p1", disabled=is_input_disabled):
                st.session_state['p2p1_answer'] = student_answer
                is_correct, gpt_comment = evaluate_page2_problem1_with_gpt(student_answer, PAGE2_PROBLEM1_GOAL_CONCEPT)
                feedback_history = st.session_state.get('p2p1_feedback_history', [])
                if is_correct:
                    st.session_state['p2p1_correct'] = True
                    st.session_state['p2p1_feedback'] = f"🎉 {gpt_comment} 정말 잘했어요!"
                    feedback_history.append(st.session_state['p2p1_feedback'])
                else:
                    if not st.session_state.get('p2p1_correct', False):
                        st.session_state['p2p1_attempts'] += 1
                    attempt = st.session_state['p2p1_attempts']
                    sequential_feedback = PAGE2_PROBLEM1_FEEDBACK_LOOP.get(min(attempt, len(PAGE2_PROBLEM1_FEEDBACK_LOOP)), PAGE2_PROBLEM1_FEEDBACK_LOOP[len(PAGE2_PROBLEM1_FEEDBACK_LOOP)])
                    st.session_state['p2p1_feedback'] = f"음... 다시 생각해볼까요? {sequential_feedback} {gpt_comment}"
                    feedback_history.append(st.session_state['p2p1_feedback'])
                st.session_state['p2p1_feedback_history'] = feedback_history
                popups = []
                if st.session_state.get('page2_show_cumulative_popup4', False): popups.append(4)
                if st.session_state.get('page2_show_cumulative_popup5', False): popups.append(5)
                chatbot_interactions = st.session_state['chat_log_page2'] if st.session_state.get('page2_show_cumulative_popup5', False) else []
                save_student_data(
                    st.session_state['student_name'], 2, "과제1", student_answer, is_correct, st.session_state['p2p1_attempts'],
                    feedback_history, popups, chatbot_interactions
                )
                st.rerun()
            if st.session_state.get('p2p1_feedback'):
                if st.session_state.get('p2p1_correct', False):
                    st.success(st.session_state['p2p1_feedback'])
                else:
                    st.warning(st.session_state['p2p1_feedback'])
            chatLog = st.session_state['chat_log_page2']
            if st.session_state.get('page2_show_cumulative_popup5', False) and len(chatLog) > 0:
                for chat in chatLog:
                    if chat["role"] == "system": continue
                    with st.chat_message(chat["role"]): st.markdown(chat["content"])
                chat_input = st.chat_input("답변:")
                if chat_input:
                    st.session_state['chat_log_page2'].append({"role":"system","content":"학생이 그래프를 조작하고 있습니다. 그래프의 값: "+str({f"{i+1}회":v for i,v in enumerate(result)})})
                    st.session_state['chat_log_page2'].append({"role": "user", "content": chat_input})
                    st.rerun()
                elif chatLog[-1]["role"] == "user":
                    response = client.chat.completions.create(model="gpt-4.1",messages=chatLog)
                    st.session_state['chat_log_page2'].append({"role": "assistant", "content": response.choices[0].message.content})
                    st.rerun()
            

            st.session_state['skip'] = ('page', 'student_page_3_myavg_setup')

            if st.session_state.get('p2p1_correct', False):
                if st.button("다음(나만의 평균 설정)", key="btn_next_p2"):
                    st.session_state['page'] = 'student_page_3_myavg_setup'
                    st.rerun()
            elif st.session_state.get('p2p1_feedback'):
                st.info("정답을 맞춰야 다음 단계로 넘어갈 수 있습니다.")
    if st.button("뒤로 가기", key="back_student2"):
        st.session_state['page'] = 'student_page_1'
        st.session_state['p2_graph_hint'] = False  # 뒤로 가면 힌트 초기화
        st.session_state['p4_graph_hint'] = False  # 뒤로 가면 힌트 초기화
        st.rerun()

# --- 학생 페이지 3 (나만의 평균 설정) ---
def student_page_3_myavg_setup():
    update_page_state_on_entry()
    st.header("초등학생 다섯 명의 일주일 용돈 평균을 예측해 봅시다.")
    st.write(f"{st.session_state.get('student_name','학생')} 학생, 우리는 초등학생 다섯 명의 일주일 용돈 평균을 예측해보려고 합니다. 내가 예측한 초등학생의 일주일 용돈 평균(최소 1000원, 최대 9000원)을 입력하세요!")
    main_col, _, popup_col = setup_columns_and_display_popups('student_page_3_myavg_setup')
    with main_col: # setup_columns_and_display_popups에서 반환된 main_col 사용
        # st.write("내가 예측한 평균 용돈:") # 선택적으로 레이블을 더 명확하게 추가할 수 있습니다.

        # 값 가져오기 및 범위 제한
        min_val = 1
        max_val = 9

        # st.number_input의 key는 "page3_avg_input"입니다.
        # 이 key를 사용하여 세션 상태에서 값을 가져오고, 없으면 'target_average_page3' 또는 기본값 5를 사용합니다.
        initial_value_candidate = st.session_state.get('page3_avg_input', st.session_state.get('target_average_page3', 5))

        # 값 제한 로직
        clamped_value = max(min_val, min(initial_value_candidate, max_val))
        if 'page3_avg_input' not in st.session_state or st.session_state.page3_avg_input != clamped_value:
            st.session_state.page3_avg_input = clamped_value


        # 열(column)을 사용하여 number_input과 단위를 배치
        # col_input의 너비 비율을 작게 설정하여 입력칸이 좁아 보이도록 합니다.
        # 비율은 전체 main_col의 너비와 디자인에 따라 조정합니다. 예: [입력칸, 단위칸, 빈 공간]
        col_input, col_unit, col_spacer = st.columns([0.3, 0.2, 0.5]) # 비율 예시, 조정 필요

        with col_input:
            # st.number_input 위젯
            # 레이블은 "일주일 용돈 (1~9)천원"으로 유지하되, label_visibility로 숨깁니다.
            # 또는, st.write로 외부 레이블을 쓰고, 여기서는 label을 간결하게 하거나 비워둘 수 있습니다.
            avg_input_value = st.number_input(
                "일주일 용돈 (1~9)천원",  # 위젯의 기본 레이블 (숨겨짐)
                min_value=min_val,
                max_value=max_val,
                value=clamped_value, # 제한된 초기값 사용
                key="page3_avg_input", # 이 key로 st.session_state에 값이 저장/로드됨
                label_visibility="collapsed", # 위젯 자체의 레이블 숨기기
                step=1 # 정수 단위로 변경
            )

        with col_unit:
            # "천원" 단위를 number_input 옆에 표시
            # 수직 정렬을 위해 HTML/CSS 사용 (약간의 margin-top)
            st.markdown(
                "<div style='margin-top: 8px; white-space: nowrap;'>천원</div>",
                unsafe_allow_html=True
            )
        if st.button("평균 설정", key="btn_set_avg_p3"):
            
            st.session_state['target_average_page3'] = st.session_state.page3_avg_input
            st.session_state['page'] = 'student_page_4_myavg_tasks'
            # 과제 시도, 피드백 등 상태 초기화
            for k in ['page4_problem_index', 'p4p1_feedback', 'p4p1_feedback_history', 'p4p1_correct', 'p4p1_attempts',
                      'p4p2_feedback', 'p4p2_feedback_history', 'p4p2_correct', 'p4p2_attempts',
                      'p4p3_answer', 'p4p3_feedback', 'p4p3_feedback_history', 'p4p3_correct', 'p4p3_attempts',
                      'p4p4_answer', 'p4p4_feedback', 'p4p4_feedback_history', 'p4p4_correct', 'p4p4_attempts',
                      'chat_log_page4_p3', 'chat_log_page4_p4']:
                if k in st.session_state: del st.session_state[k]
            st.session_state['page4_problem_index'] = 1
            st.rerun()
    if st.button("뒤로 가기", key="back_student3"):
        st.session_state['page'] = 'student_page_2_graph60'
        st.session_state['p2_graph_hint'] = False  # 뒤로 가면 힌트 초기화
        st.session_state['p4_graph_hint'] = False  # 뒤로 가면 힌트 초기화
        st.rerun()

# --- 학생 페이지 4 (나만의 평균 과제) ---
def student_page_4_myavg_tasks():
    update_page_state_on_entry()
    target_avg = st.session_state.get('target_average_page3', 5)
    current_problem_index = st.session_state.get('page4_problem_index', 1)
    st.header(f"내가 예측한 초등학생들의 일주일 용돈 평균 {target_avg}000원이 되도록 하는 자료의 값들이 어떻게 구성될지 생각해봅시다.")
    st.write(f"{st.session_state.get('student_name', '학생')} 학생이 설정한 평균 **{target_avg}**000원이 되도록 하는 다섯 명의 용돈(자료의 값)은 어떻게 구성되어 있을지 탐구해 봅시다.")
    graph_col, task_col, popup_col = setup_columns_and_display_popups('student_page_4_myavg_tasks')
    with graph_col:
        result = tuple(draggable_barchart2("graph_page_4", labels=["친구1", "친구2", "친구3", "친구4", "친구5"], hint=st.session_state.get('p4_graph_hint', False), target_avg=target_avg))
        st.session_state['graph2_average'] = sum(result) / len(result)
    with task_col:
        # 과제 2-1
        if current_problem_index == 1:
            st.subheader("과제 2-1")
            st.write(f"내가 예측한 일주일 용돈 평균 {target_avg}000원이 되려면 친구 1~5의 용돈은 얼마여야 할까요? \n 각 친구들의 막대그래프를 위 아래로 조정하여 평균이 {target_avg}000원이 되도록 만들어보세요. 막대그래프의 단위는 천원입니다.")
            if st.button("제출", key="btn_submit_p4p1"):
                st.session_state['p4p1_attempts'] += 1
                current_avg = st.session_state.get('graph2_average', 0)
                current_sum = sum(result)
                answer = abs(current_avg - target_avg) < 1e-6
                st.session_state['p4p1_correct'] = answer
                attempts = st.session_state['p4p1_attempts']

                if answer:
                    feedback = f"좋아요! 평균이 {current_avg:.2f}으로 잘 만들어주었어요!"
                else:
                    feedback = f"오답이에요. 지금의 평균은 {current_avg:.2f}입니다. 평균이 {target_avg}가 되게 만들어주세요. 평균을 수정하고 싶다면 '뒤로 가기' 버튼을 눌러주세요."
                    if attempts == 2:
                        feedback += f" 지금 자료의 총합은 {current_sum}입니다."
                st.session_state['p4p1_feedback'] = feedback
                st.session_state['p4p1_feedback_history'].append(feedback)
                st.session_state['p4p1_last_result'] = list(result)  # 2-1 제출값 저장!
                save_student_data(
                    st.session_state['student_name'],
                    4,
                    "2-1",
                    list(result),
                    answer,
                    attempts,
                    st.session_state['p4p1_feedback_history'],
                    [],
                    []
                )
                st.rerun()
            if st.session_state.get('p4p1_feedback'):
                if st.session_state.get('p4p1_correct', False):
                    st.success(st.session_state['p4p1_feedback'])
                else:
                    st.warning(st.session_state['p4p1_feedback'])
            if st.session_state.get('p4p1_correct', False):
                if st.button("다음", key="btn_next_p4p1"):
                    st.session_state['page4_problem_index'] = 2
                    st.rerun()
            if st.button("뒤로 가기", key="back_p4_1"):
                st.session_state['page'] = 'student_page_3_myavg_setup'
                st.session_state['p2_graph_hint'] = False  # 뒤로 가면 힌트 초기화
                st.session_state['p4_graph_hint'] = False  # 뒤로 가면 힌트 초기화
                st.rerun()

        # 과제 2-2
        elif current_problem_index == 2:
            st.subheader("과제 2-2")
            st.write(f"앞에서 만들었던 친구 다섯 명의 용돈(자료의 값)의 경우와 ★ 다른 용돈(자료의 값)★을 받는 경우를 생각해볼까요? \n각 친구들의 막대그래프를 위 아래로 조정하여 평균이 {target_avg}000원이 되도록 만들어보세요. 막대그래프의 단위는 천원입니다.")
            if st.button("제출", key="btn_submit_p4p2"):
                st.session_state['p4p2_attempts'] += 1
                current_avg = st.session_state.get('graph2_average', 0)
                prev_data = st.session_state.get('p4p1_last_result', None)
                result_list = list(result)
                is_same_as_prev = (prev_data == result_list)

                # 평균값 체크
                is_avg_correct = abs(current_avg - target_avg) < 1e-6
                # 2-1에서 제출한 자료값과 같으면 무조건 오답
                if is_same_as_prev:
                    feedback = "앞에서 제출한 자료 의값들과 같습니다. 다른 경우를 생각해보세요!"
                    correct = False
                elif is_avg_correct:
                    # 평균 근처에 밀집 체크 (모든 자료값이 목표평균 ±2 이내)
                    dense = all(abs(x - target_avg) <= 2 for x in result_list)
                    # 극단값 포함 체크 (하나라도 목표평균 ±3 이상 차이)
                    outlier = any(abs(x - target_avg) >= 3 for x in result_list)
                    if dense:
                        feedback = "잘 만들었어요! 만약 친구 한 명의 용돈이 너무 높거나 또는 낮게 받은 경우를 생각해볼까요?"
                        correct = True
                    elif outlier:
                        feedback = f"좋아요! 학생이 만든 것처럼 자료의 값이 너무 높거나 너무 낮아도 평균 {target_avg}을 가질 수 있어요."
                        correct = True
                    else:
                        # dense도 outlier도 아닌 경우(예외상황, 중간값 섞임)
                        feedback = f"평균 {target_avg}을 잘 맞췄어요! 여러 가지 방법이 있어요. 너무 높거나 낮은 자료의 값을 고려해볼 수도 있어요.."
                        correct = True
                else:
                    feedback = f"오답이에요. 지금의 평균은 {current_avg:.2f}입니다. 평균이 {target_avg}가 되게 만들어주세요."
                    correct = False

                st.session_state['p4p2_correct'] = correct
                st.session_state['p4p2_feedback'] = feedback
                st.session_state['p4p2_feedback_history'].append(feedback)
                save_student_data(
                    st.session_state['student_name'],
                    4,
                    "2-2",
                    result_list,
                    correct,
                    st.session_state['p4p2_attempts'],
                    st.session_state['p4p2_feedback_history'],
                    [],
                    []
                )
                st.rerun()
            if st.session_state.get('p4p2_feedback'):
                if st.session_state.get('p4p2_correct', False):
                    st.success(st.session_state['p4p2_feedback'])
                else:
                    st.warning(st.session_state['p4p2_feedback'])
            if st.session_state.get('p4p2_correct', False):
                if st.button("다음", key="btn_next_p4p2"):
                    st.session_state['page4_problem_index'] = 3
                    st.rerun()
            if st.button("뒤로 가기", key="back_p4_2"):
                st.session_state['page4_problem_index'] = 1
                st.session_state['p2_graph_hint'] = False  # 뒤로 가면 힌트 초기화
                st.session_state['p4_graph_hint'] = False  # 뒤로 가면 힌트 초기화
                st.rerun()

        elif current_problem_index == 3:
            st.subheader("과제 2-3")
            st.write(f"여러분들이 예측한 용돈 평균 {target_avg}000원을 만들기 위해 어떤 방법을 사용했나요?")
            is_input_disabled = st.session_state.get('p4p3_correct', False)
            student_answer = st.text_area("여기에 방법을 작성하세요:", height=150, key="p4p3_answer_input", value=st.session_state.get('p4p3_answer', ''), disabled=is_input_disabled)
            attempts = st.session_state.get('p4p3_attempts', 0)
            if st.session_state['p4p3_attempts'] >= 3:
                if st.button("힌트 보기", key="btn_hint_p4p3"):
                    st.session_state['p4_graph_hint'] = True
            if st.button("답변 제출", key="btn_submit_p4p3", disabled=is_input_disabled):
                st.session_state['p4p3_answer'] = student_answer
                st.session_state['p4p3_attempts'] += 1
                gpt_result, gpt_comment = evaluate_page4_problem3_with_gpt(
                    student_answer,
                    PAGE4_PROBLEM3_GOAL_CONCEPT,
                    PAGE4_PROBLEM3_SCAFFOLDING_PROMPT,
                )
                key_terms = ["평균", "그래프", "자료", "값", "합", "차이", "막대", "합계", "더하다", "빼다", "뺄셈"]
                is_correct = gpt_result or (any(term in student_answer for term in key_terms) and len(student_answer.strip()) >= 5)
                if is_correct:
                    st.session_state['p4p3_correct'] = True
                    st.session_state['p4p3_feedback'] = f"🎉 {gpt_comment} 정말 잘했어요!"
                else:
                    step_feedback = PAGE4_PROBLEM3_FEEDBACK_LOOP.get(
                        min(st.session_state['p4p3_attempts'], len(PAGE4_PROBLEM3_FEEDBACK_LOOP)), ""
                    )
                    st.session_state['p4p3_feedback'] = f"음... 다시 생각해볼까요? {step_feedback} {gpt_comment}"
                st.session_state['p4p3_feedback_history'].append(st.session_state['p4p3_feedback'])
                
                if st.session_state['p4p3_attempts'] >= 5:
                    if len(st.session_state['chat_log_page4_p3']) == 0:
                        st.session_state['chat_log_page4_p3'] = [{"role": "assistant", "content": "평균과 각각의 자료의 값이 어떤 관련이 있었는지 생각해보고, 궁금한 점을 질문해주세요!"}]
                
                # --- cumulative_popup_shown 정보 구성 시작 ---
                popups_shown_p4p3 = []
                if st.session_state.get('p4p3_attempts',0) >= 5:
                    popups_shown_p4p3.append("CUMULATIVE_FEEDBACK_5_P4P3") 
                elif st.session_state.get('p4p3_attempts',0) >= 4:
                    popups_shown_p4p3.append("CUMULATIVE_FEEDBACK_4_P4P3")
                if st.session_state.get('p4p3_attempts', 0) >= 5 and st.session_state.get('chat_log_page4_p3', []):
                    popups_shown_p4p3.append("ChatbotActive_P4P3")
                # --- cumulative_popup_shown 정보 구성 끝 ---

                # 여기가 유일하고 올바른 save_student_data 호출 지점이어야 합니다.
                save_student_data(
                    st.session_state['student_name'],
                    4,
                    "2-3",
                    student_answer,
                    is_correct,
                    st.session_state['p4p3_attempts'],
                    st.session_state['p4p3_feedback_history'],
                    popups_shown_p4p3, 
                    st.session_state.get('chat_log_page4_p3', [])
                )
                st.rerun() # 모든 상태 업데이트와 저장이 끝난 후 rerun
            if st.session_state.get('p4p3_feedback'):
                if st.session_state.get('p4p3_correct', False):
                    st.success(st.session_state['p4p3_feedback'])
                else:
                    st.warning(st.session_state['p4p3_feedback'])
            # 챗봇 (오답 5회 이상)
            if st.session_state.get('p4p3_attempts', 0) >= 5 and st.session_state.get('chat_log_page4_p3', []):
                for chat in st.session_state['chat_log_page4_p3']:
                    if chat["role"] == "system": continue
                    with st.chat_message(chat["role"]): st.markdown(chat["content"])
                chat_input = st.chat_input("질문 또는 생각을 입력하세요:")
                if chat_input:
                    st.session_state['chat_log_page4_p3'].append({"role": "user", "content": chat_input})
                    st.rerun()
                elif st.session_state['chat_log_page4_p3'] and st.session_state['chat_log_page4_p3'][-1]["role"] == "user":
                    response = client.chat.completions.create(model="gpt-4.1",messages=st.session_state['chat_log_page4_p3'])
                    st.session_state['chat_log_page4_p3'].append({"role": "assistant", "content": response.choices[0].message.content})
                    st.rerun()
                    
            if st.session_state.get('p4p3_correct', False):
                if st.button("다음", key="btn_next_p4p3"):
                    st.session_state['page4_problem_index'] = 4
                    st.rerun()
            elif st.session_state.get('p4p3_feedback'):
                st.info("정답을 맞춰야 다음 단계로 넘어갈 수 있습니다.")
            if st.button("뒤로 가기", key="back_p4_3"):
                st.session_state['page4_problem_index'] = 2
                st.session_state['p2_graph_hint'] = False  # 뒤로 가면 힌트 초기화
                st.session_state['p4_graph_hint'] = False  # 뒤로 가면 힌트 초기화
                st.rerun()
            st.session_state['skip'] = ('page4_problem_index', 4)

                
        elif current_problem_index == 4:
            st.subheader("과제 2-4")
            st.write("여러 가지 과제를 수행하면서 알게된 평균이 갖는 특징은 무엇이 있나요? 여러 가지를 적어도 좋습니다. 특히 평균이 자료를 대표하는 경우과 대표하지 않는 경우에 대해 생각해보세요. \n 또한, 평균의 함정이 무엇인지 발견한 친구 있나요? 발견했다면, 평균의 함정에 대해 자세히 설명해주세요.")
            is_input_disabled = st.session_state.get('p4p4_correct', False)
            student_answer = st.text_area("여기에 알게된 사실을 작성하세요:", height=200, key="p4p4_answer_input", value=st.session_state.get('p4p4_answer', ''), disabled=is_input_disabled)
            attempts = st.session_state.get('p4p4_attempts', 0)
            if st.button("답변 제출", key="btn_submit_p4p4", disabled=is_input_disabled):
                st.session_state['p4p4_answer'] = student_answer
                st.session_state['p4p4_attempts'] += 1
                _, gpt_comment = evaluate_page4_problem4_with_gpt(student_answer)
                is_correct = "평균" in student_answer 
                if is_correct:
                    st.session_state['p4p4_correct'] = True
                    st.session_state['p4p4_feedback'] = f"🎉 {gpt_comment} 정말 잘했어요!"
                else:
                    step_feedback = PAGE4_PROBLEM4_FEEDBACK_LOOP.get(min(st.session_state['p4p4_attempts'], len(PAGE4_PROBLEM4_FEEDBACK_LOOP)), "")
                    st.session_state['p4p4_feedback'] = f"음... 다시 생각해볼까요? {step_feedback} {gpt_comment}"
                st.session_state['p4p4_feedback_history'].append(st.session_state['p4p4_feedback'])
                
                if st.session_state['p4p4_attempts'] >= 3:
                    if len(st.session_state['chat_log_page4_p4']) == 0:
                        st.session_state['chat_log_page4_p4'] = [{"role": "assistant", "content": "평균의 특징이나 함정에 대해 궁금한 점이 있나요? 무엇이든 질문해보세요!"}]
                
                # --- cumulative_popup_shown 정보 구성 시작 ---
                popups_shown_p4p4 = []
                if st.session_state.get('p4p4_attempts',0) >= 3: 
                    popups_shown_p4p4.append("CUMULATIVE_FEEDBACK_5_4_P4P4") 
                elif st.session_state.get('p4p4_attempts',0) >= 2:
                    popups_shown_p4p4.append("CUMULATIVE_FEEDBACK_4_4_P4P4")
                if st.session_state.get('p4p4_attempts', 0) >= 3 and st.session_state.get('chat_log_page4_p4', []):
                     popups_shown_p4p4.append("ChatbotActive_P4P4")
                # --- cumulative_popup_shown 정보 구성 끝 ---

                # 여기가 유일하고 올바른 save_student_data 호출 지점이어야 합니다.
                save_student_data(
                    st.session_state['student_name'],
                    4,
                    "2-4",
                    student_answer,
                    is_correct,
                    st.session_state['p4p4_attempts'],
                    st.session_state['p4p4_feedback_history'],
                    popups_shown_p4p4, 
                    st.session_state.get('chat_log_page4_p4', [])
                )
                st.rerun() # 모든 상태 업데이트와 저장이 끝난 후 rerun
            if st.session_state.get('p4p4_feedback'):
                if st.session_state.get('p4p4_correct', False):
                    st.success(st.session_state['p4p4_feedback'])
                else:
                    st.warning(st.session_state['p4p4_feedback'])
            # 챗봇 (오답 5회 이상)
            if st.session_state.get('p4p4_attempts', 0) >= 3 and st.session_state.get('chat_log_page4_p4', []):
                for chat in st.session_state['chat_log_page4_p4']:
                    if chat["role"] == "system": continue
                    with st.chat_message(chat["role"]): st.markdown(chat["content"])
                chat_input = st.chat_input("질문 또는 생각을 입력하세요:")
                if chat_input:
                    st.session_state['chat_log_page4_p4'].append({"role": "user", "content": chat_input})
                    st.rerun()
                elif st.session_state['chat_log_page4_p4'] and st.session_state['chat_log_page4_p4'][-1]["role"] == "user":
                    response = client.chat.completions.create(model="gpt-4.1",messages=st.session_state['chat_log_page4_p4'])
                    st.session_state['chat_log_page4_p4'].append({"role": "assistant", "content": response.choices[0].message.content})
                    st.rerun()
            if st.session_state.get('p4p4_correct', False):
                if st.button("학습 완료", key="btn_next_p4p4"):
                    st.session_state['page'] = 'student_page_5_completion'
                    st.rerun()
            elif st.session_state.get('p4p4_feedback'):
                st.info("정답을 맞춰야 다음 단계로 넘어갈 수 있습니다.")
            if st.button("뒤로 가기", key="back_p4_4"):
                st.session_state['page4_problem_index'] = 3
                st.session_state['p2_graph_hint'] = False  # 뒤로 가면 힌트 초기화
                st.session_state['p4_graph_hint'] = False  # 뒤로 가면 힌트 초기화
                st.rerun()
            st.session_state['skip'] = ('page', 'student_page_5_completion')


# --- 학생 페이지 5 (학습완료) ---
def student_page_5_completion():
    st.header("학습 완료!")
    st.write(f"{st.session_state.get('student_name','학생')} 학생, 평균 학습 과제를 모두 완료했습니다! 수고했어요!")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("다른 평균 설정하여 다시 도전하기"):
            st.session_state['page'] = 'student_page_3_myavg_setup'
            st.session_state['page4_problem_index'] = 1
            st.session_state['p4_graph_hint'] = False  # 뒤로 가면 힌트 초기화
            st.session_state['p2_graph_hint'] = False  # 뒤로 가면 힌트 초기화
            # 기타 상태 초기화
            for k in ['p4p1_feedback', 'p4p1_feedback_history', 'p4p1_correct', 'p4p1_attempts',
                      'p4p2_feedback', 'p4p2_feedback_history', 'p4p2_correct', 'p4p2_attempts',
                      'p4p3_answer', 'p4p3_feedback', 'p4p3_feedback_history', 'p4p3_correct', 'p4p3_attempts',
                      'p4p4_answer', 'p4p4_feedback', 'p4p4_feedback_history', 'p4p4_correct', 'p4p4_attempts',
                      'chat_log_page4_p3', 'chat_log_page4_p4']:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
    with col2:
        if st.button("홈으로"):
            st.session_state['page'] = 'main'
            st.rerun()

# --- 교사용 페이지 (모든 데이터 표/엑셀) ---
def teacher_page():
    st.header("교사용 페이지")
    password = st.text_input("비밀번호를 입력하세요", type="password", key="teacher_pw_input_main")

    if password == TEACHER_PASSWORD:
        st.success("🔑 비밀번호 인증 성공!")
        
        try:
            if not os.path.exists(STUDENT_DATA_DIR):
                st.info(f"데이터 디렉토리 '{STUDENT_DATA_DIR}'가 아직 없습니다. 학생 활동이 시작되면 생성됩니다.")
                student_files = []
            else:
                student_files = sorted([f for f in os.listdir(STUDENT_DATA_DIR) if f.startswith("student_") and f.endswith(".json")], reverse=True) # 최근 파일이 위로
        except Exception as e:
            st.error(f"학생 데이터 파일 목록 로딩 오류: {e}")
            student_files = []

        if not student_files:
            st.info("아직 저장된 학생 데이터가 없습니다.")
        else:
            if 'selected_student_file_teacher' not in st.session_state: st.session_state.selected_student_file_teacher = None
            if 'delete_confirmation_active' not in st.session_state: st.session_state.delete_confirmation_active = False
            if 'current_file_to_delete' not in st.session_state: st.session_state.current_file_to_delete = None

            def on_student_select_teacher():
                st.session_state.selected_student_file_teacher = st.session_state.selectbox_student_files_teacher
                st.session_state.delete_confirmation_active = False # 학생 변경 시 삭제 확인 초기화
                st.session_state.current_file_to_delete = None

            selected_idx = student_files.index(st.session_state.selected_student_file_teacher) if st.session_state.selected_student_file_teacher in student_files else 0 if student_files else None

            st.selectbox("학생 선택:", student_files, index=selected_idx, 
                         placeholder="학생 기록을 보려면 선택하세요.", key="selectbox_student_files_teacher",
                         on_change=on_student_select_teacher)
            
            selected_student_file = st.session_state.selected_student_file_teacher

            if selected_student_file:
                filepath = os.path.join(STUDENT_DATA_DIR, selected_student_file)
                student_display_name = selected_student_file.replace('student_', '').replace('.json', '').replace('_', ' ')

                if not os.path.exists(filepath): # 파일 삭제 후 UI 업데이트 대응
                    st.warning(f"선택한 파일 '{selected_student_file}'을 찾을 수 없습니다. 다른 학생을 선택해주세요.")
                    st.session_state.selected_student_file_teacher = None
                    st.rerun()
                    return

                st.subheader(f"📊 {student_display_name} 학생의 학습 기록 요약")
                try:
                    with open(filepath, 'r', encoding='utf-8') as f: student_data_loaded = json.load(f)
                    
                    if not student_data_loaded:
                        st.info(f"'{student_display_name}' 학생의 기록이 비어있습니다.")
                    else:
                        # DataFrame 생성
                        summary_table_data = []
                        for entry_sum in student_data_loaded:
                            summary_table_data.append({
                                "시간": entry_sum.get("timestamp"), "페이지": entry_sum.get("page"), "문제": entry_sum.get("problem"),
                                "답변요약": str(entry_sum.get("student_answer"))[:30] + ('...' if len(str(entry_sum.get("student_answer", ""))) > 30 else ""),
                                "정오": "O" if entry_sum.get("is_correct") else "X", "시도수": entry_sum.get("attempt"),
                                "피드백수": len(entry_sum.get("feedback_history", [])),
                                "팝업": ", ".join(str(x).split('_')[-1].replace('P2P1','P2').replace('P4P3','P4.3').replace('P4P4','P4.4') for x in entry_sum.get("cumulative_popup_shown", [])),
                                "챗봇수": len([c for c in entry_sum.get("chatbot_interactions", []) if c.get("role") == "user"]), # 사용자 질문 수 기준
                            })
                        df_summary = pd.DataFrame(summary_table_data)
                        st.dataframe(df_summary, use_container_width=True, height=min(300, len(df_summary) * 35 + 38)) # 동적 높이
                        
                        csv_summary = df_summary.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(label="💾 요약 기록 다운로드 (CSV)", data=csv_summary,
                                          file_name=f"{student_display_name}_요약기록.csv", mime="text/csv",
                                          key=f"download_summary_{selected_student_file}")

                        # --- 학생 활동 상세 분석 ---
                        st.markdown("---")
                        st.subheader(f"🔬 {student_display_name} 학생 활동 상세 분석")
                        for i, entry_detail in enumerate(student_data_loaded):
                            exp_key_base = f"detail_entry_{selected_student_file}_{i}"
                            entry_summary_text = f"({entry_detail.get('timestamp')}) 페이지: {entry_detail.get('page')}, 문제: {entry_detail.get('problem')}, 시도: {entry_detail.get('attempt')}"
                            
                            with st.expander(f"기록 #{i+1}: {entry_summary_text}", expanded=False):
                                st.markdown(f"**학생 제출 내용:**")
                                student_ans = entry_detail.get("student_answer", "N/A")
                                if isinstance(student_ans, (list, dict)): st.json(student_ans)
                                else: st.markdown(f"> ```\n{student_ans}\n```" if student_ans else "> 답변 없음")

                                fb_history = entry_detail.get("feedback_history", [])
                                if fb_history:
                                    with st.expander("💬 피드백 전체 내용 보기", expanded=False, key=f"{exp_key_base}_fb_exp"):
                                        for fb_idx, fb_item in enumerate(fb_history):
                                            st.text_area(f"피드백 #{fb_idx+1}", value=fb_item, height=max(80, int(len(fb_item)/2.5)), disabled=True, key=f"{exp_key_base}_fb_item_{fb_idx}")
                                else: st.markdown("**피드백 기록 없음**")

                                chat_interactions = entry_detail.get("chatbot_interactions", [])
                                if chat_interactions:
                                    # 실제 챗봇 대화가 있는 경우 (system 프롬프트 제외하고 user, assistant만)
                                    actual_chats = [c for c in chat_interactions if c.get("role") in ["user", "assistant"]]
                                    if actual_chats:
                                        with st.expander("🤖 챗봇 대화 전체 내용 보기", expanded=False, key=f"{exp_key_base}_chat_exp"):
                                            for chat_idx, chat_item in enumerate(actual_chats):
                                                role, content = chat_item.get("role"), chat_item.get("content")
                                                if role and content:
                                                    avatar_icon = "🧑‍🎓" if role == "user" else "🤖"
                                                    with st.chat_message(role, avatar=avatar_icon, key=f"{exp_key_base}_chat_item_{chat_idx}"):
                                                        st.markdown(content)
                                    else: st.markdown("**챗봇과의 실제 대화 기록 없음**") # System 프롬프트만 있는 경우
                                else: st.markdown("**챗봇 대화 기록 없음**")
                                
                                cum_popups = entry_detail.get("cumulative_popup_shown", [])
                                if cum_popups: st.markdown(f"**표시된 누적 팝업:** `{', '.join(cum_popups)}`")
                                st.markdown("---")
                        # --- 상세 분석 끝 ---

                        # --- 학생 기록 파일 삭제 기능 ---
                        st.markdown("---")
                        st.subheader(f"🔴 '{student_display_name}' 학생 기록 파일 관리")
                        if st.session_state.delete_confirmation_active and st.session_state.current_file_to_delete == selected_student_file:
                            st.error(f"정말로 '{student_display_name}' 학생의 모든 기록 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다!")
                            col_del_confirm, col_del_cancel = st.columns(2)
                            with col_del_confirm:
                                if st.button("✔️ 예, 영구 삭제합니다", key=f"btn_del_confirm_{selected_student_file}", type="primary", use_container_width=True):
                                    try:
                                        os.remove(filepath); st.success(f"'{student_display_name}' 학생 기록 파일 삭제 완료.")
                                        st.session_state.delete_confirmation_active = False; st.session_state.current_file_to_delete = None
                                        st.session_state.selected_student_file_teacher = None # 선택 해제하여 목록 새로고침 유도
                                        st.rerun()
                                    except Exception as e_del: st.error(f"파일 삭제 오류: {e_del}"); st.rerun()
                            with col_del_cancel:
                                if st.button("❌ 아니요, 취소합니다", key=f"btn_del_cancel_{selected_student_file}", use_container_width=True):
                                    st.session_state.delete_confirmation_active = False; st.session_state.current_file_to_delete = None; st.rerun()
                        else:
                            if st.button(f"🗑️ '{student_display_name}' 학생 기록 파일 삭제하기", key=f"btn_del_req_{selected_student_file}", use_container_width=True, type="destructive" if hasattr(st, 'button') and 'type' in st.button.__kwdefaults__ and 'destructive' in st.button.__kwdefaults__['type'] else "secondary"):
                                st.session_state.delete_confirmation_active = True; st.session_state.current_file_to_delete = selected_student_file; st.rerun()
                        # --- 파일 삭제 끝 ---

                except json.JSONDecodeError: st.error(f"'{selected_student_file}' 파일이 손상되어 읽을 수 없습니다 (JSON 형식 오류).")
                except Exception as e_load: st.error(f"'{student_display_name}' 학생 데이터 처리 중 오류: {e_load}")
            # else: st.info("학생을 선택하면 기록을 볼 수 있습니다.") # placeholder로 대체됨

    elif password and password != TEACHER_PASSWORD:
        st.error("비밀번호가 틀렸습니다.")

    if st.button("↩️ 초기 화면으로", key="back_teacher_to_main_page"):
        st.session_state['page'] = 'main'
        # 교사 페이지 관련 상태 초기화
        if 'teacher_pw_input_main' in st.session_state: del st.session_state['teacher_pw_input_main']
        if 'selected_student_file_teacher' in st.session_state: del st.session_state['selected_student_file_teacher']
        if 'delete_confirmation_active' in st.session_state: del st.session_state['delete_confirmation_active']
        if 'current_file_to_delete' in st.session_state: del st.session_state.current_file_to_delete
        st.rerun()

# --- 메인 페이지 ---
def main_page():
    st.title("📊 평균에 대해 자세히 알아볼까요?")
    st.session_state['p2_graph_hint'] = False  # 뒤로 가면 힌트 초기화
    st.session_state['p4_graph_hint'] = False  # 뒤로 가면 힌트 초기화
    st.write("학생 또는 교사로 접속해주세세요.")
    user_type = st.radio("접속 유형 선택:", ("학생용", "교사용"), key="user_type_radio", horizontal=True)
    if st.button("선택 완료", key="btn_select_user_type"):
        if user_type == "학생용":
            st.session_state['page'] = 'student_page_1'
        elif user_type == "교사용":
            st.session_state['page'] = 'teacher_page'
        st.rerun()

# --- 페이지 라우팅 ---
pages = {
    'main': main_page,
    'student_page_1': student_page_1,
    'student_page_2_graph60': student_page_2_graph60,
    'student_page_3_myavg_setup': student_page_3_myavg_setup,
    'student_page_4_myavg_tasks': student_page_4_myavg_tasks,
    'student_page_5_completion': student_page_5_completion,
    'teacher_page': teacher_page,
}

st.session_state['skip'] = None

update_page_state_on_entry()
render_page = pages.get(st.session_state.get('page','main'), main_page)
render_page()
