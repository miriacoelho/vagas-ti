const el = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};
const fmt = value => value ? new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short', timeZone: 'America/Sao_Paulo'
}).format(new Date(value.length === 10 ? value + 'T12:00:00Z' : value)) : 'Não informado';
function link(text, url, cls) {
  const a = el('a', text, cls);
  if (new URL(url).protocol !== 'https:') throw Error('Link inválido');
  a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer';
  return a;
}
function card(j) {
  const article = el('article', null, 'job');
  article.append(el('div', j.company.substring(0, 2).toUpperCase(), 'company-icon'));
  const body = el('div');
  const top = el('div', null, 'job-top');
  top.append(el('span', j.company, 'company'), el('span', j.status === 'active'
    ? (j.talentPool ? 'Banco de talentos' : 'Estágio') : j.statusLabel,
    'badge' + (j.status === 'active' ? '' : ' warning')));
  if (j.discoveredVia) top.append(el('span', 'Encontrada no ' + j.discoveredVia, 'discovery-label'));
  body.append(top, el('h3', j.title.replace(/^\[Banco de Talentos\]\s*/i, '')));
  const meta = el('div', null, 'meta');
  meta.append(el('span', '⌖ ' + j.city), el('span', j.mode || 'Modalidade não informada'), el('span', j.salary || 'Bolsa não informada'));
  body.append(meta, el('p', j.summary));
  if (j.warning) body.append(el('p', j.warning, 'job-warning'));
  const details = el('details');
  details.append(el('summary', 'Atividades, requisitos e benefícios'), el('p', j.description));
  body.append(details);
  const bottom = el('div', null, 'job-bottom');
  bottom.append(el('small', 'Verificado em ' + fmt(j.checkedAt) + (j.deadline ? ' · Prazo: ' + fmt(j.deadline) : '')));
  const actions = el('div');
  if (j.status === 'active') actions.append(link(j.talentPool ? 'Cadastrar interesse ↗' : 'Ver candidatura ↗', j.applyUrl, 'apply'));
  actions.append(link('Página da empresa ↗', j.sourceUrl, 'official'));
  bottom.append(actions); body.append(bottom); article.append(body);
  return article;
}
function freshJob(j) { return Date.now() - new Date(j.checkedAt) < 48 * 3600000; }
function render(data, scope) {
  const filtered = data.jobs.filter(j => scope === 'all' || (scope === 'remote' ? j.mode === 'Remoto' : j.city.toLowerCase().includes('juiz de fora')));
  const active = filtered.filter(j => j.status === 'active' && freshJob(j));
  const other = filtered.filter(j => !active.includes(j));
  document.querySelector('#count').textContent = active.length;
  const list = document.querySelector('#jobs'); list.replaceChildren();
  if (active.length) active.forEach(j => list.append(card(j)));
  else {
    const box = el('div', null, 'empty');
    box.append(el('h3', 'Nenhum estágio com inscrição confirmada neste recorte.'),
      el('p', 'Acompanhe a próxima atualização. Anúncios com prazo encerrado ou pendência de confirmação aparecem abaixo.'));
    list.append(box);
  }
  document.querySelector('#archive').hidden = !other.length;
  document.querySelector('#archive-count').textContent = '(' + other.length + ')';
  const archive = document.querySelector('#archive-jobs'); archive.replaceChildren();
  other.forEach(j => archive.append(card({ ...j, statusLabel: j.status === 'active' ? 'Verificação desatualizada' : j.statusLabel,
    status: j.status === 'active' ? 'stale' : j.status })));
  document.querySelectorAll('[data-scope]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.scope === scope)));
}
async function main() {
  try {
    const response = await fetch('./jobs.json', { cache: 'no-store' });
    if (!response.ok) throw Error();
    const data = await response.json();
    const fresh = Date.now() - new Date(data.checkedAt) < 48 * 3600000;
    document.querySelector('#updated').textContent = 'Última varredura · ' + fmt(data.checkedAt);
    render(data, 'all');
    document.querySelectorAll('[data-scope]').forEach(button => button.addEventListener('click', () => render(data, button.dataset.scope)));
    const failed = data.sources.filter(s => s.status !== 'ok');
    if (failed.length || !fresh) {
      const n = document.querySelector('#notice'); n.hidden = false;
      n.textContent = !fresh ? 'A última varredura tem mais de 48 horas. As oportunidades precisam de nova verificação.'
        : 'Cobertura parcial: algumas fontes não permitiram consulta ou não forneceram links oficiais. Veja os detalhes da varredura abaixo.';
    }
    data.sources.forEach(s => {
      if (s.name.startsWith('Anúncio:') && s.status === 'ok') return;
      let message = s.status === 'ok' ? 'consultada' : s.message || 'indisponível';
      if (s.pages) message += ` · ${s.pages} páginas · ${s.leads} anúncios no recorte`;
      document.querySelector('#sources').append(el('li', s.name + ' — ' + message));
    });
    if (data.discovery?.unresolved) document.querySelector('#sources').append(el('li',
      `${data.discovery.unresolved} anúncio(s) do Nerdin aguardam identificação da candidatura oficial e não entram na lista de vagas confirmadas.`));
  } catch {
    document.querySelector('#jobs').replaceChildren(el('p', 'Não foi possível carregar as vagas. Atualize a página para tentar novamente.', 'empty'));
    document.querySelector('#updated').textContent = 'Verificação indisponível';
  }
}
main();
