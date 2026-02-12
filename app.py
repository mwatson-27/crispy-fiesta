from flask import Flask, render_template, jsonify, request
import sqlite3
import os
import math

app = Flask(__name__)
DATABASE = "database.db"
K = 32  # ELO constant

# -------------------------
# Database Helper
# -------------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------
# Create Table If Not Exists
# -------------------------
with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            label TEXT,
            rating REAL DEFAULT 1200
        )
    """)

# -------------------------
# Auto-Load Images From Folder
# -------------------------
@app.before_first_request
def load_images():
    with get_db() as conn:
        for file in os.listdir("static/images"):
            name, ext = os.path.splitext(file)

            if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
                continue

            # Optional: clean up label formatting
            label = name.replace("_", " ").title()

            conn.execute("""
                INSERT OR IGNORE INTO images (filename, label)
                VALUES (?, ?)
            """, (file, label))

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html")

@app.route("/matchup")
def matchup():
    with get_db() as conn:
        images = conn.execute(
            "SELECT * FROM images ORDER BY RANDOM() LIMIT 2"
        ).fetchall()

    if len(images) < 2:
        return jsonify([])

    result = []
    for img in images:
        result.append({
            "id": img["id"],
            "url": f"/static/images/{img['filename']}",
            "label": img["label"]
        })

    return jsonify(result)

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

        if not winner or not loser:
            return jsonify({"error": "Invalid IDs"}), 400

        # ELO Calculation
        expected_winner = 1 / (1 + 10 ** ((loser["rating"] - winner["rating"]) / 400))
        expected_loser = 1 - expected_winner

        new_winner = winner["rating"] + K * (1 - expected_winner)
        new_loser = loser["rating"] + K * (0 - expected_loser)

        conn.execute(
            "UPDATE images SET rating=? WHERE id=?",
            (new_winner, winner_id)
        )

        conn.execute(
            "UPDATE images SET rating=? WHERE id=?",
            (new_loser, loser_id)
        )

    return jsonify({"status": "ok"})

@app.route("/leaderboard-data")
def leaderboard_data():
    with get_db() as conn:
        images = conn.execute(
            "SELECT * FROM images ORDER BY rating DESC"
        ).fetchall()

    return jsonify([
        {
            "label": img["label"],
            "url": f"/static/images/{img['filename']}",
            "rating": round(img["rating"])
        }
        for img in images
    ])

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
