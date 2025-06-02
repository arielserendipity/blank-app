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
    2: "각각의 그래프의 자료값이 얼마인지 알아볼까요?",
    3: "그래프의 높낮이를 움직이면서 자료의 총합은 어떻게 변화하나요? '힌트 보기'를 사용해서 그래프가 어떻게 변화하는지 관찰하세요.",
}
PAGE4_PROBLEM3_GOAL_CONCEPT = "자료값과 평균 사이의 차이의 총합이 항상 0이 되도록 자료값을 조절하면 목표 평균을 달성할 수 있다는 점을 인지하는 것"
PAGE4_PROBLEM3_SCAFFOLDING_PROMPT = """당신은 학생이 평균 개념을 깊이 이해하도록 돕는 AI 튜터입니다. 학생은 자신이 설정한 목표 평균을 달성하기 위해 그래프 자료값을 조절하는 활동을 했습니다. 이 과정에서 자신이 사용한 전략에 대해 설명하라는 질문에 답변했습니다. 학생의 답변이 목표 개념인 "{goal_concept}"과 얼마나 관련 있는지 평가해주세요. 목표 개념을 직접적으로 언급하거나 답을 알려주지 말고, 학생의 현재 이해 수준에서 다음 단계로 나아갈 수 있도록 유도하는 질문이나 발문을 생성해주세요. 학생의 답변이 목표 개념과 거리가 멀다면 기본적인 개념(자료의 총합과 개수)으로 돌아가는 발문을, 조금이라도 관련 있다면 편차의 합 등 심화 개념으로 나아가도록 발문을 시도해주세요. 응답은 'FEEDBACK:' 접두사로 시작해주세요."""
CUMULATIVE_FEEDBACK_4 = "많은 어려움을 겪고 있는 것 같네요. 노란색과 초록색이 무엇을 의미하는 지 생각해보세요."
CUMULATIVE_FEEDBACK_5 = "추가 힌트를 드릴게요! 노란색의 넓이와 초록색의 넓이를 비교해보세요!"

# 아래는 2-3, 2-4 루프/팝업 피드백 추가
PAGE4_PROBLEM3_FEEDBACK_LOOP = {
    1: "목표 평균과 각 자료값의 차이를 생각해보면 좋겠어요.",
    2: "목표 평균과 각 자료값의 차이의 합이 0이 되는 순간을 찾으셨나요?",
    3: "막대를 조정하면서 목표평균과 각 자료값의 차이 합을 계속 0으로 맞추는 경험이 있었나요?",
}
PAGE4_PROBLEM4_FEEDBACK_LOOP = {
    1: "과제를 해결하면서 알게 된 사실을 생각해보세요!?",
    2: "평균은 자료를 대표하는 값이에요. 평균이 항상 자료 중간에 있나요?",
    3: "평균의 함정은 언제 발생할까요? 극단값이나 이상값이 있을 때를 생각해보세요.",
}
CUMULATIVE_FEEDBACK_4_4 = "평균의 성질에 대해 다시 한 번 천천히 생각해보세요."
CUMULATIVE_FEEDBACK_5_4 = "평균의 함정에 대해 추가로 생각해보고, 자료 전체와 평균의 관계를 떠올려보세요!"

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
            """,
    ):
        return st.button("☎")

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
    system_message = f"""당신은 학생이 평균 개념 학습을 돕는 AI 튜터입니다. 학생은 자신이 설정한 목표 평균을 달성하기 위해 그래프를 조작하였고, 그에 따른 학생의 전략을 물어보는 과제입니다.  그래프 조작 후 "{PAGE4_PROBLEM3_GOAL_CONCEPT}" 개념과 관련하여 알게된 사실을 설명했습니다. 학생의 답변이 목표 개념을 달성했는지 평가해주세요. 구체적으로 목표가 무엇인지 언급하면 안됩니다. 학생이 자연스럽게 하나의 평균에도 다양한 자료 집합을 가질 수 있음을 알게해주도록 촉진해주는 발문을 해주세요. 
평가 결과는 반드시 'CORRECT:' 또는 'INCORRECT:' 접두사로 시작해주세요. 그 뒤에 학생의 답변에 대한 짧고 격려하는 피드백을 추가해주세요. 피드백은 반드시 공백 포함 160자 이내로만 작성해주세요. 초등학생이 교육대상이므로 어렵거나 추상적인 표현 대신, 초등학생도 이해하기 쉬운 다정한 언어로 설명해주세요. 예를 들어, '평균선을 기준으로 높은 부분과 낮은 부분이 같아.', '자룟값들을 다 더하면 목표평균*5야' 등의 응답도 학습 목표를 달성했다고 봅니다. """
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
    system_message = """당신은 학생이 평균 개념을 깊이 이해하도록 돕는 AI 튜터입니다. 학생은 평균의 성질이나 '평균의 함정'에 대해 자신이 알게된 사실을 설명했습니다. 학생의 답변에 대해 격려하고, 답변 내용과 관련된 평균의 추가적인 성질이나 흥미로운 점에 대해 짧게 언급하며 탐구를 유도해주세요. 정답/오답 판단보다는 학생의 생각을 확장하는 데 집중해주세요. 응답은 'FEEDBACK:' 접두사로 시작해주세요."""
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
    st.write("이름을 입력하고 시작하세요!")
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

# --- 학생 페이지 2 (목표 평균 60, 과제 1, 챗봇, 피드백, 저장) ---
def student_page_2_graph60():
    update_page_state_on_entry()
    st.header("목표 평균 60 도전! (과제 1)")
    st.write(f"{st.session_state.get('student_name','학생')} 학생, 아래 막대그래프는 항상 평균이 60점이 되도록 하는 마법에 걸렸습니다.")
    st.info("쪽지시험 1회부터 5회까지의 점수, 즉 막대를 위아래로 드래그 조정하여 평균 60점이 되게끔하는 마법의 비밀을 풀어봅시다.")
    graph_col, task_col, popup_col = setup_columns_and_display_popups('student_page_2_graph60')
    with graph_col:
        if st.session_state.get('page2_show_cumulative_popup5', False):
            if len(st.session_state['chat_log_page2']) == 0:
                st.session_state['chat_log_page2'] = [
                    {"role": "assistant", "content": "그래프를 조정하는 데 어려움을 겪고 있는 것 같아요. 그래프의 높낮이를 조절하면서 어떤 변화가 있는지 살펴보고, 도움이 필요한 부분이 있다면 질문해주세요."},
                ]
        if 'graph_prev_values' not in st.session_state:
            st.session_state['graph_prev_values'] = (0, 0, 0, 0, 0)
        result = tuple(draggable_barchart("graph_page_2", labels=["1회", "2회", "3회", "4회", "5회"], hint=st.session_state.get('p2_graph_hint', False)))
        if result != st.session_state['graph_prev_values']:
            st.session_state['graph_prev_values'] = result
    with task_col:
        st.subheader("과제 1")
        st.write("평균이 60으로 고정되도록 그래프를 움직이면서 **알게된 사실**은 무엇인가요?")
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
        st.rerun()

# --- 학생 페이지 3 (나만의 평균 설정) ---
def student_page_3_myavg_setup():
    update_page_state_on_entry()
    st.header("나만의 평균 설정")
    st.write(f"{st.session_state.get('student_name','학생')} 학생, 원하는 목표 평균(1~10점)을 입력하세요!")
    main_col, _, popup_col = setup_columns_and_display_popups('student_page_3_myavg_setup')
    with main_col:
        avg_input = st.number_input("목표 평균 (1~10)", min_value=1, max_value=10, value=st.session_state.get('target_average_page3', 5), key="page3_avg_input")
        if st.button("평균 설정", key="btn_set_avg_p3"):
            st.session_state['target_average_page3'] = avg_input
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
        st.rerun()

# --- 학생 페이지 4 (나만의 평균 과제) ---
def student_page_4_myavg_tasks():
    update_page_state_on_entry()
    target_avg = st.session_state.get('target_average_page3', 5)
    current_problem_index = st.session_state.get('page4_problem_index', 1)
    st.header(f"나만의 평균 과제 (목표 평균: {target_avg}점)")
    st.write(f"{st.session_state.get('student_name', '학생')} 학생, 설정한 목표 평균 **{target_avg}**점을 달성하기 위한 과제들을 해결해봅시다.")
    graph_col, task_col, popup_col = setup_columns_and_display_popups('student_page_4_myavg_tasks')
    with graph_col:
        result = tuple(draggable_barchart2("graph_page_4", labels=["1회", "2회", "3회", "4회", "5회"], hint=st.session_state.get('p4_graph_hint', False), target_avg=target_avg))
        st.session_state['graph2_average'] = sum(result) / len(result)
    with task_col:
        # 과제 2-1
        if current_problem_index == 1:
            st.subheader("과제 2-1")
            st.write(f"목표 평균 {target_avg}점을 달성하기 위해 그래프 자료값을 변경해볼까요? 위에 표시된 그래프의 막대들을 조절해서 평균을 **{target_avg}**점으로 만들어보세요.")
            if st.button("제출", key="btn_submit_p4p1"):
                st.session_state['p4p1_attempts'] += 1
                current_avg = st.session_state.get('graph2_average', 0)
                current_sum = sum(result)
                answer = abs(current_avg - target_avg) < 1e-6
                st.session_state['p4p1_correct'] = answer
                attempts = st.session_state['p4p1_attempts']

                if answer:
                    feedback = f"좋아요! 평균이 {current_avg:.2f}로 잘 만들어주었어요!"
                else:
                    feedback = f"오답이에요. 지금의 평균은 {current_avg:.2f}입니다. 평균이 {target_avg}가 되게 만들어주세요. 목표 평균을 바꾸고 싶다면 ‘뒤로 가기‘ 버튼을 눌러주세요."
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
                st.rerun()

        # 과제 2-2
        elif current_problem_index == 2:
            st.subheader("과제 2-2")
            st.write(f"앞에서 제출한 자료값과 **다른 자료값들**로 이루어진 그래프를 만들어 평균 {target_avg}점을 달성해볼까요?")
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
                    feedback = "앞에서 제출한 자료값들과 같습니다. 다른 경우를 생각해보세요!"
                    correct = False
                elif is_avg_correct:
                    # 평균 근처에 밀집 체크 (모든 자료값이 목표평균 ±2 이내)
                    dense = all(abs(x - target_avg) <= 2 for x in result_list)
                    # 극단값 포함 체크 (하나라도 목표평균 ±3 이상 차이)
                    outlier = any(abs(x - target_avg) >= 3 for x in result_list)
                    if dense:
                        feedback = "잘 만들었어요! 만약 쪽지시험 중 한 번 점수를 너무 높거나 또는 낮게 받은 경우를 생각해볼까요?"
                        correct = True
                    elif outlier:
                        feedback = f"좋아요! 학생이 만든 것처럼 자료값이 너무 높거나 너무 낮아도 평균 {target_avg}을 가질 수 있어요."
                        correct = True
                    else:
                        # dense도 outlier도 아닌 경우(예외상황, 중간값 섞임)
                        feedback = f"평균 {target_avg}을 잘 맞췄어요! 여러 가지 방법이 있어요. 극단값을 더 넣거나, 밀집시켜보는 것도 연습해보세요."
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
                st.rerun()

        elif current_problem_index == 3:
            st.subheader("과제 2-3")
            st.write(f"목표 평균 {target_avg}점을 달성하기 위한 여러분만의 전략은 무엇이었나요?")
            is_input_disabled = st.session_state.get('p4p3_correct', False)
            student_answer = st.text_area("여기에 전략을 작성하세요:", height=150, key="p4p3_answer_input", value=st.session_state.get('p4p3_answer', ''), disabled=is_input_disabled)
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
                # 키워드 목록
                key_terms = ["평균", "그래프", "자료", "값", "합", "차이", "막대", "합계", "더하다", "빼다", "뺄셈"]
                # GPT가 맞다고 한 경우 or 키워드가 포함된 경우
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
                # 챗봇 연동(5회 이상 오답시)
                if st.session_state['p4p3_attempts'] >= 5:
                    if len(st.session_state['chat_log_page4_p3']) == 0:
                        st.session_state['chat_log_page4_p3'] = [{"role": "assistant", "content": "평균과 자룟값의 관계에 대해 무엇이 궁금한가요? 질문을 입력해보세요!"}]
                save_student_data(st.session_state['student_name'], 4, "2-3", student_answer, is_correct, st.session_state['p4p3_attempts'], st.session_state['p4p3_feedback_history'], [], st.session_state.get('chat_log_page4_p3', []))
                st.rerun()
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
                st.rerun()
            st.session_state['skip'] = ('page4_problem_index', 4)

                
        elif current_problem_index == 4:
            st.subheader("과제 2-4")
            st.write("여기에서 알게된 평균의 성질은 무엇이 있나요? 여러 가지를 적어도 좋습니다.\n혹시, 평균의 함정이 무엇인지 발견한 친구 있나요? 발견했다면, 평균의 함정에 대해 자세히 설명해주세요.")
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
                # 챗봇 연동(5회 이상 오답시)
                if st.session_state['p4p4_attempts'] >= 3:
                    if len(st.session_state['chat_log_page4_p4']) == 0:
                        st.session_state['chat_log_page4_p4'] = [{"role": "assistant", "content": "평균의 성질, 함정에 대해 궁금한 점이 있나요? 무엇이든 질문해보세요!"}]
                save_student_data(st.session_state['student_name'], 4, "2-4", student_answer, is_correct, st.session_state['p4p4_attempts'], st.session_state['p4p4_feedback_history'], [], st.session_state.get('chat_log_page4_p4', []))
                st.rerun()
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
                st.rerun()
            st.session_state['skip'] = ('page', 'student_page_5_completion')


# --- 학생 페이지 5 (학습완료) ---
def student_page_5_completion():
    st.header("학습 완료!")
    st.write(f"{st.session_state.get('student_name','학생')} 학생, 평균 학습 과제를 모두 완료했습니다! 수고했어요!")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("다른 평균값 설정하여 다시 시도하기"):
            st.session_state['page'] = 'student_page_3_myavg_setup'
            st.session_state['page4_problem_index'] = 1
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
    password = st.text_input("비밀번호를 입력하세요", type="password", key="teacher_pw")
    if password == TEACHER_PASSWORD:
        st.success("접속 성공!")
        try: student_files = [f for f in os.listdir(STUDENT_DATA_DIR) if f.startswith("student_") and f.endswith(".json")]
        except: st.error("데이터 폴더 오류!"); student_files = []
        if not student_files: st.info("아직 저장된 학생 데이터가 없습니다.")
        else:
            selected_student_file = st.selectbox("학생 선택:", student_files)
            if selected_student_file:
                try:
                    filepath = os.path.join(STUDENT_DATA_DIR, selected_student_file)
                    with open(filepath, 'r', encoding='utf-8') as f: student_data = json.load(f)
                    student_display_name = selected_student_file.replace('student_', '').replace('.json', '').replace('_', ' ')
                    table_data = []
                    for d in student_data:
                        table_data.append({
                            "시간": d.get("timestamp"),
                            "페이지": d.get("page"),
                            "문제": d.get("problem"),
                            "답변": d.get("student_answer"),
                            "정오": "O" if d.get("is_correct") else "X",
                            "시도수": d.get("attempt"),
                            "단순 오답 피드백 수": len(d.get("feedback_history", [])),
                            "팝업 피드백 단계": ", ".join(str(x) for x in d.get("cumulative_popup_shown", [])),
                            "챗봇 상호작용 수": len(d.get("chatbot_interactions", [])),
                            "최종 피드백": d.get("feedback_history", [])[-1] if d.get("feedback_history") else "",
                        })
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("엑셀(CSV)로 다운로드", csv, file_name=f"{student_display_name}_feedbacks.csv", mime="text/csv")
                    st.write("상세 기록(JSON):")
                    st.json(student_data)
                except Exception as e: st.error(f"데이터 로딩 중 오류 발생: {e}")
    elif password: st.error("비밀번호가 틀렸습니다.")
    if st.button("뒤로 가기", key="back_teacher"):
        st.session_state['page'] = 'main'
        st.rerun()

# --- 메인 페이지 ---
def main_page():
    st.title("📊 평균 학습 웹 앱")
    st.write("학생 또는 교사로 접속하여 평균 개념을 학습하거나 학습 현황을 확인해보세요.")
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
update_page_state_on_entry()
render_page = pages.get(st.session_state.get('page','main'), main_page)
render_page()
