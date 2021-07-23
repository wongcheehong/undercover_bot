import sqlite3
import random

conn = sqlite3.connect('./databases/undercover.db')
c = conn.cursor()

def get_all_word_pairs():
    c.execute("SELECT * FROM CompleteWordPairs where hasBeenPlayed=0")
    rows = c.fetchall()
    return rows

def set_hasBeenPlayed(id_):
    c.execute("UPDATE CompleteWordPairs SET hasBeenPlayed=1 WHERE id=?", (id_,))
    conn.commit()

def get_word_pair():
    rows = get_all_word_pairs()
    if not rows:
        c.execute("UPDATE CompleteWordPairs SET hasBeenPlayed=0")
        conn.commit()
        rows = get_all_word_pairs()
    
    row = random.choice(rows)
    set_hasBeenPlayed(row[0])
    words = [row[1], row[2]]
    random.shuffle(words)
    return words
