import os
import requests
import pandas as pd
from tqdm import tqdm
import json
from pathlib import Path

from langchain_core.documents import Document
from collections import defaultdict


oc = os.getenv('OC', '')

df = pd.read_csv("data/법령검색목록_자치법규_건축.csv", skiprows=1)

def load_documents_from_jsonl(file_path):
    """
    JSONL 파일에서 Document 객체 리스트를 불러옵니다.
    
    Args:
        file_path: JSONL 파일 경로
        
    Returns:
        List[Document]: Document 객체 리스트
    """
    documents = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            # 빈 줄 건너뛰기
            if not line.strip():
                continue
                
            # JSON 파싱
            data = json.loads(line)
            
            # Document 객체 생성
            doc = Document(
                page_content=data["page_content"],
                metadata=data["metadata"],
                id=data["id"]
            )
            documents.append(doc)
    
    print(f"✅ 총 {len(documents)}개 Document 불러오기 완료")
    return documents

def save_documents(documents, file_path):
    """
    Document 리스트를 JSONL 파일로 저장합니다.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        for doc in documents:
            json.dump({
                "id": doc.id,
                "page_content": doc.page_content,
                "metadata": doc.metadata
            }, f, ensure_ascii=False)
            f.write("\n")
    print(f"✅ {len(documents)}개 Document를 {file_path}에 저장 완료")

def extract_clause_documents(df, oc, chain_abb, chain, checkpoint_dir="checkpoints"):
    """
    조항별로 메타데이터를 추출하여 Document 리스트를 생성합니다.
    중간 저장 기능 포함.
    """
    # 체크포인트 디렉토리 생성
    Path(checkpoint_dir).mkdir(exist_ok=True)
    
    # 이미 처리된 법규 ID 확인
    processed_ids = set()
    checkpoint_file = os.path.join(checkpoint_dir, "processed_ids.txt")
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            processed_ids = set(line.strip() for line in f)
        print(f"✅ 이미 처리된 법규: {len(processed_ids)}개")
    
    documents = []
    
    # 기존 documents.jsonl이 있으면 로드
    if os.path.exists("documents.jsonl"):
        print("기존 documents.jsonl 로드 중...")
        documents = load_documents_from_jsonl("documents.jsonl")
        print(f"✅ 기존 문서의 조항 리스트 {len(documents)}개 로드 완료")
    
    # 처리할 법규만 필터링
    # total_laws = len(df["자치법규ID"])
    df_law_ids = [str(id) for id in df["자치법규ID"]]
    laws_to_process = [id for id in df_law_ids if id not in processed_ids]
    
    if not laws_to_process:
        print("✅ 모든 법규가 이미 처리되었습니다.")
        return documents

    print(f"🔄 처리할 법규: {len(laws_to_process)}개 (전체 {len(df_law_ids)}개 중)")

    for id in tqdm(laws_to_process, desc="법규 처리"):
        # try:
        url = f"http://www.law.go.kr/DRF/lawService.do?OC={oc}&target=ordin&ID={id}&type=JSON"
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        meta = data["LawService"]["자치법규기본정보"]
        content = data["LawService"]["조문"]["조"]

        # --- 조문별 텍스트 추출 ---
        ctx_list = []
        ctx_without_tt = []
        header = ""
        
        for ctx in content:
            if ctx["조문여부"] == "Y":
                txt = header + " " + ctx["조내용"]
                txt = txt.strip()
                ctx_list.append(txt)
                
                if ctx["조내용"].find(")") != -1:
                    ctx_without_tt.append(ctx["조내용"][ctx["조내용"].find(")")+1:].strip())
                else:
                    ctx_without_tt.append(ctx["조내용"])
            else:
                header = "[" + ctx["조내용"] + "]"
        # print(f"  현재 법령의 총 조항 개수: {len(ctx_list)}")
        # --- 약어 추출 ---
        abb = {}
        clause_abb_list = []  # 각 조항의 약어를 저장
        for i, item in enumerate(ctx_list):
            if "이하" in item:
                print(f"  🔤 약어 추출 중... ({i+1}/{len(ctx_list)})", end='\r')
                q = ctx_without_tt[i]
                abb_output = chain_abb.invoke({"question": q})
                
                filtered_abb = {
                    k: v for k, v in abb_output.items()
                    if (k in ["약어", ""] and v) or (k not in ["약어", ""])
                }
                abb.update(filtered_abb)
            else:
                filtered_abb = {}
            # print(f"약어: {filtered_abb}")
            clause_abb_list.append(filtered_abb)

        # --- 조항별 Document 생성 ---
        cnt = 1
        law_documents = []  # 현재 법규의 문서들
        
        for i, item in enumerate(ctx_list):
            print(f" 🔗 links 추출 중... ({i+1}/{len(ctx_list)})", end='\r')
            chunk = (
                item
            )

            q = "법률 문서의 내용은 다음과 같습니다: " + ctx_without_tt[i]
            links_llm = chain.invoke({"abb": abb, "question": q})

            filtered_links = {
                k: v for k, v in links_llm.items()
                if (k in ["기타", "법률 문서 제목"] and v) or (k not in ["기타", "법률 문서 제목"])
            }

            # --- 메타데이터 생성 ---
            doc_meta = meta.copy()
            doc_meta["약어"] = clause_abb_list[i]
            if filtered_links:
                doc_meta["links"] = [filtered_links]

            # --- Document 객체 생성 ---
            doc = Document(
                page_content=chunk,
                metadata=doc_meta,
                id=f"{meta['자치법규ID']}_clause_{cnt}"
            )
            cnt += 1
            law_documents.append(doc)
        
        # 현재 법규 문서들을 전체 리스트에 추가
        documents.extend(law_documents)
        
        # 처리 완료된 ID 기록
        processed_ids.add(id)
        with open(checkpoint_file, "a", encoding="utf-8") as f:
            f.write(f"{id}\n")
        
        # 10개 법규마다 중간 저장
        # if len(processed_ids) % 10 == 0:
        save_documents(documents, "documents.jsonl")
        # print(f"\n💾 중간 저장: {len(documents)}개 문서, {len(processed_ids)}개 법규 처리 완료")
    
        # except Exception as e:
        #     print(f"\n❌ 오류 발생 (법규 ID: {id}): {str(e)}")
        #     # 오류 로그 저장
        #     with open(os.path.join(checkpoint_dir, "error_log.txt"), "a", encoding="utf-8") as f:
        #         f.write(f"{id}: {str(e)}\n")
        #     continue

    # 최종 저장
    save_documents(documents, "documents.jsonl")
    print(f"\n✅ 최종 저장: {len(documents)}개 문서 완료")
    
    return documents

def merge_documents_by_chapter(documents, min_len=300, max_len=600, 
                               checkpoint_dir="checkpoints", batch_size=1):
    """
    조항별 Document를 장 단위로 병합하여 적절한 크기의 청크를 생성합니다.
    중간 저장 기능 포함.
    """
    # 체크포인트 디렉토리 생성
    Path(checkpoint_dir).mkdir(exist_ok=True)
    
    # 이미 병합된 문서가 있으면 로드
    merged_docs = []
    if os.path.exists("documents_merged.jsonl"):
        print("기존 documents_merged.jsonl 로드 중...")
        merged_docs = load_documents_from_jsonl("documents_merged.jsonl")
        print(f"✅ 기존 병합 문서 청크 리스트{len(merged_docs)}개 로드 완료")
    
    # 이미 처리된 법규 ID 확인
    processed_law_ids = set()
    merge_checkpoint_file = os.path.join(checkpoint_dir, "merged_law_ids.txt")
    if os.path.exists(merge_checkpoint_file):
        with open(merge_checkpoint_file, "r", encoding="utf-8") as f:
            processed_law_ids = set(line.strip() for line in f if line.strip())
        print(f"✅ 이미 병합된 법규: {len(processed_law_ids)}개")
    
    # 1️⃣ Document들을 자치법규ID 기준으로 그룹화
    docs_by_law = defaultdict(list)
    for doc in documents:
        law_id = str(doc.metadata.get("자치법규ID"))
        if law_id not in processed_law_ids:
            docs_by_law[law_id].append(doc)
    
    if not docs_by_law:
        print("✅ 모든 법규가 이미 병합되었습니다.")
        return merged_docs

    # 2️⃣ 각 법령 문서별로 처리
    total_laws = len(docs_by_law)
    processed_count = 0
    
    print(f"🔄 병합할 법규: {total_laws}개")
    
    for law_id, doc_list in tqdm(docs_by_law.items(), desc="법령별 병합"):
        try:
            # ID를 숫자 기준으로 정렬 (2019610_clause_1, 2019610_clause_2, ...)
            def extract_clause_number(doc):
                # ID 형식: "2019610_clause_1"
                parts = doc.id.split("_")
                if len(parts) >= 3:
                    try:
                        return int(parts[2])  # clause 번호
                    except:
                        return 0
                return 0
            
            doc_list = sorted(doc_list, key=extract_clause_number)
            base_meta = {k: v for k, v in doc_list[0].metadata.items() 
                         if k not in ["links", "약어"]}

            # 3️⃣ 장별로 그룹화
            chapters = []
            current_chapter = []
            current_header = ""
            
            for doc in doc_list:
                content = doc.page_content
                
                # 장 헤더 추출: [제1장 총칙] 형태
                header = ""
                if content.startswith("[") and "]" in content:
                    # 첫 번째 ']'까지가 장 헤더
                    end_idx = content.find("]")
                    potential_header = content[:end_idx+1]
                    # "제1장", "제2장" 같은 패턴이 있으면 장 헤더로 인식
                    if "장" in potential_header or "편" in potential_header:
                        header = potential_header
                
                # 헤더가 바뀌면 새 장 시작
                if header and header != current_header:
                    if current_chapter:
                        chapters.append({
                            "header": current_header,
                            "docs": current_chapter
                        })
                    current_header = header
                    current_chapter = [doc]
                else:
                    current_chapter.append(doc)
            
            # 마지막 장 추가
            if current_chapter:
                chapters.append({
                    "header": current_header,
                    "docs": current_chapter
                })

            # 4️⃣ 각 장별로 청크 생성
            for chapter_idx, chapter in enumerate(chapters, start=1):
                지자체기관명 = base_meta.get("지자체기관명", "")
                자치법규명 = base_meta.get("자치법규명", "")
                
                # 장 헤더가 있으면 포함
                if chapter["header"]:
                    base_header = f"[{지자체기관명} | {자치법규명}]\n{chapter['header']}"
                else:
                    base_header = f"[{지자체기관명} | {자치법규명}]"
                
                buffer = base_header
                merged_links_dict = defaultdict(set)
                merged_abb = {}
                chunk_id = 1
                
                for doc in chapter["docs"]:
                    content = doc.page_content
                    
                    # 장 헤더 제거 (조문 내용만 추출)
                    text = content
                    if content.startswith("[") and "]" in content:
                        # [제1장 총칙] 제1조... 형태에서 제1조... 부분만 추출
                        end_idx = content.find("]")
                        potential_header = content[:end_idx+1]
                        # 장 헤더인 경우에만 제거
                        if "장" in potential_header or "편" in potential_header:
                            text = content[end_idx+1:].strip()
                    
                    # 링크 병합
                    links_list = doc.metadata.get("links", [])
                    for links in links_list:
                        for key, values in links.items():
                            if isinstance(values, list):
                                merged_links_dict[key].update(values)
                            else:
                                merged_links_dict[key].add(values)
                    
                    # 약어 병합
                    abb = doc.metadata.get("약어", {})
                    merged_abb.update(abb)
                    
                    # 버퍼에 추가할지 결정
                    potential_length = len(buffer) + len(text) + 1
                    
                    if potential_length <= max_len:
                        buffer += f"\n{text}"
                    else:
                        # 현재 버퍼가 min_len 미만이면 강제로 추가
                        if len(buffer) < min_len:
                            buffer += f"\n{text}"
                        else:
                            # 현재 버퍼로 Document 생성
                            merged_doc = create_merged_document(
                                law_id=law_id,
                                chapter_idx=chapter_idx,
                                chunk_id=chunk_id,
                                content=buffer.strip(),
                                base_meta=base_meta,
                                links_dict=merged_links_dict,
                                abb=merged_abb
                            )
                            merged_docs.append(merged_doc)
                            
                            # 새 버퍼 시작
                            chunk_id += 1
                            buffer = base_header + f"\n{text}"
                            merged_links_dict = defaultdict(set)
                            merged_abb = {}
                            
                            # 현재 조항의 링크와 약어 추가
                            for links in links_list:
                                for key, values in links.items():
                                    if isinstance(values, list):
                                        merged_links_dict[key].update(values)
                                    else:
                                        merged_links_dict[key].add(values)
                            merged_abb.update(abb)
                
                # 마지막 버퍼 처리
                if len(buffer.strip()) > len(base_header.strip()):
                    merged_doc = create_merged_document(
                        law_id=law_id,
                        chapter_idx=chapter_idx,
                        chunk_id=chunk_id,
                        content=buffer.strip(),
                        base_meta=base_meta,
                        links_dict=merged_links_dict,
                        abb=merged_abb
                    )
                    merged_docs.append(merged_doc)
            
            # 처리 완료된 법규 ID 기록
            processed_law_ids.add(str(law_id))
            with open(merge_checkpoint_file, "a", encoding="utf-8") as f:
                f.write(f"{str(law_id)}\n")
            
            processed_count += 1
            
            # batch_size개 법규마다 중간 저장
            if processed_count % batch_size == 0:
                save_documents(merged_docs, "documents_merged.jsonl")
                # print(f"\n💾 중간 저장: {len(merged_docs)}개 병합 문서, {processed_count}/{total_laws}개 법규 처리 완료")
        
        except Exception as e:
            print(f"\n❌ 병합 오류 (법규 ID: {law_id}): {str(e)}")
            import traceback
            print(traceback.format_exc())
            # 오류 로그 저장
            with open(os.path.join(checkpoint_dir, "merge_error_log.txt"), "a", encoding="utf-8") as f:
                f.write(f"{law_id}: {str(e)}\n{traceback.format_exc()}\n")
            continue

    # 최종 저장
    save_documents(merged_docs, "documents_merged.jsonl")
    print(f"\n✅ 최종 병합 저장: {len(merged_docs)}개 문서 완료")
    
    return merged_docs

def create_merged_document(law_id, chapter_idx, chunk_id, content, base_meta, links_dict, abb):
    """
    병합된 Document 객체를 생성합니다.
    """
    metadata = base_meta.copy()
    
    # links 정리 (set을 list로 변환)
    if links_dict:
        metadata["links"] = [{k: sorted(list(v)) for k, v in links_dict.items()}]
    
    # 약어 추가
    if abb:
        metadata["약어"] = abb
    
    doc = Document(
        page_content=content,
        metadata=metadata,
        id=f"{law_id}_chapter{chapter_idx}_chunk{chunk_id}"
    )
    
    return doc

def save_documents(documents, file_path):
    """
    Document 리스트를 JSONL 파일로 저장합니다.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        for doc in documents:
            json.dump({
                "id": doc.id,
                "page_content": doc.page_content,
                "metadata": doc.metadata
            }, f, ensure_ascii=False)
            f.write("\n")

def load_documents_from_jsonl(file_path):
    """
    JSONL 파일에서 Document 객체 리스트를 불러옵니다.
    """
    documents = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
                
            data = json.loads(line)
            doc = Document(
                page_content=data["page_content"],
                metadata=data["metadata"],
                id=data["id"]
            )
            documents.append(doc)
    
    return documents

# ====== Prompt ==================================================================
# ================================================================================
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

model = ChatOllama(
    model="gpt-oss:120b-cloud",
    temperature=0.1,
    max_tokens = 1024,
    timeout=None,
    max_retries=2,
    reasoning = None,
)

system_message = """당신은 법률 문서 전문을 분석하여, 그 안에서 명시적으로 **참고해야 하는 다른 법률 문서와 해당 조항 번호**를 추출해야 합니다.

아래의 원칙을 반드시 지키세요:
1. 반드시 문서 내용에 명시적으로 등장한 법률명 또는 조항만 추출합니다.
2. 법률명이 명확히 언급되지 않은 경우, 절대 추측하지 않습니다.
3. 조항 번호나 별표만 언급된 경우, 해당 항목은 "기타" key에 넣습니다.
4. 출력은 반드시 **유효한 JSON 형식**으로 반환합니다 (파싱 가능한 구조).

다음은 약어와 실제 명칭입니다. 법률 문서 제목이나 조항명이 약어로 명시되어있는 경우, 실제 명칭으로 변환하여 반환하세요.
{abb}

출력 형식:
  "법률 문서 제목": ["관련 조항 번호", "..."],
  "기타": ["별표", "조항 번호", "..."]

주의:
- 각 리스트가 비어있다면 빈 배열([])로 반환합니다.
- 설명 문구, 해석, 자연어 문장은 절대 포함하지 마세요.
- "같은 법" 이나 "동법" 등의 표현은 실제 법률명으로 대체하세요.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_message),
    ("user", "{question}")
])

# 일반 Chain 생성
chain = prompt | model | JsonOutputParser()

model_abb = ChatOllama(
    model="gpt-oss:120b-cloud",
    temperature=0.1,
    max_tokens = 1024,
    timeout=None,
    max_retries=2,
    reasoning = None,
)

system_message_abb = """당신은 법률 문서 전문을 분석하여, 그 안에서 약어(또는 축약어)의 **원래 의미**를 추출해야 합니다.

아래의 원칙을 반드시 지키세요:
1. 반드시 문서 내용에 **명시적으로 등장한 약어 또는 축약어만** 추출합니다.
2. 약어가 정의되지 않은 경우, 절대 추측하지 않습니다.
3. 약어가 정의된 문장은 보통 “(이하 ‘~’이라 한다)” 또는 “(이하 ‘~’라 한다)” 형태로 나타납니다.
4. 약어의 원래 의미에는 다음 요소들이 포함될 수 있습니다:
   - 관련 법령, 조항 번호, 시행령/시행규칙
   - “에 따라”, “에 의한”, “이 정하여 고시하는”, “으로 정하는”, “에서 규정한” 등의 조건문
   - 문장 속 수식어, 제약 조건 등
   이러한 조건은 **절대 생략하지 말고 그대로 포함하세요.**
5. 정의 구문에 "다만", "단서", "예외" 등이 이어지는 경우, 해당 조건도 실제 명칭에 반드시 포함합니다.
6. 출력은 반드시 **파싱 가능한 JSON 형식**으로 반환해야 합니다.

출력 형식:
  "약어": "원래 의미"

- 예시 1:
입력:
"제3조(정의) 이 조례에서 사용하는 용어의 뜻은 「건축물관리법」(이하 “법”이라 한다) 및 「건축법」에서 정하는 바에 따른다."

출력:
  "법": "건축물관리법"

- 예시 2:
입력:
"법 제42조제1항(단서 부분은 제외한다)에 따라 200제곱미터 이상인 대지에 건축을 하는 건축주는 다음 각 호의 어느 하나에 해당하는 조경면적(이하 “조경의무면적”이라 한다)에 법 제42조제2항에 따라 국토교통부장관이 고시하는 조경기준(이하 “조경기준”이라 한다)에 따라 조경의 조치를 하여야 한다. 다만, 다음 각 호의 기준보다 영 제27조제2항 각 호의 기준이 더 완화된 경우에는 그 기준에 따른다. <개정 2009.12.9., 2017.11.9.>1. 연면적(대지에 둘 이상의 건축물이 있는 경우에는 연면적의 합계로 한다. 이하 이 조에서 같다)이 2천제곱미터 이상인 건축물의 조경의무면적: 대지면적의 15퍼센트 이상2. 연면적이 1천제곱미터 이상 2천제곱미터 미만인 건축물의 조경의무면적 : 대지면적의 10퍼센트 이상3. 연면적이 1천제곱미터 미만인 건축물의 조경의무면적 : 대지면적의 5퍼센트 이상② 조경기준 제4조와 제5조제1항 및 제12조에서 정하는 조경면적 산정기준이나 조경면적의 배치기준에 따라 산정한 면적을 제1항에 따른 조경의무면적으로 산정한다. 다만, 다음 각 호에서 정하는 경우에는 그 기준에 따라 산정한 면적만을 조경의무면적으로 산정하되 조경의무면적의 2분의 1을 초과할 수 없다."

출력:
  "조경의무면적": "법 제42조제1항(단서 부분은 제외한다)에 따라 200제곱미터 이상인 대지에 건축을 하는 건축주는 다음 각 호의 어느 하나에 해당하는 조경면적에 법 제42조제2항에 따라 국토교통부장관이 고시하는 조경기준에 따라 조경의 조치를 하여야 하나, 다만 다음 각 호의 기준보다 영 제27조제2항 각 호의 기준이 더 완화된 경우에는 그 기준에 따른다.",
  "조경기준": "법 제42조제2항에 따라 국토교통부장관이 고시하는 조경기준"

출력 규칙 (매우 중요):
- 반드시 유효한 JSON 형식으로만 출력합니다. 코드블록(````), 주석(`//`, `/* */`), 설명문, 기타 텍스트를 포함하지 마세요.
- 약어가 전혀 없을 경우에는 정확히 빈 JSON 객체만 출력하세요.
 """

prompt_abb = ChatPromptTemplate.from_messages([
    ("system", system_message_abb),
    ("user", "{question}")
])

# 일반 Chain 생성
chain_abb = prompt_abb | model_abb | JsonOutputParser()


# --- 메인 실행 ---
if __name__ == "__main__":
    # 1단계: 조항별 메타데이터 추출
    print("=" * 50)
    print("1단계: 조항별 메타데이터 추출 중...")
    print("=" * 50)
    clause_documents = extract_clause_documents(df, oc, chain_abb, chain)
    print(f"\n✅ 조항별 문서 {len(clause_documents)}개 완료")

    # 2단계: 장별 병합
    print("\n" + "=" * 50)
    print("2단계: 장별 병합 중...")
    print("=" * 50)
    merged_documents = merge_documents_by_chapter(
        clause_documents, 
        min_len=300, 
        max_len=600,
        batch_size=100  # 100개 법규마다 저장
    )
    print(f"\n✅ 병합 문서 {len(merged_documents)}개 완료")

    print("\n" + "=" * 50)
    print("🎉 모든 작업 완료!")
    print(f"조항별 문서: {len(clause_documents)}개 → documents.jsonl")
    print(f"병합 문서: {len(merged_documents)}개 → documents_merged.jsonl")
    print("=" * 50)