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
      ws.onmessage = (e) => handleServerMsg(JSON.parse(e.data));
      ws.onclose = () => alert("서버와의 연결이 종료되었습니다.");
    }

    function sendWS(type, data) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type, ...data }));
      }
    }

    function initTeacher() {
      role = "teacher";
      roomCode = Math.floor(1000 + Math.random() * 9000).toString();
      initWS(roomCode, () => {
        sendWS("INIT_TEACHER", {});
        document.getElementById("t-room-code").textContent = roomCode;
        switchView("view-teacher");
      });
    }

    function joinStudent() {
      const code = document.getElementById("join-code").value.trim();
      const team = document.getElementById("join-team").value.trim();
      if (!code || !team) return alert("코드와 모둠 이름을 모두 입력해 주세요.");
      role = "student";
      roomCode = code;
      myTeamName = team;
      initWS(roomCode, () => {
        sendWS("JOIN_STUDENT", { teamName: myTeamName });
        document.getElementById("s-team-name").textContent = myTeamName;
        switchView("view-student");
      });
    }

    function submitBid() {
      const val = document.getElementById("s-bid-amount").value;
      if (val === "" || Number(val) < 0) return alert("올바른 금액을 입력하세요.");
      sendWS("SUBMIT_BID", { teamName: myTeamName, amount: Number(val) });
      document.getElementById("s-bid-form").style.display = "none";
      document.getElementById("s-bid-done").style.display = "block";
    }

    function handleServerMsg(msg) {
      const { type, data } = msg;

      if (type === "ERROR") return alert(data.message);

      if (type === "UPDATE_LOBBY") {
        document.getElementById("t-team-count").textContent = data.teams.length;
        document.getElementById("t-teams-list").innerHTML = data.teams
          .map(t => `<div class="team-card">${t}</div>`).join("");
      }

      if (type === "ROUND_START") {
        if (role === "teacher") {
          document.getElementById("t-lobby").style.display = "none";
          document.getElementById("t-result").style.display = "none";
          document.getElementById("t-round").style.display = "block";
          document.getElementById("t-round-idx").textContent = `Round ${data.round} / 12`;
          document.getElementById("t-round-item").textContent = data.item;
          document.getElementById("t-round-point").textContent = `+${data.point}점`;
          updateTeacherBids(data.teams, []);
        } else {
          document.getElementById("s-wait").style.display = "none";
          document.getElementById("s-result").style.display = "none";
          document.getElementById("s-bid").style.display = "block";
          document.getElementById("s-bid-form").style.display = "block";
          document.getElementById("s-bid-done").style.display = "none";
          document.getElementById("s-round-num").textContent = `Round ${data.round}`;
          document.getElementById("s-round-item").textContent = data.item;
          document.getElementById("s-round-pts").textContent = data.point;
          document.getElementById("s-bid-amount").value = "";
        }
      }

      if (type === "BIDS_STATUS") {
        if (role === "teacher") updateTeacherBids(data.allTeams, data.submittedTeams);
      }

      if (type === "TIMER_TICK") {
        const min = String(Math.floor(data.remaining / 60)).padStart(2, '0');
        const sec = String(data.remaining % 60).padStart(2, '0');
        const text = `${min}:${sec}`;
        if (role === "teacher") document.getElementById("t-timer").textContent = text;
        if (role === "student") document.getElementById("s-timer").textContent = text;
      }

      if (type === "TIMER_STATE") {
        if (role === "teacher") {
          document.getElementById("t-pause-btn").textContent = data.isPaused ? "계속 진행" : "일시정지";
        }
      }

      if (type === "ROUND_RESULT") {
        if (role === "teacher") {
          document.getElementById("t-round").style.display = "none";
          document.getElementById("t-result").style.display = "block";
          document.getElementById("t-result-content").innerHTML = `
            <div>🎉 낙찰: <b>${data.highestTeams.join(", ")}</b> (${data.maxBid.toLocaleString()} 사용 / +${data.point}점)</div>
            <div style="color: var(--danger); margin-top: 8px;">⚠️ 최저가 페널티(-1점): <b>${data.lowestTeams.join(", ")}</b> (${data.minBid.toLocaleString()})</div>
          `;
          const sumEl = document.getElementById("t-periodic-summary");
          if (data.revealTotal) {
            sumEl.style.display = "block";
            sumEl.textContent = `📢 [누적 총액 공개] 모든 모둠 누적 낙찰액: ${data.totalSpentAll.toLocaleString()}`;
          } else {
            sumEl.style.display = "none";
          }
        } else {
          document.getElementById("s-bid").style.display = "none";
          document.getElementById("s-result").style.display = "block";
          const isHigh = data.highestTeams.includes(myTeamName);
          const isLow = data.lowestTeams.includes(myTeamName);
          const tEl = document.getElementById("s-res-title");
          const dEl = document.getElementById("s-res-desc");

          if (isHigh) {
            tEl.textContent = "🎉 낙찰 성공!";
            tEl.style.color = "var(--choco-dark)";
            dEl.innerHTML = `+${data.point}점 획득 (낙찰가: ${data.maxBid.toLocaleString()})`;
          } else if (isLow) {
            tEl.textContent = "⚠️ 최저가 감점(-1점)";
            tEl.style.color = "var(--danger)";
            dEl.textContent = "최저 입찰가로 1점이 감점되었습니다.";
          } else {
            tEl.textContent = "경매 종료";
            tEl.style.color = "#666";
            dEl.textContent = "낙찰되지 않았습니다.";
          }

          const myData = data.teamsData[myTeamName] || { score: 0, totalSpent: 0 };
          document.getElementById("s-my-score").textContent = myData.score;
          document.getElementById("s-my-spent").textContent = myData.totalSpent.toLocaleString();
          document.getElementById("s-score-badge").textContent = `${myData.score}점`;
        }
      }

      if (type === "GAME_OVER") {
        if (role === "teacher") {
          document.getElementById("t-result").style.display = "none";
          document.getElementById("t-final").style.display = "block";
          document.getElementById("t-final-winner").textContent = data.winner 
            ? `👑 최종 우승: [ ${data.winner.name} ] (${data.winner.score}점 / 누적 ${data.winner.totalSpent.toLocaleString()})`
            : "생존한 모둠이 없습니다.";

          const tbody = document.getElementById("t-final-table");
          tbody.innerHTML = "";
          let rank = 1;
          data.validTeams.forEach((t, i) => {
            tbody.innerHTML += `
              <tr class="${i === 0 ? 'winner' : ''}">
                <td><b>${rank++}위</b></td><td>${t.name}</td><td><b>${t.score}점</b></td>
                <td>${t.totalSpent.toLocaleString()}</td><td>생존</td>
              </tr>`;
          });
          data.bankruptTeams.forEach(t => {
            tbody.innerHTML += `
              <tr class="bankrupt">
                <td>-</td><td>${t.name}</td><td>${t.score}점</td>
                <td>${t.totalSpent.toLocaleString()}</td><td><b>파산 (최다 지출 탈락)</b></td>
              </tr>`;
          });
        } else {
          document.getElementById("s-bid").style.display = "none";
          document.getElementById("s-result").style.display = "block";
          const isWin = data.winner && data.winner.name === myTeamName;
          const isBankrupt = data.bankruptTeams.some(t => t.name === myTeamName);
          const tEl = document.getElementById("s-res-title");
          const dEl = document.getElementById("s-res-desc");

          if (isWin) {
            tEl.textContent = "🏆 우리 모둠 최종 우승!";
            dEl.textContent = "축하합니다! 최고 점수로 승리했습니다.";
          } else if (isBankrupt) {
            tEl.textContent = "💥 파산 탈락";
            dEl.textContent = "총 사용 금액 1위로 탈락했습니다.";
          } else {
            tEl.textContent = "게임 종료";
            dEl.textContent = "선생님 화면의 최종 순위를 확인하세요.";
          }
        }
      }
    }

    function updateTeacherBids(all, submitted) {
      document.getElementById("t-round-bids-status").innerHTML = all.map(t => {
        const done = submitted.includes(t);
        return `<div class="team-card ${done ? 'done' : ''}">${t}<br>${done ? '제출 완료' : '입찰 중...'}</div>`;
      }).join("");
    }
  </script>
</body>
</html>
"""

ROUNDS = [
    {"round": 1, "item": "초콜릿", "point": 1, "revealTotal": False},
    {"round": 2, "item": "초코케이크", "point": 3, "revealTotal": False},
    {"round": 3, "item": "초코과자", "point": 2, "revealTotal": True},
    {"round": 4, "item": "초코 폭포", "point": 4, "revealTotal": False},
    {"round": 5, "item": "초콜릿", "point": 1, "revealTotal": False},
    {"round": 6, "item": "초코과자", "point": 2, "revealTotal": True},
    {"round": 7, "item": "초콜릿", "point": 1, "revealTotal": False},
    {"round": 8, "item": "초코케이크", "point": 3, "revealTotal": False},
    {"round": 9, "item": "초코과자", "point": 2, "revealTotal": True},
    {"round": 10, "item": "초코과자", "point": 2, "revealTotal": False},
    {"round": 11, "item": "초콜릿", "point": 1, "revealTotal": False},
    {"round": 12, "item": "초코 폭포", "point": 4, "revealTotal": False},
]

class GameRoom:
    def __init__(self, code):
        self.code = code
        self.teacher_ws = None
        self.student_ws = {}
        self.teams = {}
        self.status = "lobby"
        self.current_r_idx = 0
        self.current_bids = {}
        self.timer_task = None
        self.remaining_time = 120
        self.is_paused = False

    async def broadcast(self, msg_type, data):
        payload = json.dumps({"type": msg_type, "data": data})
        targets = []
        if self.teacher_ws:
            targets.append(self.teacher_ws)
        targets.extend(self.student_ws.values())
        for ws in targets:
            try:
                await ws.send_text(payload)
            except:
                pass

    async def run_timer(self):
        while self.remaining_time > 0:
            if not self.is_paused:
                await asyncio.sleep(1)
                self.remaining_time -= 1
                await self.broadcast("TIMER_TICK", {"remaining": self.remaining_time})
            else:
                await asyncio.sleep(0.5)
        await self.evaluate_round()

    async def evaluate_round(self):
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        self.status = "result"
        r_data = ROUNDS[self.current_r_idx]

        for team in self.teams.keys():
            if team not in self.current_bids:
                self.current_bids[team] = 0

        bids_sorted = sorted(self.current_bids.items(), key=lambda x: x[1], reverse=True)
        max_bid = bids_sorted[0][1]
        min_bid = bids_sorted[-1][1]

        highest_teams = [t for t, b in bids_sorted if b == max_bid]
        lowest_teams = [t for t, b in bids_sorted if b == min_bid]

        for t in highest_teams:
            self.teams[t]["score"] += r_data["point"]
            self.teams[t]["totalSpent"] += max_bid

        for t in lowest_teams:
            self.teams[t]["score"] -= 1

        total_spent_all = sum(t["totalSpent"] for t in self.teams.values())

        await self.broadcast("ROUND_RESULT", {
            "round": r_data["round"],
            "point": r_data["point"],
            "maxBid": max_bid,
            "minBid": min_bid,
            "highestTeams": highest_teams,
            "lowestTeams": lowest_teams,
            "revealTotal": r_data["revealTotal"],
            "totalSpentAll": total_spent_all,
            "teamsData": self.teams
        })

rooms = {}

@app.get("/")
async def get_index():
    return HTMLResponse(HTML_CONTENT)

@app.websocket("/ws/{room_code}")
async def websocket_endpoint(ws: WebSocket, room_code: str):
    await ws.accept()
    if room_code not in rooms:
        rooms[room_code] = GameRoom(room_code)
    room = rooms[room_code]
    joined_team = None

    try:
        while True:
            text = await ws.receive_text()
            req = json.loads(text)
            action = req.get("type")

            if action == "INIT_TEACHER":
                room.teacher_ws = ws
                await room.broadcast("UPDATE_LOBBY", {"teams": list(room.teams.keys())})

            elif action == "JOIN_STUDENT":
                team = req.get("teamName")
                joined_team = team
                room.student_ws[team] = ws
                if team not in room.teams:
                    room.teams[team] = {"score": 0, "totalSpent": 0}
                await room.broadcast("UPDATE_LOBBY", {"teams": list(room.teams.keys())})

            elif action == "START_GAME":
                if len(room.teams) < 2:
                    await ws.send_text(json.dumps({"type": "ERROR", "data": {"message": "최소 2모둠 이상 참여해야 합니다."}}))
                    continue
                room.current_r_idx = 0
                await start_round_flow(room)

            elif action == "SUBMIT_BID":
                team = req.get("teamName")
                amt = req.get("amount")
                room.current_bids[team] = amt
                await room.broadcast("BIDS_STATUS", {
                    "allTeams": list(room.teams.keys()),
                    "submittedTeams": list(room.current_bids.keys())
                })
                if len(room.current_bids) >= len(room.teams):
                    await room.evaluate_round()

            elif action == "TOGGLE_TIMER":
                room.is_paused = not room.is_paused
                await room.broadcast("TIMER_STATE", {"isPaused": room.is_paused})

            elif action == "FORCE_END_ROUND":
                await room.evaluate_round()

            elif action == "NEXT_ROUND":
                if room.current_r_idx < 11:
                    room.current_r_idx += 1
                    await start_round_flow(room)
                else:
                    await end_game_flow(room)

    except WebSocketDisconnect:
        if joined_team and joined_team in room.student_ws:
            del room.student_ws[joined_team]

async def start_round_flow(room: GameRoom):
    room.status = "bidding"
    room.current_bids = {}
    room.remaining_time = 120
    room.is_paused = False
    r_data = ROUNDS[room.current_r_idx]

    await room.broadcast("ROUND_START", {
        "round": r_data["round"],
        "item": r_data["item"],
        "point": r_data["point"],
        "teams": list(room.teams.keys())
    })

    if room.timer_task and not room.timer_task.done():
        room.timer_task.cancel()
    room.timer_task = asyncio.create_task(room.run_timer())

async def end_game_flow(room: GameRoom):
    room.status = "gameover"
    teams_list = [{"name": name, **data} for name, data in room.teams.items()]

    max_spent = max(t["totalSpent"] for t in teams_list) if teams_list else 0
    bankrupt_teams = [t for t in teams_list if t["totalSpent"] == max_spent and max_spent > 0]
    bankrupt_names = [t["name"] for t in bankrupt_teams]

    valid_teams = [t for t in teams_list if t["name"] not in bankrupt_names]
    valid_teams.sort(key=lambda x: (-x["score"], x["totalSpent"]))

    winner = valid_teams[0] if valid_teams else None

    await room.broadcast("GAME_OVER", {
        "winner": winner,
        "validTeams": valid_teams,
        "bankruptTeams": bankrupt_teams
    })
