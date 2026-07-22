Free-Space S-Parameter Analyzer (Mode 1)
=========================================

구성 파일
---------
- s2p_calc.py   : 핵심 계산 로직 (s2p 파싱 + 전체 EM 물성 계산)
- s2p_gui.py    : GUI 실행 파일 (이 파일을 실행)

파이썬으로 바로 실행하는 방법 (Windows, macOS, Linux 공통)
-----------------------------------------------------------
1) Python 3.9 이상 설치 (https://www.python.org/downloads/)
   설치 시 "Add Python to PATH" 체크

2) 필요한 라이브러리 설치 (명령 프롬프트/터미널에서):
   pip install numpy pandas

3) 실행:
   python s2p_gui.py

   -> GUI 창이 뜨면 "찾아보기"로 .s2p 파일 선택, 두께(mm) 입력 후
      "확인" 버튼 클릭 -> 결과 CSV 저장 위치 지정

Windows용 .exe 만드는 방법 A) 직접 Windows PC에서 빌드
----------------------------------------------------
1) 위 1), 2)번까지 동일하게 진행

2) PyInstaller 설치:
   pip install pyinstaller

3) 아래 폴더(두 .py 파일이 있는 위치)에서 명령 프롬프트 실행 후:
   pyinstaller --onefile --noconsole --name S2P_Analyzer s2p_gui.py

4) 빌드 완료 후 dist 폴더 안에 S2P_Analyzer.exe 생성됨
   (이 파일 하나만 배포/실행하면 됩니다. GUI 창이 뜹니다.)


Windows용 .exe 만드는 방법 B) GitHub Actions로 자동 빌드 (Windows PC 없이 가능)
------------------------------------------------------------------------------
이 폴더에는 이미 .github/workflows/build.yml 이 포함되어 있어,
GitHub에 올리기만 하면 자동으로 Windows 환경에서 exe를 빌드해줍니다.

1) github.com 에서 새 저장소(Repository) 생성
   - 이름 예: s2p-analyzer
   - Public/Private 상관없음 (Private도 Actions 무료 사용 가능, 계정 종류에 따라 월 한도 있음)
   - README 등 추가 파일 없이 "Create repository"만 클릭

2) 이 폴더(README.txt가 있는 폴더) 전체를 저장소에 업로드
   방법 1 - 웹 브라우저에서 드래그 앤 드롭:
     저장소 페이지 -> "Add file" -> "Upload files" -> 이 폴더 안의
     모든 파일(.github 폴더 포함, 폴더째로 드래그 가능)을 끌어다 놓고
     "Commit changes" 클릭

   방법 2 - git 명령어 사용:
     git init
     git add .
     git commit -m "initial commit"
     git branch -M main
     git remote add origin https://github.com/사용자명/저장소명.git
     git push -u origin main

   * 반드시 .github/workflows/build.yml 파일이 저장소 루트 기준
     .github/workflows/ 경로 그대로 들어가야 합니다 (구조가 깨지지
     않도록 폴더째로 업로드하세요).

3) 업로드(push) 하면 자동으로 빌드가 시작됩니다.
   저장소 상단 메뉴 "Actions" 탭 클릭 -> "Build Windows EXE" 워크플로우
   실행 중/완료 확인 (보통 1~3분 소요)
   * 자동으로 안 돌아가면 Actions 탭 -> 좌측 "Build Windows EXE" 선택
     -> 우측 "Run workflow" 버튼으로 수동 실행 가능

4) 빌드 완료 후 해당 실행(run) 페이지 하단 "Artifacts" 항목에서
   "S2P_Analyzer_windows_exe" 다운로드 (zip 파일)
   -> 압축 풀면 S2P_Analyzer.exe 있음, 그대로 실행

주의사항
--------
- 입력 s2p 파일은 "# Hz S DB R 50" 형식(FREQ, S33_dB/ang, S43_dB/ang,
  S34_dB/ang, S44_dB/ang 순서, 공백 구분)만 지원합니다. 다른 포맷이면
  s2p_calc.py의 parse_s2p_free_space() 함수 수정이 필요합니다.
- NRW(유전율/투자율 추출) 계산은 시료가 "균질한 단일 슬래브"라는 가정
  하에 이루어집니다. LIG+PI+기타 다층 구조 전체를 하나로 넣으면
  "등가(effective) 물성"이 산출되며, 층별 개별 물성이 아닙니다.
- 결과 CSV의 'passivity_flag' 컬럼이 False인 행은 eps'' 또는 mu''가
  음수로 계산된 구간으로, 캘리브레이션/다층구조 영향으로 비물리적
  값이 나온 것일 수 있으니 해석 시 참고하세요.
- 위상 unwrap(연속화)을 이용해 NRW의 branch(2*pi*m) 모호성을 1차적으로
  완화했으나, 시료가 두껍거나 주파수 간격이 넓으면 완전히 해결되지
  않을 수 있습니다.
