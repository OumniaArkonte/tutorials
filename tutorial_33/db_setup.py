import sqlite3

# Nom du fichier DB
DB_FILE = "logistics.db"

# Connexion à SQLite (créera le fichier si n'existe pas)
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# --- Création de la table prices ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carrier TEXT NOT NULL,
    max_weight REAL NOT NULL,
    price REAL NOT NULL
)
""")

# --- Vider la table si déjà existante (optionnel pour tests) ---
cursor.execute("DELETE FROM prices")

# --- Insertion des tarifs de test ---
tarifs = [
    ("DHL", 1.0, 10.0),
    ("DHL", 3.0, 25.0),
    ("DHL", 5.0, 40.0),
    ("UPS", 2.0, 15.0),
    ("UPS", 3.0, 28.0),
    ("FedEx", 2.0, 22.0),
    ("FedEx", 5.0, 45.0)
]

cursor.executemany("INSERT INTO prices (carrier, max_weight, price) VALUES (?, ?, ?)", tarifs)

# Sauvegarder et fermer
conn.commit()
conn.close()

print(f" Base '{DB_FILE}' créée avec succès et tarifs insérés.")
