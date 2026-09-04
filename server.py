import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

HTML_CONTENT = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>무제한 초코 경매</title>
  <style>
    :root {
      --choco-dark: #2c1810;
      --choco-milk: #533024;
      --gold: #d4af37;
      --cream: #fff8f0;
      --bg: #f4ede4;
      --danger: #d9534f;
      --success: #5cb85c;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
      background: var(--bg);
      color: var(--choco-dark);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 15px;
    }
    .container {
      width: 100%;
      max-width: 860px;
      background: #ffffff;
      border-radius: 18px;
      padding: 25px;
      box-shadow: 0 6px 20px rgba(44, 24, 16, 0.12);
      border: 2px solid #e8dbce;
    }
    h1, h2, h3 { text-align: center; }
    h1 { font-size: 2rem; margin-bottom: 20px; }
    .btn {
      background: var(--choco-milk);
      color: var(--cream);
      border: none;
      padding: 12px 24px;
      font-size: 1rem;
      font-weight: 700;
      border-radius: 10px;
      cursor: pointer;
    }
    .btn:hover { background: var(--choco-dark); }
    .btn-gold { background: var(--gold); color: var(--choco-dark); }
    .btn-danger { background: var(--danger); color: #fff; }
    input[type="text"], input[type="number"] {
      width: 100%;
      padding: 12px;
      font-size: 1.1rem;
      border: 2px solid #d4c5b9;
      border-radius: 8px;
      margin-bottom: 12px;
      text-align: center;
      outline: none;
    }
    .badge {
      display: inline-block;
      padding: 6px 14px;
      border-radius: 20px;
      background: var(--gold);
      color: var(--choco-dark);
      font-weight: bold;
    }
    .grid-teams {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
      margin: 15px 0;
    }
    .team-card {
      background: var(--cream);
      border: 2px solid #ecdac9;
      padding: 12px;
      border-radius: 10px;
      text-align: center;
      font-weight: bold;
    }
    .team-card.done {
      border-color: var(--success);
      background: #eafaf1;
      color: var(--success);
    }
    .timer-display {
      font-size: 3rem;
      font-weight: 900;
      color: var(--choco-milk);
      text-align: center;
      margin: 10px 0;
    }
    .banner {
      background: var(--choco-dark);
      color: var(--gold);
      padding: 18px;
      border-radius: 12px;
      text-align: center;
      margin: 15px 0;
      font-size: 1.3rem;
      font-weight: bold;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 10px; text-align: center; border-bottom: 1px solid #ebdcd0; }
    th { background: var(--cream); }
    .bankrupt { color: var(--danger); text-decoration: line-through; }
    .view { display: none; }
    .view.active { display: block; }
  </style>
</head>
<body>
  <div id="view-entry" class="container view active">
    <h1>🍫 무제한 초코 경매</h1>
    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
      <div style="flex: 1; min-width: 250px; background: var(--cream); padding: 20px; border-radius: 12px; text-align: center;">
        <h2>교사용 화면</h2>
        <p style="margin: 12px 0; color: #666;">교실 프로젝터용 방을 개설합니다.</p>
        <button class="btn" onclick="initTeacher()">게임방 만들기</button>
      </div>
      <div style="flex: 1; min-width: 250px; background: var(--cream); padding: 20px; border-radius: 12px; text-align: center;">
        <h2>학생 모둠 화면</h2>
        <p style="margin: 12px 0; color: #666;">방 코드와 모둠명을 입력합니다.</p>
        <input type="text" id="join-code" placeholder="방 코드 4자리" maxlength="4" />
        <input type="text" id="join-team" placeholder="모둠 이름 (예: 1모둠)" maxlength="10" />
        <button class="btn btn-gold" onclick="joinStudent()">대기실 입장</button>
      </div>
    </div>
  </div>

  <div id="view-teacher" class="container view">
    <div id="t-lobby">
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ecdac9; padding-bottom: 10px;">
        <h2>🍫 초코 경매장 대기실</h2>
        <div>입장 코드: <span id="t-room-code" class="badge" style="font-size: 1.6rem;">0000</span></div>
      </div>
      <h3 style="margin-top: 20px; text-align: left;">접속 모둠 (<span id="t-team-count">0</span>)</h3>
      <div class="grid-teams" id="t-teams-list"></div>
      <div style="text-align: center; margin-top: 20px;">
        <button class="btn btn-gold" style="font-size: 1.2rem; padding: 14px 36px;" onclick="sendWS('START_GAME', {})">게임 시작</button>
      </div>
    </div>

    <div id="t-round" style="display: none;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span id="t-round-idx" class="badge">Round 1 / 12</span>
        <span id="t-round-item" style="font-size: 1.6rem; font-weight: 900;">초콜릿</span>
        <span id="t-round-point" class="badge" style="background: var(--choco-milk); color: #fff;">+1점</span>
      </div>
      <div class="timer-display" id="t-timer">02:00</div>
      <div style="text-align: center; margin-bottom: 15px;">
        <button class="btn" onclick="sendWS('TOGGLE_TIMER', {})" id="t-pause-btn">일시정지</button>
        <button class="btn btn-danger" onclick="sendWS('FORCE_END_ROUND', {})">즉시 마감</button>
      </div>
      <div class="grid-teams" id="t-round-bids-status"></div>
    </div>

    <div id="t-result" style="display: none; text-align: center;">
      <h2>경매 결과</h2>
      <div id="t-result-content" style="font-size: 1.2rem; margin: 15px 0; line-height: 1.7;"></div>
      <div id="t-periodic-summary" class="banner" style="display: none;"></div>
      <button class="btn btn-gold" onclick="sendWS('NEXT_ROUND', {})">다음으로</button>
    </div>

    <div id="t-final" style="display: none;">
      <h2>🏆 최종 결과 발표</h2>
      <div id="t-final-winner" class="banner"></div>
      <table>
        <thead>
          <tr><th>순위</th><th>모둠명</th><th>최종 점수</th><th>누적 낙찰 금액</th><th>상태</th></tr>
        </thead>
        <tbody id="t-final-table"></tbody>
      </table>
    </div>
  </div>

  <div id="view-student" class="container view" style="max-width: 460px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <h3 id="s-team-name">모둠명</h3>
      <span class="badge" id="s-score-badge">0점</span>
    </div>

    <div id="s-wait" style="text-align: center; padding: 40px 0;">
      <h3>입장 완료! 대기 중...</h3>
      <p style="color: #666; margin-top: 10px;">선생님이 게임을 시작하면 화면이 열립니다.</p>
    </div>

    <div id="s-bid" style="display: none;">
      <div style="background: var(--cream); padding: 12px; border-radius: 10px; margin-bottom: 15px; text-align: center;">
        <span id="s-round-num" style="font-weight: bold;">R1</span>
        <h2 id="s-round-item" style="margin: 4px 0;">초콜릿</h2>
        <div style="font-size: 0.9rem; color: #666;">배점: <b id="s-round-pts">1</b>점</div>
        <div class="timer-display" id="s-timer" style="font-size: 2.2rem;">02:00</div>
      </div>
      <div id="s-bid-form">
        <label style="display: block; margin-bottom: 6px; font-weight: bold;">입찰 금액 입력 (무제한)</label>
        <input type="number" id="s-bid-amount" placeholder="초코 화폐 단위를 입력" min="0" />
        <button class="btn btn-gold" style="width: 100%;" onclick="submitBid()">입찰 제출하기</button>
      </div>
      <div id="s-bid-done" style="display: none; text-align: center; padding: 15px; background: #eafaf1; border-radius: 10px;">
        <h3 style="color: var(--success);">입찰 완료!</h3>
        <p style="margin-top: 6px;">결과 발표를 기다리는 중...</p>
      </div>
    </div>

    <div id="s-result" style="display: none; text-align: center; padding: 15px 0;">
      <h2 id="s-res-title">결과</h2>
      <p id="s-res-desc" style="font-size: 1.1rem; margin: 12px 0;"></p>
      <div style="background: var(--cream); padding: 12px; border-radius: 10px; text-align: left; line-height: 1.6;">
        <div>우리 모둠 누적 점수: <b id="s-my-score">0</b>점</div>
        <div>우리 모둠 누적 낙찰액: <b id="s-my-spent">0</b></div>
      </div>
    </div>
  </div>

  <script>
    let ws = null;
    let role = null;
    let roomCode = "";
    let myTeamName = "";

    function switchView(id) {
      document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
      document.getElementById(id).classList.add("active");
    }

    function initWS(code, onOpenCallback) {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${proto}//${window.location.host}/ws/${code}`);
      ws.onopen = onOpenCallback;
      ws.onmessage = (e) => handleServerMsg(JSON.parse(
