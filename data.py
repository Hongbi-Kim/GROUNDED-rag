import requests
import os, re
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from dotenv import load_dotenv
load_dotenv()

oc = os.getenv('OC', '')

df = pd.read_csv("data/법령검색목록_법령_건축.csv", skiprows=1)

id = "001823"
url = f"http://www.law.go.kr/DRF/lawService.do?OC={oc}&target=eflaw&ID=001823&type=JSON"
response = requests.get(url)
response.raise_for_status()

data = response.json()

@dataclass
class ArticleChunk:
    """조 단위 chunk"""
    # 식별
    law_name: str                    # "건축법"
    law_id: str                      # "001823"
    article_num: str                 # "46"
    article_title: str               # "건축선의 지정"
    
    # 본문
    content: str                     # 항+호+목 플랫 결합 텍스트
    content_resolved: str = ""       # 축약어 치환 버전 (STEP 1-5에서 채움)
    
    # 계층 구조 보존 (metadata용)
    paragraphs: list = field(default_factory=list)
    # [
    #   {"num": "1", "content": "...", 
    #    "subs": [{"num": "1", "content": "...", 
    #              "items": [{"num": "가", "content": "..."}]}]}
    # ]
    
    # 참조 (STEP 1-4에서 채움)
    internal_refs: list = field(default_factory=list)
    external_refs: list = field(default_factory=list)
    parent_law_refs: list = field(default_factory=list)
    
    # 축약어맵 (STEP 1-3에서 채움)
    abbreviations: dict = field(default_factory=dict)
    
    # 메타
    effective_date: str = ""
    change_type: str = ""


def parse_law_data(data: dict) -> list[ArticleChunk]:
    """
    법령 API 응답 전체를 파싱하여 ArticleChunk 리스트 반환
    """
    law_info = data["법령"]["기본정보"]
    law_name = law_info["법령명_한글"]
    law_id = law_info["법령ID"]
    
    articles_raw = data["법령"]["조문"]["조문단위"]
    # article = articles_raw[0]
    chunks = []
    for article in articles_raw:
        chunk = parse_article(article, law_name, law_id)
        if chunk:
            chunks.append(chunk)


    return chunks


def parse_article(article: dict, law_name: str, law_id: str) -> ArticleChunk | None:
    """단일 조문을 ArticleChunk로 변환"""
    
    # 조문 여부 확인 (부칙 등 제외)
    if article.get("조문여부") != "조문":
        return None
    
    article_num = article.get("조문번호", "")
    article_title_raw = article.get("조문제목", "")
    article_header = article.get("조문내용", "")  # "제2조(정의)"
    
    # 항 파싱
    paragraphs_structured = []
    content_parts = [article_header]  # 플랫 텍스트 시작
    
    paragraphs_raw = normalize_to_list(article.get('항'))

    for para in paragraphs_raw:
        para_num = normalize_paragraph_num(para.get("항번호", ""))
        para_content = para.get("항내용", "")
        
        content_parts.append(para_content)
        
        subs_structured = []
        
        # 호 파싱
        for sub in para.get("호", []):
            sub_num = sub.get("호번호", "").strip().rstrip(".")
            sub_content = sub.get("호내용", "")
            
            content_parts.append(sub_content)
            
            items_structured = []
            
            # 목 파싱
            for item in sub.get("목", []):
                item_num = item.get("목번호", "").strip().rstrip(".")
                item_content = item.get("목내용", "")
                
                content_parts.append(item_content)
                items_structured.append({
                    "num": item_num,
                    "content": item_content
                })
            
            subs_structured.append({
                "num": sub_num,
                "content": sub_content,
                "items": items_structured
            })
        
        paragraphs_structured.append({
            "num": para_num,
            "content": para_content,
            "subs": subs_structured
        })

    # 플랫 텍스트 결합
    content = "\n".join(content_parts)
    
    return ArticleChunk(
        law_name=law_name,
        law_id=law_id,
        article_num=article_num,
        article_title=article_title_raw,
        content=content,
        paragraphs=paragraphs_structured,
        effective_date=article.get("조문시행일자", ""),
        change_type=article.get("조문제개정유형", ""),
    )


def normalize_paragraph_num(raw: str) -> str:
    """①②③... → 1, 2, 3..."""
    circled_map = {
        "①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5",
        "⑥": "6", "⑦": "7", "⑧": "8", "⑨": "9", "⑩": "10",
        "⑪": "11", "⑫": "12", "⑬": "13", "⑭": "14", "⑮": "15",
    }
    raw = raw.strip()
    return circled_map.get(raw, raw)

def normalize_to_list(value):
    """항/호/목이 dict로 올 수도, list로 올 수도, 없을 수도 있는 경우 처리"""
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return value
    return []

