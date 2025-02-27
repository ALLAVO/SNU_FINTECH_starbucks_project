import streamlit as st
import networkx as nx
import json
from pyvis.network import Network
import pandas as pd
import numpy as np
import tempfile
import os
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="스타벅스 키워드 네트워크",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터 로드 함수
@st.cache_data
def load_keywords_data():
    with open('./keyword_data/store_keywords.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data
def load_theme_keywords():
    df = pd.read_csv('./keyword_data/0_네이버_리뷰_테마_전체.csv')
    return df['Keywords'].tolist()

# 키워드 카테고리 매핑 함수
def map_keywords_to_categories(keywords):
    # 카테고리 키워드 맵핑
    category_keywords = {
        "맛/음료": ["맛있", "커피", "디저트", "메뉴", "음료", "차가", "양이"],
        "청결/위생": ["청결", "깨끗", "화장실"],
        "좌석/공간": ["좌석", "편해", "자리", "넓어", "의자", "매장이 넓"],
        "인테리어/분위기": ["인테리어", "분위기", "예쁜", "멋", "뷰", "사진", "음악"],
        "서비스": ["친절", "서비스", "가성비"],
        "사교/대화": ["대화", "수다", "친구"],
        "집중/업무": ["집중", "공부", "카공", "오래 머무"]
    }
    
    keyword_to_category = {}
    
    # 각 키워드를 적절한 카테고리로 매핑
    for keyword in keywords:
        keyword_lower = keyword.lower()
        assigned = False
        
        for category, patterns in category_keywords.items():
            if not assigned:
                for pattern in patterns:
                    if pattern in keyword_lower:
                        keyword_to_category[keyword] = category
                        assigned = True
                        break
        
        if not assigned:
            keyword_to_category[keyword] = "기타"
    
    return keyword_to_category

# 키워드 네트워크 데이터 생성 함수
def create_keyword_network(data, min_edge_weight=0, max_edges=100, theme_keywords=None, min_node_value=0):
    # 키워드 총 빈도수 계산
    keyword_total_freq = {}
    for store, keywords in data.items():
        for keyword, freq in keywords.items():
            keyword_total_freq[keyword] = keyword_total_freq.get(keyword, 0) + freq
    
    # 테마 키워드 필터링
    if theme_keywords:
        filtered_keywords = {k: v for k, v in keyword_total_freq.items() if k in theme_keywords}
    else:
        filtered_keywords = keyword_total_freq
    
    # 최소 빈도수 필터링
    filtered_keywords = {k: v for k, v in filtered_keywords.items() if v >= min_node_value}
    
    # 카테고리 매핑
    keyword_categories = map_keywords_to_categories(filtered_keywords.keys())
    
    # 노드 생성
    nodes = []
    for keyword, freq in filtered_keywords.items():
        category = keyword_categories.get(keyword, "기타")
        
        # 노드 크기 계산 (로그 스케일로 조정)
        size = 15 + np.log1p(freq) * 5
        
        nodes.append({
            "id": keyword,
            "label": keyword,
            "value": freq,
            "title": f"{keyword}<br>총 언급 횟수: {freq}회",
            "category": category,
            "size": size
        })
    
    # 동시 등장 관계 행렬 생성
    co_occurrence = {}
    node_connections = {}
    
    # 키워드 빈도 정규화 (상위 키워드의 영향 감소)
    max_freq = max(filtered_keywords.values())
    normalized_keywords = {k: v/max_freq for k, v in filtered_keywords.items()}
    
    for store, store_keywords in data.items():
        keyword_list = list(store_keywords.keys())
        
        for i, keyword1 in enumerate(keyword_list):
            if keyword1 not in filtered_keywords:
                continue
                
            if keyword1 not in co_occurrence:
                co_occurrence[keyword1] = {}
                node_connections[keyword1] = {}
            
            for j, keyword2 in enumerate(keyword_list):
                if i != j and keyword2 in filtered_keywords:
                    # 연관 강도 계산 (정규화된 빈도 사용)
                    strength = np.sqrt(
                        normalized_keywords[keyword1] * 
                        normalized_keywords[keyword2] * 
                        store_keywords[keyword1] * 
                        store_keywords[keyword2]
                    )
                    
                    co_occurrence[keyword1][keyword2] = co_occurrence[keyword1].get(keyword2, 0) + strength
                    node_connections[keyword1][keyword2] = node_connections[keyword1].get(keyword2, 0) + strength
    
    # 엣지 생성
    edges = []
    for keyword1, relations in co_occurrence.items():
        for keyword2, strength in relations.items():
            # 중복 방지 (A-B와 B-A 중 하나만 추가)
            if keyword1 < keyword2 and strength >= min_edge_weight:
                edges.append({
                    'from': keyword1,
                    'to': keyword2,
                    'value': strength,
                    'title': f"{keyword1} ↔ {keyword2}: {strength:.1f}"
                })
    
    # 강도 기준 내림차순 정렬
    edges.sort(key=lambda x: x['value'], reverse=True)
    
    # 최대 엣지 수 제한
    edges = edges[:max_edges]
    
    # 각 노드에 대한 상위 연관 키워드 데이터
    node_top_connections = {}

    for node_id in node_connections:
        # 상위 6개 키워드로 변경
        top_cons = sorted(node_connections[node_id].items(), key=lambda x: x[1], reverse=True)[:6]
        node_top_connections[node_id] = [conn[0] for conn in top_cons]
        
    # 각 노드의 연관 강도 저장
    node_connection_strengths = {}
    for node_id in node_connections:
        connections = node_connections[node_id]
        sorted_connections = sorted(connections.items(), key=lambda x: x[1], reverse=True)
        node_connection_strengths[node_id] = {conn[0]: conn[1] for conn in sorted_connections[:6]}
    
    return {
        'nodes': nodes,
        'edges': edges,
        'top_connections': node_top_connections,
        'connection_strengths': node_connection_strengths
    }
    
# 카테고리별 색상 매핑
def get_category_colors():
    return {
        "맛/음료": "#006241",  # 스타벅스 그린
        "청결/위생": "#00A862",  # 밝은 초록색
        "좌석/공간": "#D4B59E",  # 베이지색
        "인테리어/분위기": "#FF8C3A",  # 주황색
        "서비스": "#1A75CF",  # 파란색
        "사교/대화": "#E01931",  # 빨간색
        "집중/업무": "#9370DB",  # 보라색
        "기타": "#767676"  # 회색
    }

# 세션 상태의 초기 좌표 가져오기
def get_initial_positions():
    if 'network_positions' not in st.session_state:
        # 초기값 생성 (빈 딕셔너리)
        st.session_state.network_positions = {}
    return st.session_state.network_positions

# 메인 앱
def main():
    st.title("☕ 스타벅스 리뷰 키워드 네트워크 그래프")
    
    # 리셋 플래그 설정
    if "reset_selection" in st.session_state and st.session_state["reset_selection"]:
        # 리셋 플래그 제거
        st.session_state["reset_selection"] = False
        # 새 세션 상태 변수 설정 (기존 node_selector는 직접 수정 불가)
        st.session_state["node_selector"] = "-- 선택하세요 --"

    # 데이터 로드
    keywords_data = load_keywords_data()
    theme_keywords = load_theme_keywords()
    
    # 네트워크 데이터 생성 (최적화된 기본값)
    network_data = create_keyword_network(
        keywords_data,
        min_edge_weight=150,  # 최적화된 기본값
        max_edges=80,         # 더 많은 연결 표시
        theme_keywords=theme_keywords,
        min_node_value=30     # 약간 낮춘 최소 빈도값
    )
    
    nodes = network_data['nodes']
    node_ids = [node['id'] for node in nodes]
    edges = network_data['edges']
    top_connections = network_data['top_connections']
    conn_strengths = network_data['connection_strengths']
    
    # 카테고리 범례 표시 (카테고리 선택 기능 없음)
    category_colors = get_category_colors()
    categories = set(node['category'] for node in nodes)
    
    st.markdown('#### 키워드 카테고리')
    category_list = sorted(categories) if categories else []
    num_categories = len(category_list)

    if num_categories > 0:
        category_cols = st.columns(num_categories)
        for i, category in enumerate(category_list):
            with category_cols[i]:
                color = category_colors.get(category, "#767676")
                st.markdown(
                    f'<div style="display: flex; align-items: center; justify-content: center; margin-bottom: 10px;">'
                    f'<div style="width: 15px; height: 15px; background-color: {color}; '
                    f'margin-right: 8px; border-radius: 50%;"></div>'
                    f'<span>{category}</span></div>',
                    unsafe_allow_html=True
                )
    else:
        st.info("키워드 카테고리 정보가 없습니다.")
    # 노드 선택 드롭다운 (리스트 방식)
    st.markdown("#### 키워드 선택")
    
    # 노드 ID 정렬 (가나다순)
    sorted_node_ids = sorted(node_ids)
    
    selected_node = st.selectbox(
        "키워드를 선택하면 연관성이 가장 높은 TOP 6 키워드가 표시됩니다",
        options=["-- 선택하세요 --"] + sorted_node_ids,
        key="node_selector"
    )
    
    if selected_node == "-- 선택하세요 --":
        selected_node = None
    
    # 하이라이트 리셋 버튼
    if selected_node:
        if st.button("모든 키워드 표시로 돌아가기"):
            # 리셋 플래그를 세션 상태에 설정
            st.session_state["reset_selection"] = True
            st.rerun()
    
    # 네트워크 그래프 영역
    st.markdown("#### 네트워크 그래프")
    st.info(f"총 {len(nodes)}개의 키워드와 {len(edges)}개의 연관 관계가 표시됩니다.")
    
    # 네트워크 그래프 생성
    net = Network(height="700px", width="100%", notebook=False, bgcolor="#ffffff", directed=False)
    
    # 선택된 노드와 연관된 TOP 노드 찾기
    highlighted_nodes = []
    highlighted_edges = []

    if selected_node and selected_node in top_connections:
        # TOP 6개 키워드로 변경
        highlighted_nodes = top_connections[selected_node][:6] + [selected_node]
        
        # 하이라이트할 엣지 찾기
        for edge in edges:
            if ((edge['from'] == selected_node and edge['to'] in highlighted_nodes) or
                (edge['to'] == selected_node and edge['from'] in highlighted_nodes)):
                highlighted_edges.append((edge['from'], edge['to']))
        
    # 노드 추가
    for node in nodes:
        node_id = node['id']
        category = node['category']
        size = node['size']
        
        # 선택된 노드 또는 관련 노드는 강조
        if highlighted_nodes and node_id in highlighted_nodes:
            if node_id == selected_node:
                # 선택된 노드 - 더 크고 빨간색 테두리
                color = {"background": "#FF5733", "border": "#FF0000", "highlight": {"background": "#FF5733", "border": "#FF0000"}}
                size = size * 1.5  # 크기 50% 증가
                font = {"color": "#000000", "size": 18, "face": "Arial", "bold": True}
            else:
                # 관련된 TOP 3 노드 - 약간 크고 다른 테두리
                color = {"background": "#FF9966", "border": "#FF0000", "highlight": {"background": "#FF9966", "border": "#FF0000"}}
                size = size * 1.2  # 크기 20% 증가
                font = {"color": "#000000", "size": 16, "face": "Arial", "bold": True}
        else:
            # 관련 없는 노드
            if highlighted_nodes:  # 선택된 노드가 있으면 흐리게
                color = {"background": category_colors.get(category, "#767676"), "border": "#aaaaaa", "highlight": {"background": category_colors.get(category, "#767676"), "border": "#aaaaaa"}}
                opacity = 0.2
                font = {"color": "#aaaaaa", "size": 14, "face": "Arial"}
            else:  # 선택된 노드가 없으면 일반 표시
                color = category_colors.get(category, "#767676")
                opacity = 1.0
                font = {"color": "#000000", "size": 14, "face": "Arial"}
        
        # 노드 추가 (x, y 좌표 지정)
        x = None
        y = None
        fixed = None
        
        # 세션 상태에 저장된 좌표가 있으면 사용
        positions = get_initial_positions()
        if node_id in positions:
            x = positions[node_id]['x']
            y = positions[node_id]['y']
            fixed = True  # 노드 위치 고정
        
        # 노드 추가
        net.add_node(
            node_id,
            label=node['label'],
            title=node['title'],
            size=size,
            color=color if isinstance(color, dict) else {"background": color, "border": color},
            font=font,
            x=x,
            y=y,
            fixed=fixed
        )
        
        # 투명도 설정 (하이라이트 효과)
        if highlighted_nodes and node_id not in highlighted_nodes:
            net.node_map[node_id]['opacity'] = 0.2
    
    # 엣지 추가
    for edge in edges:
        from_node = edge['from']
        to_node = edge['to']
        value = edge['value']
        title = edge['title']
        
        # 연관 강도에 따른 선 굵기 계산
        max_width = 10
        min_width = 1
        max_value = max(e['value'] for e in edges) if edges else 1
        min_value = min(e['value'] for e in edges) if edges else 0
        
        # 선형 스케일링
        if max_value > min_value:
            width = min_width + (value - min_value) / (max_value - min_value) * (max_width - min_width)
        else:
            width = min_width
        
        # 선택된 엣지 강조
        if highlighted_edges and (from_node, to_node) in highlighted_edges or (to_node, from_node) in highlighted_edges:
            color = {"color": "#FF0000", "opacity": 1.0}
            width = width * 2  # 선 두께 2배
        else:
            if highlighted_nodes:  # 선택된 노드가 있으면 흐리게
                color = {"color": "#dddddd", "opacity": 0.2}
            else:  # 선택된 노드가 없으면 일반 표시
                color = {"color": "#666666", "opacity": 0.7}
        
        net.add_edge(
            from_node,
            to_node,
            title=title,
            width=width,
            arrows='',  # 화살표 없음
            color=color
        )
    
    # 물리 엔진 설정 (JSON 형식으로 올바르게 전달)
    physics_options = {
      "physics": {
        "enabled": True,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
            "gravitationalConstant": -10,  # 중력 상수를 더 작게
            "centralGravity": 0.005,        # 중앙 중력 매우 약하게
            "springLength": 150,            # 노드 간 거리 
            "springConstant": 0.02,         # 스프링 강도 매우 약하게
            "damping": 0.9,                 # 감쇠 높게 (움직임 제한)
            "avoidOverlap": 0.5             # 노드 겹침 방지
        },
        "maxVelocity": 20,                  # 최대 속도 낮춤
        "minVelocity": 0.1,                 # 최소 속도 낮춤
        "stabilization": {
            "enabled": True,
            "iterations": 500,              # 안정화 반복 횟수 줄임
            "updateInterval": 100,          # 업데이트 간격 늘림
            "onlyDynamicEdges": False,
            "fit": True
        }
      },
        "nodes": {
            "shape": "dot",
            "font": {
                "size": 14,
                "face": "Arial"
            },
            "fixed": {
                "x": False,
                "y": False
            }
        },
        "edges": {
            "smooth": {
                "enabled": True,
                "type": "dynamic",
                "roundness": 0.5
            }
        },
        "interaction": {
            "hover": True,
            "dragNodes": True,
            "dragView": True,
            "zoomView": True,
            #"navigationButtons": true,
            "hoverConnectedEdges": True,       # 연결된 엣지 하이라이트
            "multiselect": True,               # 다중 선택 가능
            "tooltipDelay": 100
        },
        "layout": {
            "improvedLayout": True,
            "randomSeed": 42  # 항상 같은 초기 레이아웃 사용
        }
    }
    
    # 옵션 적용 (JSON 문자열로 변환)
    net.set_options(json.dumps(physics_options))
    
    # 노드 위치를 저장하는 스크립트
    position_script = """
    <script>
    // 네트워크 안정화 완료 후 모든 노드 위치 저장
    network.on("stabilizationIterationsDone", function() {
        // 물리 엔진 비활성화 (레이아웃이 더 이상 움직이지 않도록)
        network.setOptions({physics: {enabled: true}});
        
        // 모든 노드 위치 가져오기
        var positions = network.getPositions();
        
        // 위치 정보 저장 (로컬 스토리지)
        localStorage.setItem('networkPositions', JSON.stringify(positions));
    });
    
    // 노드 드래그 후 새 위치 저장
    network.on("dragEnd", function(params) {
        if (params.nodes.length > 0) {
            // 저장된 위치 정보 불러오기
            var positions = JSON.parse(localStorage.getItem('networkPositions') || '{}');
            
            // 드래그된 노드의 새 위치 가져오기
            var draggedNode = params.nodes[0];
            var nodePosition = network.getPosition(draggedNode);
            
            // 위치 정보 업데이트
            positions[draggedNode] = nodePosition;
            
            // 업데이트된 위치 정보 저장
            localStorage.setItem('networkPositions', JSON.stringify(positions));
        }
    });
    
    // 저장된 위치 정보 불러오기
    var savedPositions = localStorage.getItem('networkPositions');
    if (savedPositions) {
        var positions = JSON.parse(savedPositions);
        // 각 노드의 위치 고정
        for (var nodeId in positions) {
            network.moveNode(nodeId, positions[nodeId].x, positions[nodeId].y);
        }
    }
    </script>
    """
    
    # 그래프 생성 및 표시
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp_file:
        path = tmp_file.name
        net.save_graph(path)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                html = f.read()
                # 노드 위치 저장 스크립트 추가
                html = html.replace('</body>', f'{position_script}</body>')
                components.html(html, height=700)
        finally:
            os.unlink(path)
    
    # 선택된 노드가 있을 경우 관련 정보 표시
    if selected_node and selected_node in top_connections:
        st.subheader(f"'{selected_node}'와 가장 연관성이 높은 키워드")
        
        related_keywords = top_connections[selected_node][:6]  # TOP 6로 변경
        related_strengths = conn_strengths[selected_node]
        
        # 관련 키워드 카드형 표시
        cols = st.columns(6)  # 컬럼도 6개로 변경
        for i, keyword in enumerate(related_keywords):
            with cols[i]:
                strength = related_strengths.get(keyword, 0)
                
                st.markdown(
                    f"""
                    <div style="
                        background-color: #CFE9E5; 
                        padding: 20px; 
                        border-radius: 10px; 
                        border-left: 5px solid #004b2b;
                        margin: 10px 5px;
                        text-align: center;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    ">
                        <div style="font-size: 22px; font-weight: bold; color: #004b2b; margin-bottom: 10px;">{keyword}</div>
                        <div style="font-size: 16px; color: #004b2b;">연관 강도: <span style="font-weight: bold;">{strength:.1f}</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

if __name__ == "__main__":
    main()