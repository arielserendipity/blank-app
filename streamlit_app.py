# streamlit_app.py 파일의 전체 내용입니다.

import streamlit as st
from draggable_barchart import draggable_barchart

# --- 페이지 설정 (가장 먼저 호출) ---
st.set_page_config(layout="wide") # 화면 너비를 최대한 사용하도록 설정


import streamlit.components.v1 as components
from streamlit_option_menu import option_menu
import json
import time
from datetime import datetime
import os
import math # 평균 계산 및 통계 값 사용을 위해 math 또는 statistics 모듈 필요
# import statistics # statistics 모듈도 유용할 수 있습니다.

from openai import OpenAI

# OpenAI API 키 설정 및 클라이언트 초기화
# secrets.toml 사용 방식 (권장)
try:
    api_key = st.secrets["openai_api_key"]
    if not api_key:
         st.error("OpenAI API 키가 .streamlit/secrets.toml 파일에 설정되지 않았습니다.")
         st.stop() # 앱 실행 중지
    client = OpenAI(api_key=api_key)
except FileNotFoundError:
    st.error("오류: .streamlit/secrets.toml 파일을 찾을 수 없습니다. API 키를 설정해주세요.")
    st.stop() # 앱 실행 중지
except KeyError:
    st.error("오류: .streamlit/secrets.toml 파일에 'openai_api_key' 키가 없습니다. 'openai_api_key = \"YOUR_KEY\"' 형식으로 설정해주세요.")
    st.stop() # 앱 실행 중지
except Exception as e:
    st.error(f"OpenAI 클라이언트 초기화 중 오류 발생: {e}")
    st.stop() # 앱 실행 중지


# --- 상수 정의 ---
TEACHER_PASSWORD = "2025"
STUDENT_DATA_DIR = "student_data"
INACTIVITY_THRESHOLD_SECONDS = 60 # 비활동 감지 시간 (1분)

# 페이지 2 (목표 평균 60) 과제 1 관련 상수
PAGE2_PROBLEM1_GOAL_CONCEPT = "평균선을 기준으로 초과/미만의 범위(총합)가 같음을 인지하는 것"
PAGE2_PROBLEM1_FEEDBACK_LOOP = { # 페이지 2 오답 시 순차적 피드백
    1: "평균은 모든 자룟값을 모두 더하고 자료의 개수로 나눈 것이에요!",
    2: "각각의 그래프의 자료값이 얼마인지 알아볼까요?",
    3: "그래프의 높낮이를 움직이면서 자료의 총합은 어떻게 변화하나요?",
}

# 페이지 4 (나만의 평균 과제) 관련 상수
PAGE4_PROBLEM3_GOAL_CONCEPT = "자료값과 평균 사이의 차이(편차)의 총합이 항상 0이 되도록 자료값을 조절하면 목표 평균을 달성할 수 있다는 점을 인지하는 것"
PAGE4_PROBLEM3_SCAFFOLDING_PROMPT = """당신은 학생이 평균 개념을 깊이 이해하도록 돕는 AI 튜터입니다. 학생은 자신이 설정한 목표 평균을 달성하기 위해 그래프 자료값을 조절하는 활동을 했습니다. 이 과정에서 자신이 사용한 전략에 대해 설명하라는 질문에 답변했습니다. 학생의 답변이 목표 개념인 "{goal_concept}"과 얼마나 관련 있는지 평가해주세요. 목표 개념을 직접적으로 언급하거나 답을 알려주지 말고, 학생의 현재 이해 수준에서 다음 단계로 나아갈 수 있도록 유도하는 질문이나 발문을 생성해주세요. 학생의 답변이 목표 개념과 거리가 멀다면 기본적인 개념(자료의 총합과 개수)으로 돌아가는 발문을, 조금이라도 관련 있다면 편차의 합 등 심화 개념으로 나아가도록 발문을 시도해주세요. 응답은 'FEEDBACK:' 접두사로 시작해주세요."""

# 누적 오답 횟수 팝업 메시지
CUMULATIVE_FEEDBACK_5 = "많은 어려움을 겪고 있는 것 같네요. 노란색과 초록색이 무엇을 의미하는 지 생각해보세요."
CUMULATIVE_FEEDBACK_7 = "추가 힌트를 드릴게요! 노란색의 넓이와 초록색의 넓이를 비교해보세요!"


# --- 폴더 생성 ---
if not os.path.exists(STUDENT_DATA_DIR):
    os.makedirs(STUDENT_DATA_DIR)

# --- 함수 정의 --- (save_student_data 는 현재 호출되지 않으나 남겨둠)
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

# GPT를 사용하여 학생 응답 평가 (페이지 2 과제 1)
def evaluate_page2_problem1_with_gpt(student_answer, goal_concept):
    system_message = f"""당신은 학생이 평균 개념 학습을 돕는 AI 튜터입니다. 학생은 그래프 조작 후 "{goal_concept}" 개념과 관련하여 발견한 내용을 설명했습니다. 학생의 답변이 목표 개념을 인지하고 있는지 평가해주세요. '균형', '상쇄', '평균보다 높은/낮은 부분의 합', '총합이 일정' 등 관련 개념 포함 여부를 확인하세요.
평가 결과는 반드시 'CORRECT:' 또는 'INCORRECT:' 접두사로 시작해주세요. 그 뒤에 학생의 답변에 대한 짧고 격려하는 피드백을 추가해주세요.
예시 1) 학생 답변: "높은 곳을 낮추면 낮은 곳을 높여야 평균이 안 변해요" -> CORRECT: 맞아요! 변화량이 서로 상쇄된다는 것을 잘 파악했네요!
예시 2) 학생 답변: "막대 색깔이 바뀌어요" -> INCORRECT: 막대 색깔 변화도 관찰했군요. 그래프의 높이 변화에 좀 더 집중해볼까요?
주의: 정답이나 오답의 정의, 순차적인 힌트는 여기서 제공하지 마세요. 평가와 관련된 짧은 피드백만 제공해주세요.
"""
    user_message = f"""학생의 답변: {student_answer}"""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # 적절한 모델 사용 (gpt-4o-mini, gpt-4o 등도 가능)
            messages=messages,
            max_tokens=100,
            temperature=0.5,
        )
        gpt_text = response.choices[0].message.content.strip()
        if gpt_text.lower().startswith("correct:"):
            is_correct = True
            feedback_text = gpt_text[len("correct:"):].strip()
        elif gpt_text.lower().startswith("incorrect:"):
            is_correct = False
            feedback_text = gpt_text[len("incorrect:"):].strip()
        else:
            is_correct = False
            feedback_text = "답변을 이해하기 어렵습니다. 다시 설명해주시겠어요?" # fallback

        return is_correct, feedback_text

    except Exception as e:
        st.error(f"GPT API 호출 중 오류 발생: {e}")
        return False, "죄송합니다. 현재 피드백을 제공할 수 없습니다."


# GPT를 사용하여 학생 응답 평가 (페이지 4 과제 3 - 전략)
def evaluate_page4_problem3_with_gpt(student_answer, goal_concept, scaffolding_prompt):
     system_message = scaffolding_prompt.format(goal_concept=goal_concept)
     user_message = f"""학생의 답변: {student_answer}"""

     messages = [
         {"role": "system", "content": system_message},
         {"role": "user", "content": user_message}
     ]

     try:
         response = client.chat.completions.create(
             model="gpt-3.5-turbo", # 또는 gpt-4o-mini 등으로 변경
             messages=messages,
             max_tokens=200,
             temperature=0.7,
         )
         gpt_text = response.choices[0].message.content.strip()

         if gpt_text.lower().startswith("feedback:"):
              feedback_text = gpt_text[len("feedback:"):].strip()
         else:
              feedback_text = "답변에 대해 흥미로운 생각이네요. 평균에 대해 더 탐구해볼까요?" # fallback

         is_correct = False # 이 문제는 제출 시 바로 정답으로 처리하지 않음.

         return is_correct, feedback_text

     except Exception as e:
         st.error(f"GPT API 호출 중 오류 발생: {e}")
         return False, "죄송합니다. 현재 피드백을 제공할 수 없습니다."


# GPT를 사용하여 학생 응답 평가 (페이지 4 과제 4 - 성질/함정)
def evaluate_page4_problem4_with_gpt(student_answer):
    system_message = """당신은 학생이 평균 개념을 깊이 이해하도록 돕는 AI 튜터입니다. 학생은 평균의 성질이나 '평균의 함정'에 대해 자신이 발견한 것을 설명했습니다. 학생의 답변에 대해 격려하고, 답변 내용과 관련된 평균의 추가적인 성질이나 흥미로운 점에 대해 짧게 언급하며 탐구를 유도해주세요. 정답/오답 판단보다는 학생의 생각을 확장하는 데 집중해주세요.
예시) 학생 답변: "가운데 값이 아니어도 평균이 될 수 있어요" -> 훌륭한 발견이에요! 자료값 중에 평균과 같은 값이 없을 수도 있다는 것을 파악했네요. 혹시 극단적인 값이 평균에 어떤 영향을 주는지도 생각해본 적 있나요?
응답은 'FEEDBACK:' 접두사로 시작해주세요.
"""
    user_message = f"""학생의 답변: {student_answer}"""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # 또는 gpt-4o-mini 등으로 변경
            messages=messages,
            max_tokens=200,
            temperature=0.8,
        )
        gpt_text = response.choices[0].message.content.strip()

        if gpt_text.lower().startswith("feedback:"):
             feedback_text = gpt_text[len("feedback:"):].strip()
        else:
             feedback_text = "평균에 대해 좋은 생각을 공유해주었어요!" # fallback

        is_correct = True # 이 문제는 제출만 하면 완료로 간주

        return is_correct, feedback_text

    except Exception as e:
        st.error(f"GPT API 호출 중 오류 발생: {e}")
        # 오류 발생 시에도 일단 진행은 시키도록 True 반환
        return True, "죄송합니다. 현재 피드백을 제공할 수 없습니다."


# --- 페이지 상태 초기화 ---
# 세션 상태는 앱이 처음 로드될 때만 이 값들로 초기화됩니다.
# 페이지 이동 시 특정 상태 초기화는 update_page_state_on_entry 함수에서 관리합니다.
default_states = {
    'page': 'main',
    'prev_page': None, # 이전 페이지 추적용
    'student_name': '',
    'target_average_page3': 5, # 페이지 3에서 설정할 목표 평균 (기본값 5)
    'show_graph_page_3': False, # 페이지 3에서 평균 설정 완료 여부

    # 페이지 2 (목표 평균 60) 과제 1 상태
    'page2_problem_index': 1, # 페이지 2는 문제가 1개
    'p2p1_answer': '',
    'p2p1_feedback': None,
    'p2p1_correct': False,
    'p2p1_attempts': 0,

    # 페이지 4 (나만의 평균 과제) 상태
    'page4_problem_index': 1, # 현재 진행 중인 페이지 4 문제 번호 (1부터 시작)
    # 'p4p1_values': None, # 그래프 값을 받지 못하므로 더 이상 필요 없음 (또는 항상 None)
    'p4p1_correct': False,
    'p4p1_attempts': 0,
    'p4p1_feedback': None,

    # 'p4p2_values': None, # 그래프 값을 받지 못하므로 더 이상 필요 없음 (또는 항상 None)
    'p4p2_correct': False,
    'p4p2_attempts': 0,
    'p4p2_feedback': None,

    'p4p3_answer': '',
    'p4p3_feedback': None,
    'p4p3_correct': False, # GPT 피드백 로직에 따라 항상 False로 유지될 수도 있음
    'p4p3_attempts': 0,

    'p4p4_answer': '',
    'p4p4_feedback': None,
    'p4p4_correct': False, # 문제 특성상 제출 즉시 True로 간주
    'p4p4_attempts': 0,

    # 누적 오답 횟수 팝업 상태 (페이지 2, 4 공통)
    'page2_show_cumulative_popup5': False,
    'page2_show_cumulative_popup7': False,
    'page4_show_cumulative_popup5': False,
    'page4_show_cumulative_popup7': False,

    # 비활동 감지 타이머
    'last_interaction_time': time.time(),
}

# 세션 상태 초기화 (기존 상태가 없으면 default_states로 채움)
for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- 페이지 진입 시 타이머 및 팝업 상태 업데이트 ---
# 모든 페이지 함수 호출 전에 실행
def update_page_state_on_entry():
    """
    페이지가 렌더링될 때마다 호출되어 타이머를 업데이트하고,
    페이지 전환 시 특정 상태를 초기화합니다.
    """
    # 비활동 감지 타이머 업데이트 (Streamlit 리렌더링 발생 시마다)
    st.session_state['last_interaction_time'] = time.time()

    # 페이지 이동 감지 및 상태 초기화
    current_page = st.session_state.get('page')
    prev_page = st.session_state.get('prev_page', None)

    if current_page != prev_page:
        # --- 페이지 이동 시 공통 초기화 ---
        # 누적 오답 팝업 상태 초기화 (페이지 이동 시 사라져야 함)
        st.session_state['page2_show_cumulative_popup5'] = False
        st.session_state['page2_show_cumulative_popup7'] = False
        st.session_state['page4_show_cumulative_popup5'] = False
        st.session_state['page4_show_cumulative_popup7'] = False
        # 문제별 피드백 메시지 초기화 (페이지 이동 시 사라져야 함)
        st.session_state['p2p1_feedback'] = None
        st.session_state['p4p1_feedback'] = None
        st.session_state['p4p2_feedback'] = None
        st.session_state['p4p3_feedback'] = None
        st.session_state['p4p4_feedback'] = None


        # --- 특정 페이지로 이동 시 추가 초기화 ---

        # '학생: 이름 입력' 페이지에서 '학생: 목표 평균 60'으로 갈 때
        if current_page == 'student_page_2_graph60' and prev_page == 'student_page_1':
             st.session_state.update({
                'page2_problem_index': 1, # 문제 인덱스 1로 리셋
                'p2p1_answer': '', # 답변 초기화
                'p2p1_correct': False, 'p2p1_attempts': 0, # 과제 1 상태 초기화
                # 누적 팝업 초기화는 위에서 공통 처리됨
             })

        # '학생: 목표 평균 60' 완료 후 '학생: 나만의 평균 설정'으로 갈 때
        # Note: Page 3 -> Page 4 이동 시 Page 4 상태 초기화는 아래 별도로 처리됨
        if current_page == 'student_page_3_myavg_setup' and prev_page == 'student_page_2_graph60':
             st.session_state.update({
                 'target_average_page3': 5, # 목표 평균 기본값으로 리셋
                 'show_graph_page_3': False, # 평균 설정 전 상태로 리셋
             })

        # '학생: 나만의 평균 설정' 완료 후 '학생: 나만의 평균 과제'로 갈 때
        if current_page == 'student_page_4_myavg_tasks' and prev_page == 'student_page_3_myavg_setup':
             st.session_state.update({
                 'page4_problem_index': 1, # 문제 인덱스 1로 리셋
                 'p4p1_correct': False, 'p4p1_attempts': 0, # 과제 2-1 상태 초기화
                 'p4p2_correct': False, 'p4p2_attempts': 0, # 과제 2-2 상태 초기화
                 'p4p3_answer': '', 'p4p3_correct': False, 'p4p3_attempts': 0, # 과제 2-3 상태 초기화
                 'p4p4_answer': '', 'p4p4_correct': False, 'p4p4_attempts': 0, # 과제 2-4 상태 초기화
                 # 누적 오답 초기화는 위에서 공통 처리됨
             })

        # '학생: 학습 완료'에서 '학생: 나만의 평균 설정' (다시 학습)으로 돌아갈 때
        # 이 조건과 초기화 로직을 추가/수정합니다.
        if current_page == 'student_page_3_myavg_setup' and prev_page == 'student_page_5_completion':
             # Page 3 및 Page 4 과제 관련 상태 모두 초기화
             st.session_state.update({
                'target_average_page3': 5, # 목표 평균 기본값으로 리셋
                'show_graph_page_3': False, # 평균 설정 전 상태로 리셋
                'page4_problem_index': 1,
                'p4p1_correct': False, 'p4p1_attempts': 0, 'p4p1_feedback': None,
                'p4p2_correct': False, 'p4p2_attempts': 0, 'p4p2_feedback': None,
                'p4p3_answer': '', 'p4p3_feedback': None, 'p4p3_correct': False, 'p4p3_attempts': 0,
                'p4p4_answer': '', 'p4p4_feedback': None, 'p4p4_correct': False, 'p4p4_attempts': 0,
                # 누적 오답 초기화는 위에서 공통 처리됨
             })


    # 현재 페이지를 이전 페이지로 저장
    st.session_state['prev_page'] = current_page


# --- 컬럼 레이아웃 설정 및 팝업 표시 함수 ---
def setup_columns_and_display_popups(current_page):
    """
    페이지에 따라 컬럼 레이아웃을 설정하고 팝업을 우측 컬럼에 표시합니다.
    그래프 컬럼, 과제 컬럼, 팝업 컬럼 객체 또는 None을 반환합니다.
    반환값: (graph_col, task_col, popup_col) 또는 (main_col, None, popup_col) 또는 (None, None, None)
    """
    graph_col, task_col, popup_col = None, None, None # 컬럼 초기화
    main_col = None # Page 3용 메인 컬럼 초기화

    # 누적 오답 계산 및 팝업 상태 업데이트 (레이아웃 설정 전에 수행)
    cumulative_attempts2 = st.session_state.get('p2p1_attempts', 0)
    cumulative_attempts4 = st.session_state.get('p4p1_attempts', 0) + \
                          st.session_state.get('p4p2_attempts', 0) + \
                          st.session_state.get('p4p3_attempts', 0) + \
                          st.session_state.get('p4p4_attempts', 0)

    # 누적 오답 상태 업데이트
    st.session_state['page2_show_cumulative_popup5'] = (cumulative_attempts2 >= 5)
    st.session_state['page2_show_cumulative_popup7'] = (cumulative_attempts2 >= 7)

    st.session_state['page4_show_cumulative_popup5'] = (cumulative_attempts4 >= 5)
    st.session_state['page4_show_cumulative_popup7'] = (cumulative_attempts4 >= 7)


    # 3컬럼 레이아웃이 필요한 페이지 (그래프 | 과제 | 팝업)
    if current_page in ['student_page_2_graph60', 'student_page_4_myavg_tasks']:
         # 그래프, 과제, 팝업 3개 컬럼 생성 (비율 조정 가능)
         # 화면을 넓게 사용하도록 비율 조정
         # Page 2에서는 그래프가 고정이므로 그래프 컬럼을 좁게, 과제를 넓게 할 수도 있습니다. (현재는 Page 4와 동일 비율)
         graph_col, task_col, popup_col = st.columns([0.4, 0.4, 0.2]) # 예시 비율: 그래프 40%, 과제 40%, 팝업 20%

         # 팝업 내용을 팝업 컬럼에 배치
         with popup_col:
            # 비활동 감지 팝업
            elapsed_time = time.time() - st.session_state.last_interaction_time
            if elapsed_time > INACTIVITY_THRESHOLD_SECONDS:
                 st.info('고민하고 있는건가요? 그래프의 높낮이를 움직이면서 어떤 변화가 있는지 살펴보세요.', icon="💡")

            # 누적 오답 팝업 메시지 표시
            if st.session_state.get('page', 'main') == 'student_page_2_graph60':
                if st.session_state.get('page2_show_cumulative_popup7', False):
                    st.warning(CUMULATIVE_FEEDBACK_7, icon="🚨")
                elif st.session_state.get('page2_show_cumulative_popup5', False):
                    st.warning(CUMULATIVE_FEEDBACK_5, icon="⚠️")
            elif st.session_state.get('page', 'main') == 'student_page_4_myavg_tasks':
                if st.session_state.get('page4_show_cumulative_popup7', False):
                    st.warning(CUMULATIVE_FEEDBACK_7, icon="🚨")
                elif st.session_state.get('page4_show_cumulative_popup5', False):
                    st.warning(CUMULATIVE_FEEDBACK_5, icon="⚠️")

         # 그래프 컬럼, 과제 컬럼, 팝업 컬럼을 반환
         return graph_col, task_col, popup_col

    # 페이지 3 (나만의 평균 설정)은 2컬럼 레이아웃 (메인 콘텐츠 | 팝업)
    elif current_page == 'student_page_3_myavg_setup':
         main_col, popup_col = st.columns([0.7, 0.3]) # 메인 콘텐츠 70%, 팝업 30%

         with popup_col:
            # 비활동 감지 팝업
            elapsed_time = time.time() - st.session_state.last_interaction_time
            if elapsed_time > INACTIVITY_THRESHOLD_SECONDS:
                 st.info('고민하고 있는건가요? 그래프의 높낮이를 움직이면서 어떤 변화가 있는지 살펴보세요.', icon="💡")

            # 누적 오답 팝업 (Page 3에서도 Page 2/4의 누적 오답을 표시)
            if st.session_state.get('page', 'main') == 'student_page_2_graph60':
                if st.session_state.get('page2_show_cumulative_popup7', False):
                    st.warning(CUMULATIVE_FEEDBACK_7, icon="🚨")
                elif st.session_state.get('page2_show_cumulative_popup5', False):
                    st.warning(CUMULATIVE_FEEDBACK_5, icon="⚠️")
            elif st.session_state.get('page', 'main') == 'student_page_4_myavg_tasks':
                if st.session_state.get('page4_show_cumulative_popup7', False):
                    st.warning(CUMULATIVE_FEEDBACK_7, icon="🚨")
                elif st.session_state.get('page4_show_cumulative_popup5', False):
                    st.warning(CUMULATIVE_FEEDBACK_5, icon="⚠️")

         # Page 3에서는 메인 콘텐츠 컬럼과 팝업 컬럼을 반환 (그래프 컬럼 없음)
         return main_col, None, popup_col # 메인 컬럼, 그래프 컬럼(None), 팝업 컬럼 반환

    else: # 팝업 및 특정 레이아웃이 필요 없는 페이지 (main, student_page_1, teacher_page, student_page_5_completion)
        return None, None, None # 컬럼이 필요 없으므로 모두 None 반환


# --- 페이지 함수 정의 ---

# 학생용 페이지 1: 이름 입력
def student_page_1():
    update_page_state_on_entry() # 페이지 진입 시 상태 업데이트

    # 제목 배치 (컬럼 레이아웃 위에)
    st.header("평균 학습 시작")

    # 팝업 없는 페이지이므로 cols는 (None, None, None)
    graph_col, task_col, popup_col = setup_columns_and_display_popups('student_page_1')

    # cols가 None이므로 with 문 사용 안 함, 직접 배치
    st.write("환영합니다! 저는 평균 학습을 도와주는 김함정이라고 해요. 학생의 이름을 입력하고 평균을 학습하러 가볼까요?")
    name = st.text_input("이름을 입력하세요", key="student_name_input")
    if st.button("입장하기", key="btn_enter_student1"):
        if name:
            st.session_state['student_name'] = name
            # save_student_data(name, 1, f"학생 이름 입력: {name}") # 저장 잠시 보류
            # 다음 페이지로 이동 (update_page_state_on_entry에서 다음 페이지 상태 초기화됨)
            st.session_state['page'] = 'student_page_2_graph60'
            st.rerun()
        else:
            st.warning("이름을 입력해주세요.")
    if st.button("이전", key="btn_prev_student1"):
        st.session_state['page'] = 'main'
        st.rerun()

# 학생용 페이지 2: 목표 평균 60 (과제 1)
def student_page_2_graph60():
    update_page_state_on_entry() # 페이지 진입 시 상태 업데이트

    if not st.session_state.get('page_2_timer', False):
        st.session_state['page_2_timer'] = time.time()
        st.session_state['has_interacted'] = False # 제출 버튼 클릭시 True로 변경
    elapsed_time = time.time() - st.session_state['page_2_timer']
    if elapsed_time > INACTIVITY_THRESHOLD_SECONDS and not st.session_state.get('has_interacted', False):
        st.warning("제출을 60초동안 안하셨습니다", icon="⚠️")

    # 제목 배치 (컬럼 레이아웃 위에)
    st.header("목표 평균 60 도전! (과제 1)")
    st.write(f"{st.session_state.get('student_name', '학생')} 학생, 아래 그래프의 막대를 조절하여 평균 60점을 만들어보세요.")
    st.info("막대를 위아래로 드래그하여 점수를 조절할 수 있습니다.")

    # 3컬럼 레이아웃 페이지이므로 graph_col, task_col, popup_col은 컬럼 객체
    graph_col, task_col, popup_col = setup_columns_and_display_popups('student_page_2_graph60')

    # 그래프 컬럼에 그래프 배치
    with graph_col:
        if 'graph_trial' not in st.session_state:
            st.session_state['graph_trial'] = 0
        elif st.session_state['graph_trial'] > 2:
            if len(st.session_state.get('chat_log', [])) == 0:
                st.session_state['chat_log'] = [
                    {"role": "assistant", "content": "그래프를 조정하는 데 어려움을 겪고 있는 것 같아요. 그래프의 높낮이를 조절하면서 어떤 변화가 있는지 살펴보세요."},
                ]
        if 'graph_prev_values' not in st.session_state:
            st.session_state['graph_prev_values'] = (0, 0, 0, 0, 0)
        result = tuple(draggable_barchart("graph_page_2", labels=["1회", "2회", "3회", "4회", "5회"]))
        if result != st.session_state['graph_prev_values']:
            st.session_state['graph_trial'] += 1
            st.session_state['graph_prev_values'] = result
        # # HTML 파일 로드 및 표시 (components.html 사용)
        # # Page 2 그래프는 값 전달 기능 필요 없음. 간단히 표시만. key는 필수 인자가 아닙니다.
        # try:
        #     with open("graph_page_2.html", "r", encoding="utf-8") as f:
        #         html_graph_1 = f.read()
        #     # 'key' 인자 제거 (오류 해결)
        #     components.html(html_graph_1, height=550)
        # except FileNotFoundError:
        #     st.error("오류: graph_page_2.html 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인하세요.")
        # except Exception as e:
        #     st.error(f"HTML 컴포넌트 로딩 중 오류 발생: {e}")

    # 과제 컬럼에 과제 UI 배치
    with task_col:
        st.subheader("과제 1")
        st.write("평균이 60으로 고정되도록 그래프를 움직이면서 **발견한 것**이 있나요?")

        # 학생 응답 입력 (정답 맞추면 비활성화)
        is_input_disabled = st.session_state.get('p2p1_correct', False)
        student_answer = st.text_area("여기에 발견한 내용을 작성하세요:", height=150, key="p2p1_answer_input", value=st.session_state.get('p2p1_answer', ''), disabled=is_input_disabled) # height 추가하여 크기 확보

        # 제출 버튼 (정답 맞추면 비활성화)
        if st.button("답변 제출", key="btn_submit_p2p1", disabled=is_input_disabled):
            st.session_state['has_interacted'] = True # 제출 버튼 클릭 시 True로 변경
            if not student_answer:
                st.warning("답변을 입력해주세요.")
            else:
                # save_student_data(st.session_state['student_name'], 2, f"과제1 답변 제출: {student_answer}") # 데이터 저장 (필요시 활성화)
                st.session_state['p2p1_answer'] = student_answer # 현재 응답 저장

                # GPT를 사용하여 응답 평가
                is_correct, gpt_comment = evaluate_page2_problem1_with_gpt(student_answer, PAGE2_PROBLEM1_GOAL_CONCEPT)

                if is_correct:
                    st.session_state['p2p1_correct'] = True
                    st.session_state['p2p1_feedback'] = f"🎉 {gpt_comment} 정말 잘했어요!"
                    # 누적 오답 팝업 상태 업데이트는 setup_columns_and_display_popups에서 누적 시도 횟수 기반으로 자동 처리됨

                else:
                    # 오답 횟수 증가 (정답 맞추기 전까지만)
                    if not st.session_state.get('p2p1_correct', False):
                         st.session_state['p2p1_attempts'] += 1

                    attempt = st.session_state['p2p1_attempts']
                    # 순차적 오답 피드백 설정 + GPT 코멘트
                    sequential_feedback = PAGE2_PROBLEM1_FEEDBACK_LOOP.get(min(attempt, len(PAGE2_PROBLEM1_FEEDBACK_LOOP)), PAGE2_PROBLEM1_FEEDBACK_LOOP[len(PAGE2_PROBLEM1_FEEDBACK_LOOP)]) # 정의된 최대 횟수 이후는 마지막 피드백 반복
                    st.session_state['p2p1_feedback'] = f"음... 다시 생각해볼까요? {sequential_feedback} {gpt_comment}"

                    # 누적 오답 팝업 상태 업데이트는 setup_columns_and_display_popups에서 누적 시도 횟수 기반으로 자동 처리됨

                st.rerun() # 피드백 표시를 위해 다시 실행

        # 피드백 표시
        if st.session_state.get('p2p1_feedback'):
            if st.session_state.get('p2p1_correct', False):
                st.success(st.session_state['p2p1_feedback'])
            else:
                 st.warning(st.session_state['p2p1_feedback'])
                 # 오답 횟수 표시 (선택 사항)
                 # st.info(f"현재 오답 시도 횟수: {st.session_state['p2p1_attempts']}회")

        chatLog = st.session_state.get('chat_log', [])
        if len(chatLog) > 0:
            for i, chat in enumerate(chatLog):
                if chat["role"] == "system": continue # 시스템 메시지는 표시하지 않음
                with st.chat_message(chat["role"]):
                    st.markdown(chat["content"])
            
            # 채팅 입력창
            chat_input = st.chat_input("답변:")
            if chat_input:
                # 사용자의 입력을 채팅 로그에 추가
                st.session_state['chat_log'].append({"role": "system", "content": "학생이 그래프를 조작하고 있습니다. 그래프의 값: " + str({
                    f"{i+1}회": v for i, v in enumerate(result)
                })})
                st.session_state['chat_log'].append({"role": "user", "content": chat_input})
                st.rerun()
            
            elif chatLog[-1]["role"] == "user":
                response = client.chat.completions.create(
                    model="gpt-4.1",
                    messages=st.session_state['chat_log'],
                )

                print(response)

                # GPT의 응답을 채팅 로그에 추가
                st.session_state['chat_log'].append({"role": "assistant", "content": response.choices[0].message.content})
                st.rerun()


        # 다음 페이지 이동 버튼 (과제 1 정답 시 활성화)
        if st.session_state.get('p2p1_correct', False):
            if st.button("다음 과제로 이동", key="btn_next_p2"):
                st.session_state['page'] = 'student_page_3_myavg_setup' # 다음 페이지로 이동
                st.rerun()
        elif st.session_state.get('p2p1_feedback'): # 정답이 아니지만 피드백이 있으면 안내
             st.info("정답을 맞춰야 다음 과제로 넘어갈 수 있습니다.")


    # 컬럼 밖에 배치 (전체 너비 버튼)
    if st.button("이전", key="btn_prev_p2_full"): # 버튼 키 변경 (컬럼 안의 이전 버튼과 구분)
        st.session_state['page'] = 'student_page_1'
        st.rerun()


# 학생용 페이지 3: 나만의 평균 설정
def student_page_3_myavg_setup():
    update_page_state_on_entry() # 페이지 진입 시 상태 업데이트

    # 제목 배치 (컬럼 레이아웃 위에)
    st.header("나만의 평균 만들기 (설정)")
    st.write(f"{st.session_state.get('student_name', '학생')} 학생, 앞에서는 평균이 60점으로 주어졌을 때 여러 점수 조합이 가능하다는 것을 확인했어요.")
    st.write("이제는 여러분이 **원하는 평균 점수 (1점 ~ 10점)**를 직접 만들고, 그렇게 만들기 위해 막대 그래프의 값들을 어떻게 조절할 수 있는지 탐색해 보세요!")

    # Page 3는 2컬럼 레이아웃 (메인 | 팝업)
    # setup_columns_and_display_popups는 Page 3에서 main_col, None, popup_col을 반환
    main_col, graph_col, popup_col = setup_columns_and_display_popups('student_page_3_myavg_setup')

    with main_col: # 메인 콘텐츠 컬럼 안에 내용 배치
        # 평균 설정 입력 (설정 완료 시 비활성화)
        is_input_disabled = st.session_state.get('show_graph_page_3', False)
        col1, col2 = st.columns([3, 1]) # 이 컬럼은 설정 UI 내부의 미니 컬럼
        with col1:
            target_avg_input = st.number_input("만들고 싶은 평균 점수를 입력하세요 (1~10)", min_value=1, max_value=10, step=1, value=st.session_state.get('target_average_page3', 5), disabled=is_input_disabled, key="target_avg_input_page3") # 기본값 설정
        with col2:
             st.write(""); st.write("") # 버튼 위치 조정을 위한 빈 공간
             if st.button("평균 설정", key="btn_set_avg_p3", disabled=is_input_disabled):
                  st.session_state['target_average_page3'] = target_avg_input
                  st.session_state['show_graph_page_3'] = True
                  # Page 4 과제 상태 초기화는 student_page_3_myavg_setup -> student_page_4_myavg_tasks 이동 시 update_page_state_on_entry에서 처리됨
                  st.rerun()

        # 평균 설정 완료 후 다음 단계 버튼 표시 (그래프는 Page 4에서 표시)
        if st.session_state.get('show_graph_page_3', False):
            st.success(f"목표 평균: **{st.session_state.get('target_average_page3', 5)}** 점으로 설정되었습니다.")
            st.write("이제 이 목표 평균으로 그래프를 조절하는 과제를 시작할 수 있습니다.")

            # 다음 과제(페이지 4)로 이동하는 버튼
            if st.button("나만의 평균 과제 시작", key="btn_start_p4"):
                 st.session_state['page'] = 'student_page_4_myavg_tasks'
                 st.rerun()

            # 다른 평균으로 변경하기 버튼
            if st.button("다른 목표 평균으로 변경하기", key="btn_change_avg_p3"):
                st.session_state['show_graph_page_3'] = False
                st.rerun()

    # 메인 컬럼 밖에 배치 (전체 너비 버튼)
    if st.button("이전", key="btn_prev_p3_full"): # 버튼 키 변경
        st.session_state['page'] = 'student_page_2_graph60'
        st.rerun()


# 학생용 페이지 4: 나만의 평균 과제 (문제 1~4)
def student_page_4_myavg_tasks():
    update_page_state_on_entry() # 페이지 진입 시 상태 업데이트

    target_avg = st.session_state.get('target_average_page3', 5) # 설정된 목표 평균 가져오기
    current_problem_index = st.session_state.get('page4_problem_index', 1) # 현재 진행 중인 문제 번호 가져오기 (기본값 1)

    # 제목 배치 (컬럼 레이아웃 위에)
    st.header(f"나만의 평균 과제 (목표 평균: {target_avg}점)")
    st.write(f"{st.session_state.get('student_name', '학생')} 학생, 설정한 목표 평균 **{target_avg}**점을 달성하기 위한 과제들을 해결해봅시다.")


    # 3컬럼 레이아웃 페이지이므로 graph_col, task_col, popup_col은 컬럼 객체
    graph_col, task_col, popup_col = setup_columns_and_display_popups('student_page_4_myavg_tasks')

    # 그래프 컬럼에 그래프 배치
    with graph_col:
        # 과제 2-1, 2-2에 필요한 그래프 표시
        # 이 그래프는 HTML/JS에서 조작되지만, components.html은 값을 파이썬으로 직접 반환하지 않습니다.
        # 따라서 아래 문제들의 "제출" 버튼 로직은 현재 HTML로부터 값을 받을 수 없습니다.
        st.info("**참고:** 그래프를 조작할 수 있지만, 조작된 막대 값은 현재 앱으로 전달되지 않아 제출 시 평가되지 않습니다. 이 기능은 사용자 지정 컴포넌트로 구현해야 합니다.")
        try:
            with open("graph_page_3.html", "r", encoding="utf-8") as f: html_template = f.read()
            # 자바스크립트에 목표 평균 값 전달 (스크립트 주입 방식은 작동)
            js_injection = f"""<script>window.pythonTargetAverage = {target_avg}; console.log("Python Target Average:", window.pythonTargetAverage);</script>"""
            html_graph_modified = html_template.replace("</head>", f"{js_injection}</head>", 1)
            if "</head>" not in html_template: html_graph_modified = html_template.replace("</body>", f"{js_injection}</body>", 1)
            # 'key' 인자 제거 (오류 해결), 할당문 제거
            components.html(html_graph_modified, height=500)
        except FileNotFoundError:
            st.error("오류: graph_page_3.html 파일을 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"HTML 처리 중 오류 발생: {e}")

    # 과제 컬럼에 과제 UI 배치
    with task_col:
        # --- 문제 영역 (현재 문제에 따라 UI 변경) ---

        if current_problem_index == 1:
            st.subheader("과제 2-1")
            st.write(f"목표 평균 {target_avg}점을 달성하기 위해 그래프 자료값을 변경해볼까요? 위에 표시된 그래프의 막대들을 조절해서 평균을 **{target_avg}**점으로 만들어보세요. (값 평가는 현재 작동하지 않습니다.)")

            # 제출 버튼 (값 평가 기능 없음)
            if st.button("제출 (값 평가 기능 없음)", key="btn_submit_p4p1"):
                 # save_student_data(st.session_state['student_name'], 4, f"과제2-1 제출 (값 평가 안됨)") # 데이터 저장
                 st.session_state['p4p1_attempts'] += 1 # 시도 횟수만 증가
                 # 값 평가는 현재 불가하므로, 제출 즉시 다음 문제로 넘어가도록 처리 (요구사항과 다름, 임시 방편)
                 st.session_state['p4p1_correct'] = True # 다음 문제로 넘어가기 위해 강제 True
                 st.session_state['p4p1_feedback'] = "그래프 값 평가는 현재 작동하지 않습니다. 다음 문제로 이동합니다."
                 st.rerun()

            # 피드백 표시 (임시 메시지)
            if st.session_state.get('p4p1_feedback'):
                 if st.session_state.get('p4p1_correct', False):
                     st.info(st.session_state['p4p1_feedback']) # 성공 메시지 아님 주의
                 else: # 이 분기는 현재 제출 로직에서 발생하지 않음
                      st.warning(st.session_state['p4p1_feedback'])
                 st.info(f"현재 과제 2-1 시도 횟수: {st.session_state.get('p4p1_attempts', 0)}회")


            # 다음 문제 이동 버튼 (과제 1 정답 조건 삭제: 제출 버튼 누르면 무조건 활성화)
            if st.button("다음 문제로 이동", key="btn_next_p4p1_actual"): # 실제 이동 버튼
                 st.session_state['page4_problem_index'] = 2 # 문제 번호 증가
                 # 다음 문제 상태 초기화 (page_state_on_entry에서 처리)
                 st.rerun()
            # else: # 제출하지 않으면 안내 (필요시 활성화)
            #      st.info("'제출' 버튼을 눌러야 다음 문제로 넘어갈 수 있습니다. (값 평가는 현재 작동하지 않습니다)")


        elif current_problem_index == 2:
             st.subheader("과제 2-2")
             st.write(f"앞에서 제출한 자료값과 **다른 자료값들**로 이루어진 그래프를 만들어 평균 {target_avg}점을 달성해볼까요? (값 평가는 현재 작동하지 않습니다.)")

             # 제출 버튼 (값 평가 기능 없음)
             if st.button("제출 (값 평가 기능 없음)", key="btn_submit_p4p2"):
                  # save_student_data(st.session_state['student_name'], 4, f"과제2-2 제출 (값 평가 안됨)") # 데이터 저장
                  st.session_state['p4p2_attempts'] += 1 # 시도 횟수만 증가
                  # 값 평가는 현재 불가하므로, 제출 즉시 다음 문제로 넘어가도록 처리 (요구사항과 다름, 임시 방편)
                  st.session_state['p4p2_correct'] = True # 다음 문제로 넘어가기 위해 강제 True
                  st.session_state['p4p2_feedback'] = "그래프 값 평가는 현재 작동하지 않습니다. 다음 문제로 이동합니다."
                  st.rerun()

             # 피드백 표시 (임시 메시지)
             if st.session_state.get('p4p2_feedback'):
                  if st.session_state.get('p4p2_correct', False):
                      st.info(st.session_state['p4p2_feedback']) # 성공 메시지 아님 주의
                  else: # 이 분기는 현재 제출 로직에서 발생하지 않음
                       st.warning(st.session_state['p4p2_feedback'])
                  st.info(f"현재 과제 2-2 시도 횟수: {st.session_state.get('p4p2_attempts', 0)}회")


             # 다음 문제 이동 버튼 (과제 2 정답 조건 삭제: 제출 버튼 누르면 무조건 활성화)
             if st.button("다음 문제로 이동", key="btn_next_p4p2_actual"): # 실제 이동 버튼
                   st.session_state['page4_problem_index'] = 3 # 문제 번호 증가
                   # 다음 문제 상태 초기화 (page_state_on_entry에서 처리)
                   st.rerun()
             # else: # 제출하지 않으면 안내 (필요시 활성화)
             #       st.info("'제출' 버튼을 눌러야 다음 문제로 넘어갈 수 있습니다. (값 평가는 현재 작동하지 않습니다)")


        elif current_problem_index == 3:
             st.subheader("과제 2-3")
             st.write(f"목표 평균 {target_avg}점을 달성하기 위한 여러분만의 전략은 무엇이었나요?")

             # 학생 응답 입력 (정답 맞추면 비활성화 - 이 문제는 GPT 피드백 후 다음 문제로 이동)
             is_input_disabled = st.session_state.get('p4p3_feedback') is not None # 피드백을 받으면 입력 비활성화
             student_answer = st.text_area("여기에 전략을 작성하세요:", height=150, key="p4p3_answer_input", value=st.session_state.get('p4p3_answer', ''), disabled=is_input_disabled) # height 추가

             # 제출 버튼 (정답 맞추면 비활성화 - 이 문제는 GPT 피드백 후 다음 문제로 이동)
             if st.button("답변 제출", key="btn_submit_p4p3", disabled=is_input_disabled):
                 if not student_answer:
                     st.warning("답변을 입력해주세요.")
                 else:
                     # save_student_data(st.session_state['student_name'], 4, f"과제2-3 답변 제출: {student_answer}") # 데이터 저장
                     st.session_state['p4p3_answer'] = student_answer # 현재 응답 저장
                     st.session_state['p4p3_attempts'] += 1 # 시도 횟수 증가

                     # GPT를 사용하여 응답 평가 및 스캐폴딩 피드백 생성
                     is_correct, gpt_comment = evaluate_page4_problem3_with_gpt(student_answer, PAGE4_PROBLEM3_GOAL_CONCEPT, PAGE4_PROBLEM3_SCAFFOLDING_PROMPT)

                     st.session_state['p4p3_feedback'] = gpt_comment
                     # 과제 2-3은 제출하면 완료로 간주하고 다음 문제로 넘어갈 수 있도록 플래그 설정
                     st.session_state['p4p3_correct'] = True

                     st.rerun() # 피드백 표시 위해 다시 실행

             # 피드백 표시
             if st.session_state.get('p4p3_feedback'):
                  # 과제 2-3 피드백은 정답/오답 형태가 아니므로 info로 표시
                  st.info(st.session_state['p4p3_feedback'])
                  # 오답 횟수 표시
                  st.info(f"현재 과제 2-3 시도 횟수: {st.session_state.get('p4p3_attempts', 0)}회")


             # 다음 문제 이동 버튼 (답변 제출 시 활성화)
             if st.session_state.get('p4p3_correct', False): # 제출 후에는 True가 됨
                  if st.button("다음 문제로 이동", key="btn_next_p4p3"):
                       st.session_state['page4_problem_index'] = 4 # 문제 번호 증가
                       # 다음 문제 상태 초기화 (page_state_on_entry에서 처리)
                       st.rerun()
             # else: # 제출하지 않으면 안내
             #       st.info("답변을 제출해야 다음 문제로 넘어갈 수 있습니다.")


        elif current_problem_index == 4:
             st.subheader("과제 2-4")
             st.write("여기에서 발견한 평균의 성질은 무엇이 있나요? 여러 가지를 적어도 좋습니다.")
             st.write("혹시, 평균의 함정을 발견한 친구 있나요? 있다면 자세히 설명해주세요.")

             # 학생 응답 입력 (정답 맞추면 비활성화 - 이 문제는 제출 즉시 다음 페이지 이동 버튼 활성화)
             is_input_disabled = st.session_state.get('p4p4_feedback') is not None # 피드백을 받으면 입력 비활성화
             student_answer = st.text_area("여기에 발견한 내용을 작성하세요:", height=200, key="p4p4_answer_input", value=st.session_state.get('p4p4_answer', ''), disabled=is_input_disabled) # height 추가

             # 제출 버튼 (정답 맞추면 비활성화 - 이 문제는 제출 즉시 다음 페이지 이동 버튼 활성화)
             if st.button("답변 제출", key="btn_submit_p4p4", disabled=is_input_disabled):
                 if not student_answer:
                     st.warning("답변을 입력해주세요.")
                 else:
                     # save_student_data(st.session_state['student_name'], 4, f"과제2-4 답변 제출: {student_answer}") # 데이터 저장
                     st.session_state['p4p4_answer'] = student_answer # 현재 응답 저장
                     st.session_state['p4p4_attempts'] += 1 # 시도 횟수 증가

                     # GPT를 사용하여 피드백 생성 (이 문제는 정답/오답 판단보다는 탐구 유도)
                     is_correct, gpt_comment = evaluate_page4_problem4_with_gpt(student_answer)

                     # 과제 2-4는 제출만 하면 완료로 간주하고 다음 페이지로 이동
                     st.session_state['p4p4_feedback'] = gpt_comment
                     st.session_state['p4p4_correct'] = True # 제출 후에는 True가 됨

                     st.rerun() # 피드백 표시 위해 다시 실행

             # 피드백 표시
             if st.session_state.get('p4p4_feedback'):
                  # 과제 2-4 피드백은 정답/오답 형태가 아니므로 info로 표시
                  st.info(st.session_state['p4p4_feedback'])
                  # 오답 횟수 표시
                  st.info(f"현재 과제 2-4 시도 횟수: {st.session_state.get('p4p4_attempts', 0)}회")

             # 다음 페이지 이동 버튼 (답변 제출 시 활성화)
             # 정답 조건 삭제: 제출 버튼 누르면 무조건 활성화
             # if st.session_state.get('p4p4_correct', False): # <- 이 조건 삭제
             if st.button("학습 완료 페이지로 이동", key="btn_next_p4p4"):
                  st.session_state['page'] = 'student_page_5_completion' # 최종 완료 페이지로 이동
                  st.rerun()
             # else: # 제출하지 않으면 안내 (필요시 활성화)
             #       st.info("답변을 제출해야 다음 페이지로 넘어갈 수 있습니다.")


    # 컬럼 밖에 배치 (전체 너비 버튼)
    # 과제 중간에 이전 페이지로 돌아갈 수 있도록 허용
    if st.button("이전 페이지로 돌아가기", key="btn_prev_p4_full"): # 버튼 키 변경
        # 이전 페이지는 Page 3 (나만의 평균 설정)
        st.session_state['page'] = 'student_page_3_myavg_setup'
        st.rerun()


# 학생용 페이지 5: 학습 완료
def student_page_5_completion():
    update_page_state_on_entry() # 페이지 진입 시 상태 업데이트

    # 제목 배치 (컬럼 레이아웃 위에)
    st.header("학습 완료!")

    # 팝업 없는 페이지이므로 cols는 (None, None, None)
    graph_col, task_col, popup_col = setup_columns_and_display_popups('student_page_5_completion')

    # cols가 None이므로 with 문 사용 안 함, 직접 배치
    st.balloons() # 축하 효과!
    st.write(f"{st.session_state.get('student_name', '학생')} 학생, 평균 학습 과제를 모두 완료했습니다!")
    st.write("수고했어요! 오늘의 학습은 여기까지입니다. 나만의 평균 만들기에서 다른 목표 평균값으로 다시 시도해보는 것도 좋을 것 같아요. :)")

    # 다시 학습하기 버튼 (Page 3로 이동하도록 수정)
    if st.button("다른 목표 평균값으로 다시 시도하기", key="btn_restart_p5"): # 버튼 텍스트도 변경
        st.session_state['page'] = 'student_page_3_myavg_setup' # Page 3 (나만의 평균 설정)으로 이동
        # student_page_3_myavg_setup 진입 시 update_page_state_on_entry에서 Page 3,4 상태가 초기화됨
        st.rerun()

    # 메인 페이지 버튼
    if st.button("메인 페이지로", key="btn_main_from_p5"):
        st.session_state['page'] = 'main'
        st.rerun()

# 교사용 페이지
def teacher_page():
    update_page_state_on_entry() # 페이지 진입 시 상태 업데이트

    # 제목 배치 (컬럼 레이아웃 위에)
    st.header("교사용 페이지")

    # 팝업 없는 페이지이므로 cols는 (None, None, None)
    graph_col, task_col, popup_col = setup_columns_and_display_popups('teacher_page')

    # cols가 None이므로 with 문 사용 안 함, 직접 배치
    password = st.text_input("비밀번호를 입력하세요", type="password", key="teacher_pw")
    if password == TEACHER_PASSWORD:
        st.success("접속 성공!")
        st.subheader("학생 학습 데이터 조회")
        try: student_files = [f for f in os.listdir(STUDENT_DATA_DIR) if f.startswith("student_") and f.endswith(".json")]
        except FileNotFoundError: st.error(f"데이터 폴더({STUDENT_DATA_DIR})를 찾을 수 없습니다."); student_files = []
        if not student_files: st.info("아직 저장된 학생 데이터가 없습니다.");
        else:
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

    # 이전 페이지 버튼
    if st.button("이전", key="btn_prev_teacher"):
        st.session_state['page'] = 'main'
        st.rerun()

# 메인 페이지
def main_page():
    update_page_state_on_entry() # 페이지 진입 시 상태 업데이트
    # 앱 전체 시작 시간은 여기에서만 설정
    if 'enter_time' not in st.session_state:
        st.session_state.enter_time = time.time()

    # 제목 배치 (컬럼 레이아웃 위에)
    st.title("📊 평균 학습 웹 앱") # 메인 페이지는 보통 title 사용

    # 팝업 없는 페이지이므로 cols는 (None, None, None)
    graph_col, task_col, popup_col = setup_columns_and_display_popups('main')

    # cols가 None이므로 with 문 사용 안 함, 직접 배치
    st.write("학생 또는 교사로 접속하여 평균 개념을 학습하거나 학습 현황을 확인해보세요.")
    user_type = st.radio("접속 유형 선택:", ("학생용", "교사용"), key="user_type_radio", horizontal=True)
    if st.button("선택 완료", key="btn_select_user_type"):
        if user_type == "학생용":
             st.session_state['page'] = 'student_page_1'
             # 학생 학습 시작 시 모든 학생 관련 상태 초기화
             st.session_state.update({
                'student_name': '', # 이름도 초기화
                'page2_problem_index': 1,
                'p2p1_answer': '', 'p2p1_feedback': None, 'p2p1_correct': False, 'p2p1_attempts': 0,
                'target_average_page3': 5, 'show_graph_page_3': False,
                'page4_problem_index': 1,
                'p4p1_correct': False, 'p4p1_attempts': 0, 'p4p1_feedback': None,
                'p4p2_correct': False, 'p4p2_attempts': 0, 'p4p2_feedback': None,
                'p4p3_answer': '', 'p4p3_feedback': None, 'p4p3_correct': False, 'p4p3_attempts': 0,
                'p4p4_answer': '', 'p4p4_feedback': None, 'p4p4_correct': False, 'p4p4_attempts': 0,
                'page2_show_cumulative_popup5': False, 'page2_show_cumulative_popup7': False,
             })
        elif user_type == "교사용":
             st.session_state['page'] = 'teacher_page'
        st.rerun()


# --- 페이지 라우팅 ---
# 페이지 이름과 함수 매핑
pages = {
    'main': main_page,
    'student_page_1': student_page_1, # 이름 입력
    'student_page_2_graph60': student_page_2_graph60, # 목표 평균 60 (과제 1)
    'student_page_3_myavg_setup': student_page_3_myavg_setup, # 나만의 평균 설정
    'student_page_4_myavg_tasks': student_page_4_myavg_tasks, # 나만의 평균 과제 (2-1 ~ 2-4)
    'student_page_5_completion': student_page_5_completion, # 학습 완료
    'teacher_page': teacher_page,
}

# 사이드바 메뉴
with st.sidebar:
    # 전체 메뉴 항목 정의 (숨김 여부와 무관)
    full_menu = {
        "main": "홈",
        "student_page_1": "학생: 이름 입력",
        "student_page_2_graph60": "학생: 목표 평균 60 (과제 1)",
        "student_page_3_myavg_setup": "학생: 나만의 평균 설정",
        "student_page_4_myavg_tasks": "학생: 나만의 평균 과제 (2-1~2-4)",
        "student_page_5_completion": "학생: 학습 완료", # 학습 완료 페이지 메뉴 항목 추가
        "teacher_page": "교사용"
    }

    # 사이드바에 표시될 메뉴 항목 (이번에는 모든 학생/교사 페이지를 항상 표시)
    # 교사용 페이지는 비밀번호로 보호되므로 항상 표시해도 무방
    # 학습 완료 페이지도 이제 항상 표시
    menu_to_display = full_menu.copy()
    # 특정 페이지를 메뉴에서 제외하고 싶다면 여기서 del menu_to_display['key'] 사용 (이번에는 제외 없음)


    page_keys = list(menu_to_display.keys())
    page_labels = list(menu_to_display.values())

    # 현재 페이지 키 가져오기
    current_page_key = st.session_state.get('page', 'main')

    # 현재 페이지 키가 표시될 메뉴에 없거나 유효하지 않으면 'main'으로 리다이렉트 (발생 가능성 낮음)
    if current_page_key not in page_keys and current_page_key in full_menu:
         # 현재 페이지가 표시될 메뉴에는 없지만 전체 메뉴에는 있다면 (예: 숨김 처리 페이지였던 경우),
         # 해당 페이지 라벨을 찾아 default_index 계산에 사용
         current_page_label = full_menu[current_page_key]
         try:
              default_index = page_labels.index(current_page_label)
         except ValueError:
              # 숨겨진 페이지였고 표시될 메뉴에 같은 라벨이 없다면 기본 인덱스 0 (발생 가능성 낮음)
              default_index = 0
    elif current_page_key not in full_menu: # 정의된 모든 페이지(full_menu)에도 없다면 main으로
         current_page_key = 'main'
         st.session_state['page'] = current_page_key # 유효하지 않은 경우 상태 업데이트
         current_page_label = full_menu.get(current_page_key, page_labels[0] if page_labels else "홈")
         default_index = page_labels.index(current_page_label) if current_page_label in page_labels else 0
    else: # 현재 페이지 키가 표시될 메뉴에 있다면 해당 라벨로 인덱스 설정
         current_page_label = menu_to_display.get(current_page_key, page_labels[0] if page_labels else "홈")
         default_index = page_labels.index(current_page_label)

    selected_label = option_menu(
        "메뉴", page_labels,
        icons=['house', 'person', 'bar-chart', 'pencil', 'star', 'check-circle', 'lock'], # 아이콘 추가/변경
        menu_icon="app-indicator",
        default_index=default_index,
        manual_select=page_keys.index(st.session_state.get('page', 'main')),
        key="sidebar_menu", # 사이드바 메뉴 자체에 고유 키 추가
    )
    if st.session_state.get('prev_option_selected', None) != selected_label:
        st.session_state['prev_option_selected'] = selected_label

        # 메뉴 선택 시 페이지 이동 (현재 페이지와 다르면 이동)
        # 선택된 라벨에 해당하는 키를 찾음 (전체 메뉴 기준)
        selected_key = None
        for key, label in full_menu.items(): # 전체 메뉴를 기준으로 키를 찾아야 정확함
            if label == selected_label:
                selected_key = key
                break

        if selected_key and st.session_state['page'] != selected_key:
            st.session_state['page'] = selected_key
            # 페이지 이동 시 상태 초기화는 update_page_state_on_entry에서 처리됩니다.
            st.rerun()


# 페이지 진입 상태 업데이트 함수 호출 (렌더링 함수 호출 전에)
update_page_state_on_entry()

# 선택된 페이지 렌더링
render_page = pages.get(st.session_state['page'], main_page)
render_page()