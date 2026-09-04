import asyncio
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# 품목별 이미지 URL 매핑
ITEM_IMAGES = {
    "초콜릿": "https://images.unsplash.com/photo-1548907040-4baa42d10919?w=500&auto=format&fit=crop&q=80",
    "초코케이크": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=500&auto=format&fit=crop&q=80",
    "초코과자": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=500&auto=format&fit=crop&q=80",
    "초코 폭포": "https://images.unsplash.com/photo-1511381939415-e44015466834?w=500&auto=format&fit=crop&q=80"
}

ROUNDS = [
    {"round": 1, "item": "초콜릿", "point": 1, "revealTotal": False, "img": ITEM_IMAGES["초콜릿"]},
    {"round": 2, "item": "초코케이크", "point": 3, "revealTotal": False, "img": ITEM_IMAGES["초코케이크"]},
    {"round": 3, "item": "초코과자", "point": 2, "revealTotal": True, "img": ITEM_IMAGES["초코과자"]},
    {"round": 4, "item": "초코 폭포", "point": 4, "revealTotal": False, "img": ITEM_IMAGES["초코 폭포"]},
    {"round": 5, "item": "초콜릿", "point": 1, "revealTotal": False, "img": ITEM_IMAGES["초콜릿"]},
    {"round": 6, "item": "초코과자", "point": 2, "revealTotal": True, "img": ITEM_IMAGES["초코과자"]},
    {"round": 7, "item": "초콜릿", "point": 1, "revealTotal": False, "img": ITEM_IMAGES["초콜릿"]},
    {"round": 8, "item": "초코케이크", "point": 3, "revealTotal": False, "img": ITEM_IMAGES["초코케이크"]},
    {"round": 9, "item": "초코과자", "point": 2, "revealTotal": True, "img": ITEM_IMAGES["초코과자"]},
    {"round": 10, "item": "초코과자", "point": 2, "revealTotal": False, "img": ITEM_IMAGES["초코과자"]},
    {"round": 11, "item": "초콜릿", "point": 1, "revealTotal": False, "img": ITEM_IMAGES["초콜릿"]},
    {"round": 12, "item": "초코 폭포", "point": 4, "revealTotal": False, "img": ITEM_IMAGES["초코 폭포"]},
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
            "item": r_data["item"],
            "img": r_data["img"],
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
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

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

            elif action == "FORCE_END_GAME":
                if room.timer_task and not room.timer_task.done():
                    room.timer_task.cancel()
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
        "img": r_data["img"],
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
