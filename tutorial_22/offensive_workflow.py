from agno.agent import Agent
from agno.models.google import Gemini
import whois
import dns.resolver
import requests
from textwrap import dedent
from tools import ALL_TOOLS  
from dotenv import load_dotenv


load_dotenv()



def extract_domain(url: str) -> str:
    return url.split("//")[-1].split("/")[0].strip()

def get_whois(domain: str) -> str:
    try:
        w = whois.whois(domain)
        return "\n".join(f"{k}: {v}" for k, v in w.items())
    except Exception as e:
        return f"WHOIS lookup failed: {e}"

def get_dns(domain: str) -> str:
    try:
        answers = dns.resolver.resolve(domain, 'A')
        return ", ".join(rdata.address for rdata in answers)
    except Exception as e:
        return f"DNS lookup failed: {e}"

def get_http_headers(domain: str) -> str:
    try:
        r = requests.head(f"https://{domain}", timeout=5)
        return "\n".join(f"{k}: {v}" for k, v in r.headers.items())
    except Exception as e:
        return f"HTTP headers fetch failed: {e}"

def main():
    # Définition des agents
    analyzer_agent = Agent(
        name="Analyzer",
        model=Gemini(id="gemini-2.0-flash"),
        description="Agent d'analyse passive, qui identifie les tests de sécurité pertinents"
    )

    tester_agent = Agent(
        name="Tester",
        model=Gemini(id="gemini-2.0-flash"),
        description="Agent de test qui exécute les outils non intrusifs pour analyser la sécurité"
    )

    # Prendre le domaine cible
    target_input = input("Entrez le domaine ou URL cible: ")
    domain = extract_domain(target_input)

    # Collecte des données passives
    whois_info = get_whois(domain)
    dns_info = get_dns(domain)
    headers_info = get_http_headers(domain)

    context = dedent(f"""
    Domaine : {domain}

    WHOIS :
    {whois_info}

    DNS :
    {dns_info}

    HTTP Headers :
    {headers_info}
    """)

    # Étape 1: Reconnaissance / analyse
    print("=== Étape 1 : Analyse (Analyzer Agent) ===")
    recon_output = analyzer_agent.run(context)
    try:
        recon_text = recon_output.content
    except Exception:
        # si output est juste une string
        recon_text = str(recon_output)

    print("=== Résultat de l’analyse ===")
    print(recon_text)

    # Étape 2: Tester avec les outils pertinents
    print("\n=== Étape 2 : Tests (Tester Agent) ===")

    prompt_for_tester = dedent(f"""
    Voici le résumé des tests recommandés par l'agent d'analyse :

    {recon_text}

    Tu as accès aux outils suivants : {', '.join(ALL_TOOLS.keys())}

    Pour chacun des tests recommandés, choisis l'outil correspondant, exécute-le (non intrusif), et rapporte :
    - Les outils utilisés + pourquoi
    - Les outils ignorés + raison
    - Les résultats des tests
    - Un score de sécurité (Low / Medium / High)
    - Des recommandations pour améliorer la sécurité
    """)

    test_output = tester_agent.run(prompt_for_tester)
    try:
        test_text = test_output.content
    except Exception:
        test_text = str(test_output)

    print("=== Rapport des tests ===")
    print(test_text)

if __name__ == "__main__":
    main()
