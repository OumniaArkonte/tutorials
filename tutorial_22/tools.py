import requests
from bs4 import BeautifulSoup
from typing import List

REQUEST_TIMEOUT = 5

def check_security_headers(domain: str) -> str:
    url = f"https://{domain}"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        headers = r.headers
        required = ['Content-Security-Policy', 'X-Frame-Options', 'Strict-Transport-Security']
        results = []
        for h in required:
            results.append(f" {h} found" if h in headers else f" {h} missing")
        # add some extra header info
        results.append(f"Server header: {headers.get('Server', 'Not found')}")
        return "\n".join(results)
    except Exception as e:
        return f"Header check failed: {e}"

def check_common_directories(domain: str) -> str:
    base = f"https://{domain}"
    wordlist = ["/admin", "/login", "/config", "/.git", "/backup", "/wp-admin", "/phpinfo.php"]
    found = []
    for p in wordlist:
        try:
            r = requests.get(base + p, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if r.status_code in (200, 401, 403):
                found.append(f" {base + p} [{r.status_code}]")
        except Exception:
            continue
    return "\n".join(found) if found else "No common directories found."

def find_js_urls(domain: str) -> str:
    url = f"https://{domain}"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        js_urls = []
        for s in soup.find_all("script", src=True):
            src = s["src"]
            if src.startswith("http"):
                js_urls.append(src)
            else:
                js_urls.append(f"{url.rstrip('/')}/{src.lstrip('/')}")
        return "\n".join(js_urls) if js_urls else "No JS files found."
    except Exception as e:
        return f"JS scan failed: {e}"

def check_robots_txt(domain: str) -> str:
    url = f"https://{domain}/robots.txt"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            text = r.text
            snippet = text if len(text) <= 1000 else text[:1000] + "\n... (truncated)"
            return f" robots.txt found:\n{snippet}"
        else:
            return f" robots.txt not found (status {r.status_code})"
    except Exception as e:
        return f"robots.txt check failed: {e}"

def check_sitemap(domain: str) -> str:
    url = f"https://{domain}/sitemap.xml"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            text = r.text
            snippet = text if len(text) <= 1000 else text[:1000] + "\n... (truncated)"
            return f" sitemap.xml found:\n{snippet}"
        else:
            return f" sitemap.xml not found (status {r.status_code})"
    except Exception as e:
        return f"sitemap check failed: {e}"

def check_env_exposure(domain: str) -> str:
    url = f"https://{domain}/.env"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            text = r.text
            sensitive_markers = ["APP_KEY", "DB_PASSWORD", "DATABASE_URL", "SECRET_KEY"]
            found_markers = [m for m in sensitive_markers if m in text]
            if found_markers:
                snippet = text[:800] + ("\n... (truncated)" if len(text) > 800 else "")
                return f" Exposed .env file with markers {found_markers}:\n{snippet}"
            else:
                return " .env file accessible but no known sensitive markers found."
        else:
            return ".env file not accessible."
    except Exception as e:
        return f".env check failed: {e}"

def check_server_header(domain: str) -> str:
    url = f"https://{domain}"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        return f" Server: {r.headers.get('Server', 'Not found')}"
    except Exception as e:
        return f"Server header check failed: {e}"

def check_http_redirect(domain: str) -> str:
    try:
        r = requests.get(f"http://{domain}", timeout=REQUEST_TIMEOUT, allow_redirects=True)
        final = r.url
        if final.startswith("https://"):
            return f" HTTP redirects to HTTPS (final: {final})"
        else:
            return f" HTTP does not redirect to HTTPS (final: {final})"
    except Exception as e:
        return f"Redirect check failed: {e}"

def check_github_mentions(domain: str) -> str:
    # ne fait pas de scraping — retourne juste le lien de recherche pour enquête manuelle
    query = f'"{domain}" site:github.com'
    link = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    return f" Rechercher sur GitHub (manuel):\n{link}"

# liste exportable d'outils pour être fournie au Test Agent
ALL_TOOLS = {
    "check_security_headers": check_security_headers,
    "check_common_directories": check_common_directories,
    "find_js_urls": find_js_urls,
    "check_robots_txt": check_robots_txt,
    "check_sitemap": check_sitemap,
    "check_env_exposure": check_env_exposure,
    "check_server_header": check_server_header,
    "check_http_redirect": check_http_redirect,
    "check_github_mentions": check_github_mentions,
}
