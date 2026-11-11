# 아메리칸 맥기의 앨리스 (American McGee's Alice, PS3) 한글 패치

> **내려받기:** [릴리즈 페이지](https://github.com/hospi0/alice1-kr-patch/releases/latest)에서 받을 수 있고, 최신 판은 v0.9입니다.
> 「앨리스 매드니스 리턴즈」 북미 디스크판(BLUS30607)에 딸린 1편 DLC용입니다. **RPCS3 전용**입니다.
> 적용 방법과 원본 MD5는 묶음 안의 readme.txt에 있습니다.
>
> 이 저장소에는 도구, 번역 텍스트, 작업 문서만 있습니다. 게임 데이터와 빌드 결과물은 없습니다.
> 2편 한글 패치는 [hospi0/alice2-kr-patch](https://github.com/hospi0/alice2-kr-patch)에 있습니다.

## 적용

1. zip을 풉니다.
2. `한글패치_적용.bat`을 실행합니다.
3. 첫 질문에 RPCS3 폴더(rpcs3.exe가 있는 곳)를, 둘째 질문에 게임(디스크) 폴더를 끌어다 놓습니다.
4. 배치가 아래 순서로 처리합니다.
   - 실행 파일: 원본 MD5 확인 → 원본 백업 → RPCS3 `--decrypt`로 복호화 → xdelta 적용 → 결과 MD5 확인
   - DLC 메뉴 파일 7개: xdelta 적용
   - `pak9_korean.pk3`: DLC 폴더에 넣음

되돌릴 때는 `되돌리기.bat`을 씁니다.

## 바뀌는 것

- 음성 대사 자막 전부(848줄)
- 메뉴, 설정, 조작, 불러오기/저장, 장 이름
- 저장, 불러오기, 새 게임 확인창 문구(실행 파일 안)
- 한글 글꼴(고운바탕 Bold): 엔진의 1바이트 글꼴(256칸)에 CP949 2바이트 한글 그리기를 덧붙였습니다.

그림으로 된 제목 글씨, 엔딩 크레딧, XMB 저장 데이터 이름은 영어 그대로입니다.

## 구조

| 경로 | 내용 |
|---|---|
| `tools/ps3pkg.py` | DLC pkg 풀기 |
| `tools/extract.py` | tlk 자막과 urc/scr 메뉴 추출 |
| `tools/merge_ko.py` | 번역 병합과 검사(글꼴 밖 글자 막기, 표기 치환) → `work/text/ko.tsv` |
| `tools/build_font.py` | 2048 텍스처에 한글 2,350자를 넣은 ritualfont |
| `tools/patch_elf.py` | 실행 파일 훅(그리기, 문자열 폭, 줄바꿈 폭) |
| `tools/sysmsg.py` | 실행 파일 안 확인창 문구 |
| `tools/build.py` | 빌드 → pak9_korean.pk3, INT urc, 한글 ELF |
| `tools/make_dist.py` | 배포 묶음(xdelta와 bat) |
| `docs/` | 조사 기록, 용어표(2편과 통일), 인물별 말투표 |
| `work/text/ko.tsv` | 번역(번호, 위치, EN, KO) |
| `work/ko/` | 다듬기 수정분, 확인창 번역 |

글꼴: [고운바탕](https://github.com/yangheeryu/Gowun-Batang) (SIL Open Font License 1.1)
