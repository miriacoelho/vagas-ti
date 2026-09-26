# Vagas TI — Juiz de Fora e estágios remotos

Página pública de oportunidades de estágio em tecnologia em Juiz de Fora e no modelo remoto em outras cidades, com candidatura nas páginas oficiais das empresas. Interface em português, responsiva, com filtros local/remoto e sem cadastro.

## Atualização diária

O GitHub Actions executa `.github/workflows/update.yml` diariamente às **11h17 UTC (8h17 em Brasília)**, em cada push para `main` e sob acionamento manual. Coleta, testa, salva o JSON e publica `dist/` no GitHub Pages. Não precisa de servidor ou chave de API. O agendamento pode atrasar; o GitHub pode desativar schedules de repositórios públicos após 60 dias sem atividade. Verifique a aba Actions se a atualização parar.

## Fontes e critérios

- Páginas de carreira da Guiando/TOTVS, Rede Verbita, Unimed Juiz de Fora, Smart NX, Apogeu e DOMO/Gupy. O conteúdo público completo da Gupy é lido, incluindo vagas além da primeira página visual.
- Nerdin: percorre a categoria de estágios e início de carreira, seguindo a paginação pública (até 10 páginas e 40 detalhes por execução). Extrai título, empresa e modalidade; consulta links oficiais quando disponíveis e cruza os anúncios com as empresas monitoradas. A correspondência exige empresa conhecida e título compatível. Anúncios sem origem identificada ficam registrados em `discovery` no JSON e não viram candidatura no site. Não acessa áreas restritas ou contatos Premium.
- O estágio DOMO encontrado no Nerdin foi associado à vaga oficial; a fonte oficial informa prazo passado, por isso fica no histórico. A rotina também descobre novas vagas remotas diretamente nas empresas, como FinOps.
- Os três agregadores sugeridos são fontes de descoberta; seus links nunca são usados para candidatura. Bloqueios, robots.txt e falhas são registrados, sem contornar proteções.
- A descoberta é limitada às fontes e plataformas suportadas, não cobre toda a web. Novas empresas podem ser incluídas em `sources.json`; outros sistemas precisam de adaptador.
- Somente anúncios com título de estágio em TI e cidade de Juiz de Fora **ou modalidade explicitamente remota** entram na lista. Híbrido fora de Juiz de Fora não entra. Vagas remotas podem impor restrições de residência; consulte a descrição. Menções genéricas a tecnologia na apresentação institucional não bastam.
- Descrição, empresa e local são extraídos de JobPosting; TOTVS também fornece as seções completas. A interface exibe texto simples para impedir execução de HTML das fontes.
- Bancos de talentos são identificados explicitamente. O prazo de inscrição `registerEndDate` da Gupy prevalece sobre `validThrough`, que pode estar desatualizado nos metadados de busca. Prazos passados aparecem separados, mesmo que a página continue acessível.
- Candidatura usa o formulário estável da TOTVS quando exposto, ou a página exata da vaga na plataforma da empresa. Nunca usa link de busca ou agregador.
- Falhas não fabricam vagas, não apagam silenciosamente registros anteriores e não renovam sua data de verificação. Registros antigos ficam a confirmar; após 48 horas a interface retira a indicação de inscrição confirmada.
- O coletor respeita robots.txt, limita a frequência por domínio, aplica timeout e limita cada execução a 100 anúncios. Fontes que dependem de JavaScript ou bloqueiam robôs podem ficar indisponíveis. Cobertura e erros aparecem na página.
- Bolsa e modalidade não informadas são apresentadas como tal. Não inferimos valores ou regime.

## Currículos para estudantes

A seção `#curriculos` oferece dois modelos originais gratuitos em DOCX editável e TXT: primeiro estágio e projetos em destaque. Os arquivos ficam em `dist/downloads/`, não exigem cadastro e são publicados junto com o site. Os campos entre colchetes devem ser substituídos por informações verdadeiras; seções sem aplicação devem ser removidas. A página traz orientações de preenchimento, revisão e envio, com leitura complementar do MIT. Os modelos não incluem dados reais de alunos e não prometem aprovação em processos seletivos.

## Rodar localmente

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/collect.py
python -m http.server 8765 --directory dist
```

Abra http://localhost:8765. O frontend usa somente HTML, CSS e JavaScript. Fontes do Google são opcionais: há fontes locais de fallback.

## Publicar

Em Settings → Pages, selecione **GitHub Actions** como fonte. Execute **Atualizar vagas e publicar** na aba Actions. O workflow precisa de `contents: write`, `pages: write` e `id-token: write`. Ele guarda os dados no próprio repositório, evitando que uma indisponibilidade temporária descarte o histórico.

O arquivo `dist/jobs.json` contém a data real da coleta, as fontes consultadas, suas falhas e os anúncios. Uma falha geral é publicada como indisponibilidade e marca a execução do workflow como falha.
