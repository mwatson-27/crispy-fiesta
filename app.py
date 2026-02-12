rom flask import Flask, render_template, request, jsonify
import sqlite3
import random
import math

app = Flask(__name__)
DATABASE = "database.db"
K = 32

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Create table
with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            label TEXT NOT NULL,
            rating REAL DEFAULT 1200
        )
    """)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    with get_db() as conn:
        conn.execute(
            "INSERT INTO images (url, label) VALUES (?, ?)",
            (data["url"], data["label"])
        )
    return jsonify({"status": "ok"})

@app.route("/matchup")
def matchup():
    with get_db() as conn:
        images = conn.execute(
            "SELECT * FROM images ORDER BY RANDOM() LIMIT 2"
        ).fetchall()

    if len(images) < 2:
        return jsonify([])

    return jsonify([dict(img) for img in images])

@app.route("/vote", methods=["POST"])
def vote():
    data = request.json
    winner_id = data["winnerId"]
    loser_id = data["loserId"]

    with get_db() as conn:
        winner = conn.execute(
            "SELECT rating FROM images WHERE id=?",
            (winner_id,)
        ).fetchone()

        loser = conn.execute(
            "SELECT rating FROM images WHERE id=?",
            (loser_id,)
        ).fetchone()

        expected_winner = 1 / (1 + 10 ** ((loser["rating"] - winner["rating"]) / 400))
        expected_loser = 1 - expected_winner

        new_winner = winner["rating"] + K * (1 - expected_winner)
        new_loser = loser["rating"] + K * (0 - expected_loser)

        conn.execute("UPDATE images SET rating=? WHERE id=?", (new_winner, winner_id))
        conn.execute("UPDATE images SET rating=? WHERE id=?", (new_loser, loser_id))

    return jsonify({"status": "ok"})

@app.route("/leaderboard-data")
def leaderboard_data():
    with get_db() as conn:
        images = conn.execute(
            "SELECT * FROM images ORDER BY rating DESC"
        ).fetchall()

    return jsonify([dict(img) for img in images])

if __name__ == "__main__":
    app.run(debug=True)
