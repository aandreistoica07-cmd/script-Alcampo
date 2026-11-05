"""Read-only audit of the public portal's OAuth callback, without account data."""
import hashlib
import json
import re
from urllib.parse import urljoin

import requests


def inspect():
    portal = 'https://www.miportal.alcampo.es'
    response = requests.get(portal + '/es/cuenta/fidelidad', timeout=25)
    response.raise_for_status()
    assets = re.findall(r'(?:src|href)=["\'](/assets/js/app\.[^"\']+\.js)', response.text)
    assets = list(dict.fromkeys(assets))
    if len(assets) != 1:
        raise RuntimeError('No se identifica de forma única el bundle actual del portal')
    url = urljoin(portal, assets[0])
    response = requests.get(url, timeout=25)
    response.raise_for_status()
    source = response.text
    return {
        'public_bundle': url,
        'sha256': hashlib.sha256(response.content).hexdigest(),
        'callback_reads_query_code': bool(re.search(r'logInSF\(\{code:\w+\.query\.code', source)),
        'redirect_uri_uses_callback_path': 'e.protocol+"//"+e.host+e.pathname' in source,
        'callback_clears_previous_session': '$cookies.remove("token")' in source,
        'callback_exchanges_code_on_portal': 'data:{code:t.code,redirectUri:t.redirectUri}' in source,
        'pkce_text_present': bool(re.search(r'code_verifier|code_challenge', source)),
        'scope': 'Public source only; does not prove a transferable login works.',
    }


if __name__ == '__main__':
    print(json.dumps(inspect(), ensure_ascii=False, indent=2))
