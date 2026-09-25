"""Daily public-page collector. Only employer recruiting pages become job cards."""
import html
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
UA = 'VagasTIJF/1.0 (+https://github.com/miriacoelho/vagas-ti)'
SESSION = requests.Session()
SESSION.headers['User-Agent'] = UA
ROBOTS = {}
LAST_REQUEST = {}

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c)).lower()

def text(s):
    return BeautifulSoup(str(s or ''), 'html.parser').get_text(' ', strip=True)

def official(url):
    p = urlparse(url)
    return p.scheme == 'https' and (p.hostname or '').endswith('.gupy.io') and p.hostname != 'portal.gupy.io' or p.scheme == 'https' and p.hostname == 'atracaodetalentos.totvs.app'

def job_url(url):
    p = urlparse(url)
    return official(url) and bool(re.search(r'/jobs/\d+|/[^/]+/\d+/[^/]+', p.path))

def canonical(url):
    p = urlparse(url)
    return p._replace(query='', fragment='').geturl().rstrip('/')

def get(url):
    """Respect robots, finite timeouts, conservative rate and redirect policy."""
    for _ in range(5):
        p = urlparse(url)
        if p.scheme != 'https' or not p.hostname or p.username:
            raise ValueError('URL não permitida')
        # Discovery never follows arbitrary user-controlled URLs: all requests
        # originate from config, Bing or supported ATS hosts.
        origin = f'https://{p.netloc}'
        if origin not in ROBOTS:
            response = SESSION.get(origin+'/robots.txt', timeout=20, allow_redirects=False)
            if response.status_code == 404:
                ROBOTS[origin] = None
            elif response.status_code == 200:
                robot = RobotFileParser()
                robot.parse(response.text.splitlines())
                ROBOTS[origin] = robot
            else:
                raise ValueError('robots.txt indisponível; consulta adiada')
        robot = ROBOTS[origin]
        if robot and not robot.can_fetch(UA, url):
            raise ValueError('Consulta não permitida por robots.txt')
        delay = max(1, (robot.crawl_delay(UA) or 0) if robot else 0)
        time.sleep(max(0, delay - (time.monotonic()-LAST_REQUEST.get(origin, 0))))
        r = SESSION.get(url, timeout=(10, 35), allow_redirects=False)
        LAST_REQUEST[origin] = time.monotonic()
        if r.is_redirect:
            target = urljoin(url, r.headers['Location'])
            if urlparse(target).hostname != p.hostname:
                raise ValueError('Redirecionamento externo precisa de revisão')
            url = target
            continue
        r.raise_for_status()
        # Both ATS providers emit UTF-8; requests may otherwise assume Latin-1.
        r.encoding = 'utf-8'
        return r.text
    raise ValueError('Redirecionamentos excessivos')

def jsonld(soup):
    def walk(value):
        if isinstance(value, list):
            for v in value:
                yield from walk(v)
        elif isinstance(value, dict):
            if value.get('@type') == 'JobPosting':
                yield value
            if '@graph' in value:
                yield from walk(value['@graph'])
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            # TOTVS currently appends a JavaScript semicolon to its JSON-LD.
            raw = script.get_text().strip().removesuffix(';').strip()
            try:
                value = json.loads(raw)
            except ValueError:
                value = json.loads(html.unescape(raw))
            yield from walk(value)
        except (ValueError, TypeError):
            continue

def relevant(title, city):
    t = norm(title)
    return 'juiz de fora' in norm(city) and bool(re.search(r'\bestagi(?:o|ario|aria)', t)) and bool(re.search(r'\bti\b|tecnologia|informatica|desenvolvimento|banco de dados|infraestrutura|software|sistemas|programa[cç]ao|dados|redes|seguranca da informacao', t))

def date_part(value):
    if value and re.match(r'^\d{4}-\d{2}-\d{2}', str(value)):
        return str(value)[:10]
    return None

def parse_job(raw, url, now):
    soup = BeautifulSoup(raw, 'html.parser')
    record = next(jsonld(soup), None)
    if not record:
        raise ValueError('Página sem dados estruturados de vaga; revisão necessária')
    title = text(record.get('title'))
    locations = record.get('jobLocation', [])
    if isinstance(locations, dict):
        locations = [locations]
    cities = [l.get('address', {}).get('addressLocality', '') for l in locations if isinstance(l, dict)]
    city = ', '.join(cities)
    if not relevant(title, city):
        return None
    description = text(record.get('description'))
    company = text(record.get('hiringOrganization', {}).get('name'))
    deadline = date_part(record.get('validThrough'))
    status = 'active'
    mode = None
    warnings = []
    next_data = soup.find('script', id='__NEXT_DATA__')
    if next_data:
        job = json.loads(next_data.string)['props']['pageProps'].get('job', {})
        # Gupy's application deadline is more specific than its Google indexing expiry.
        deadline = date_part(job.get('registerEndDate')) or deadline
        if job.get('status') not in (None, 'published'):
            status = 'closed'
        mode = {'on-site':'Presencial','hybrid':'Híbrido','remote':'Remoto'}.get(job.get('workplaceType'))
    if deadline and deadline < now[:10]:
        status = 'expired'
    if 'contratacao: efetiva' in norm(description) and 'estagi' in norm(title):
        warnings.append('O título indica estágio, mas o texto menciona contratação CLT. Confirme o vínculo com a empresa.')
    sections = []
    # TOTVS renders duplicated mobile/desktop descriptions; keep each section once.
    for node in soup.select('.job-opportunity__text'):
        value = node.get_text(' ', strip=True)
        if value and value not in sections:
            sections.append(value)
    if sections:
        description = '\n\n'.join(sections)
    apply_url = url
    has_apply = False
    for a in soup.select('a[href]'):
        label = norm(a.get_text(' ', strip=True))
        target = urljoin(url, a['href'])
        if any(x in label for x in ['candidat', 'apply', 'inscreva']):
            if official(target) or urlparse(target).hostname == 'centraldocandidato.totvs.app':
                has_apply = True
                # Stable employer detail page for Gupy; TOTVS direct form has a stable job UUID.
                if urlparse(target).hostname == 'centraldocandidato.totvs.app' and 'job-opportunity-application/' in target:
                    apply_url = target
    if not has_apply and status == 'active':
        status = 'unconfirmed'
    labels = {'active':'Inscrições disponíveis','expired':'Prazo informado encerrado','closed':'Inscrições encerradas','unconfirmed':'Candidatura a confirmar'}
    return {'id':canonical(url),'title':title,'company':company,'city':'Juiz de Fora · MG','mode':mode,
            'salary':None,'summary':description[:290].rsplit(' ',1)[0]+'…' if len(description)>290 else description,
            'description':description,'talentPool':'banco de talentos' in norm(title+' '+description),
            'sourceUrl':canonical(url),'applyUrl':apply_url,'checkedAt':now,'publishedAt':date_part(record.get('datePosted')),
            'deadline':deadline,'status':status,'statusLabel':labels[status],'warning':' '.join(warnings)}

def extract_candidates(raw, base):
    soup = BeautifulSoup(raw, 'html.parser')
    result = set()
    for a in soup.select('a[href]'):
        url = canonical(urljoin(base, a['href']))
        if job_url(url):
            # On employer boards, fetch only internship listings; aggregators may
            # expose links without a label, so accept those for subsequent validation.
            label = norm(a.get_text(' ', strip=True))
            if 'estagi' in label or not official(base):
                result.add(url)
    return result

def run():
    config = json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc).isoformat()
    output = ROOT/'dist/jobs.json'
    previous = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {'jobs':[]}
    candidates = set(config['seeds']) | {j['sourceUrl'] for j in previous['jobs']}
    sources = []
    for source in config['boards']+config['discovery']:
        try:
            raw = get(source['url'])
            found = extract_candidates(raw, source['url'])
            candidates |= found
            # Fail visibly if a challenge or client-only replacement hides the list.
            if not found and not any(x in norm(raw) for x in ['vagas','jobs','oportunidades']):
                raise ValueError('Conteúdo da página não reconhecido')
            sources.append({**source,'status':'ok','candidates':len(found)})
        except Exception as e:
            sources.append({**source,'status':'error','message':str(e)[:200]})
    for query in config['searches']:
        source = {'name':'Busca web: '+query, 'url':'https://www.bing.com/search?format=rss&q='+quote(query)}
        try:
            raw = get(source['url'])
            links = re.findall(r'<link>(.*?)</link>', raw)
            found = {canonical(html.unescape(u)) for u in links if job_url(html.unescape(u))}
            candidates |= found
            if '<rss' not in raw:
                raise ValueError('Busca web não retornou RSS; consulta indisponível')
            sources.append({**source,'status':'ok','candidates':len(found)})
        except Exception as e:
            sources.append({**source,'status':'error','message':str(e)[:200]})
    jobs = {}
    old = {j['sourceUrl']:j for j in previous['jobs']}
    verified = 0
    for url in sorted(candidates)[:100]:
        try:
            result = parse_job(get(url), url, now)
            verified += 1
            if result:
                jobs[result['id']] = result
            sources.append({'name':'Anúncio: '+url,'url':url,'status':'ok'})
        except Exception as e:
            sources.append({'name':'Anúncio: '+url,'url':url,'status':'error','message':str(e)[:200]})
            if url in old:
                jobs[url] = {**old[url], 'status':'unconfirmed','statusLabel':'Verificação indisponível'}
    result = {'checkedAt':now,'jobs':sorted(jobs.values(),key=lambda j:(j['status']!='active',j['company'],j['title'])),'sources':sources}
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(output)
    print(json.dumps({'jobs':len(jobs),'active':sum(j['status']=='active' for j in jobs.values()),'verified':verified,'sourceErrors':sum(s['status']!='ok' for s in sources)},ensure_ascii=False))
    # Keep the publication step running so the public page displays an outage,
    # but allow the workflow to report the failed collection after publication.
    return 0 if verified else 2

if __name__ == '__main__':
    sys.exit(run())
