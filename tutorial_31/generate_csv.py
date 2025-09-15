import csv

# ============================
# EXEMPLE DE DONNEES STATIQUES
# ============================
header = ["product", "vendor", "price", "website", "description", "delivery", "MOQ", "discounts"]

data = [
    ["Chaise ergonomique", "Vendor A", "$150", "https://vendorA.com", "Chaise de bureau", "5 jours", "10", "10% dès 20 unités"],
    ["MacBook Pro 16", "Vendor B", "$2400", "https://vendorB.com", "Apple MacBook Pro", "7 jours", "5", "Livraison gratuite"],
    ["Tableau blanc", "Vendor C", "$50", "https://vendorC.com", "Tableau magnétique", "3 jours", "2", "5% dès 10 unités"],
]

# ============================
# ECRITURE DANS LE CSV
# ============================
with open("data.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(data)

print(" Fichier data.csv généré avec succès")
