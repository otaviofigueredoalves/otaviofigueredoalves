"""Atualiza somente informações públicas do proprietário; nenhuma dependência externa."""
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER = os.environ.get('PROFILE_USERNAME', 'otaviofigueredoalves')
if not re.fullmatch(r'[A-Za-z0-9-]{1,39}', OWNER):
    raise ValueError('Nome de usuário inválido')


def fetch_repositories():
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'github-profile-dashboard'}
    token = os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    repos = []
    page = 1
    while True:
        url = f'https://api.github.com/users/{quote(OWNER)}/repos?type=owner&sort=pushed&per_page=100&page={page}'
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError('Resposta inesperada da API')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [r for r in repos if not r.get('private') and not r.get('fork')
            and r['owner']['login'].lower() == OWNER.lower() and r['name'].lower() != OWNER.lower()]


def render(repos):
    recent = sorted([r for r in repos if r.get('pushed_at') and not r.get('archived')],
                    key=lambda r: r['pushed_at'], reverse=True)[:3]
    stamp = datetime.now(timezone.utc).strftime('%d/%m/%Y · %H:%M UTC')
    langs = Counter(r['language'] for r in repos if r.get('language'))
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="330" viewBox="0 0 1100 330" role="img" aria-labelledby="title">',
           '<title id="title">Repositórios públicos próprios e últimos repositórios com push registrado</title>',
           '<rect width="1100" height="330" rx="20" fill="#0b1220"/>',
           '<g font-family="Arial,Helvetica,sans-serif">',
           '<circle cx="32" cy="35" r="4" fill="#42d392"/>',
           '<text x="47" y="40" fill="#a9b9ce" font-size="13" letter-spacing="2">PUBLIC REPOSITORIES / LIVE SNAPSHOT</text>',
           f'<text x="30" y="96" fill="#f1f5fc" font-size="37" font-weight="700">{len(repos)}</text>',
           '<text x="30" y="122" fill="#92a5bf" font-size="14">repositórios próprios</text>',
           f'<text x="280" y="96" fill="#42d392" font-size="37" font-weight="700">{sum(r.get("stargazers_count",0) for r in repos)}</text>',
           '<text x="280" y="122" fill="#92a5bf" font-size="14">estrelas nos repositórios</text>',
           f'<text x="550" y="88" fill="#c3b5ff" font-size="17">{escape(" / ".join(k for k,v in langs.most_common(4)) or "Sem linguagem identificada")}</text>',
           '<text x="550" y="116" fill="#92a5bf" font-size="13">linguagens principais por número de repositórios</text>',
           '<path d="M30 145H1070" stroke="#23354c"/>',
           '<text x="30" y="173" fill="#92a5bf" font-size="12" letter-spacing="2">ÚLTIMOS REPOSITÓRIOS COM PUSH REGISTRADO</text>']
    lines = []
    for i, repo in enumerate(recent):
        date = repo['pushed_at'][:10]
        name = repo['name']
        label = name if len(name) <= 70 else name[:67] + '...'
        svg.append(f'<text x="30" y="{204+i*30}" fill="#e0e8f5" font-size="16">{escape(label)}</text>')
        svg.append(f'<text x="960" y="{204+i*30}" fill="#7e95b2" font-size="13">{date}</text>')
        # A lista contém links funcionais mesmo quando SVGs não renderizam.
        lines.append(f'- [{name}](https://github.com/{quote(OWNER)}/{quote(name)}) · último push registrado em {date}')
    if not recent:
        svg.append('<text x="30" y="208" fill="#92a5bf" font-size="15">Sem repositórios públicos não arquivados com push registrado.</text>')
    svg.append(f'<text x="30" y="308" fill="#6f859f" font-size="12">Atualizado em {stamp} · Sem forks, repositórios privados ou repositório do perfil.</text></g></svg>')
    return '\n'.join(svg), '\n'.join(lines) or 'Sem repositórios públicos disponíveis neste recorte.'


def main():
    # Buscar tudo antes de escrever: uma falha de API preserva a versão anterior.
    repos = fetch_repositories()
    svg, links = render(repos)
    readme_path = ROOT / 'README.md'
    readme = readme_path.read_text(encoding='utf-8')
    pattern = r'(?s)(<!-- ACTIVITY:START -->).*?(<!-- ACTIVITY:END -->)'
    if len(re.findall(pattern, readme)) != 1:
        raise ValueError('README deve conter exatamente um bloco ACTIVITY')
    updated = re.sub(pattern, lambda m: m[1] + '\n' + links + '\n' + m[2], readme)
    (ROOT / 'assets/activity.svg').write_text(svg, encoding='utf-8')
    readme_path.write_text(updated, encoding='utf-8')
    print(f'Painel atualizado: {len(repos)} repositórios públicos próprios.')


if __name__ == '__main__':
    main()
