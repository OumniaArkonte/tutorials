import sqlite3

DB_PATH = "logistics.db"

def get_price(carrier: str, weight: float = 5.0) -> str:
    """
    Récupère le prix depuis logistics.db pour un transporteur donné et un poids donné
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT price FROM prices WHERE carrier=? AND weight=?",
        (carrier.lower(), weight)
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return f" Tarif {carrier.upper()} : {result[0]}€ pour {weight}kg."
    else:
        return f" Aucun tarif trouvé pour {carrier.upper()} et {weight}kg."
