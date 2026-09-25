import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect import parse_job, relevant, official, extract_candidates

class ValidationTests(unittest.TestCase):
    def page(self, deadline='2027-01-01', extra=''):
        data={'@type':'JobPosting','title':'Estágio em TI','hiringOrganization':{'name':'Empresa'},'description':'Suporte técnico e redes.','validThrough':deadline,'jobLocation':{'address':{'addressLocality':'Juiz de Fora'}}}
        return '<script type="application/ld+json">'+json.dumps(data)+'</script><a href="https://empresa.gupy.io/jobs/1">Candidatar-se</a>'+extra

    def test_rejects_other_cities_and_non_it(self):
        self.assertFalse(relevant('Estágio em TI','São Paulo'))
        self.assertFalse(relevant('Estágio em Administração','Juiz de Fora'))
        self.assertFalse(relevant('Analista de TI','Juiz de Fora'))
        self.assertTrue(relevant('Estágio em Banco de Dados','Juiz de Fora'))

    def test_expired_not_active(self):
        j=parse_job(self.page('2025-01-01'),'https://empresa.gupy.io/jobs/1','2026-09-25T12:00:00Z')
        self.assertEqual(j['status'],'expired')

    def test_application_deadline_overrides_seo_expiry(self):
        extra='<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'job':{'status':'published','registerEndDate':'2026-10-30'}}}})+'</script>'
        j=parse_job(self.page('2026-07-01',extra),'https://empresa.gupy.io/jobs/1','2026-09-25T12:00:00Z')
        self.assertEqual(j['status'],'active')
        self.assertEqual(j['deadline'],'2026-10-30')

    def test_closed_job_stays_closed(self):
        extra='<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'job':{'status':'closed'}}}})+'</script>'
        self.assertEqual(parse_job(self.page(extra=extra),'https://empresa.gupy.io/jobs/1','2026-09-25T12:00:00Z')['status'],'closed')

    def test_aggregator_and_spoof_domains_not_official(self):
        for u in ['https://br.jobsora.com/job/1','https://empresa.gupy.io.evil.test/jobs/1','http://empresa.gupy.io/jobs/1','javascript:alert(1)']:
            self.assertFalse(official(u))

    def test_discovery_deduplicates_and_rejects_aggregator(self):
        raw='<a href="https://empresa.gupy.io/jobs/1?utm_source=x">Estágio TI</a><a href="https://empresa.gupy.io/jobs/1">Estágio TI</a><a href="https://br.jobsora.com/job/1">Estágio TI</a>'
        self.assertEqual(extract_candidates(raw,'https://br.jobsora.com/'),{'https://empresa.gupy.io/jobs/1'})

    def test_missing_apply_is_unconfirmed(self):
        raw=self.page().split('<a')[0]
        self.assertEqual(parse_job(raw,'https://empresa.gupy.io/jobs/1','2026-09-25T12:00:00Z')['status'],'unconfirmed')

if __name__=='__main__':
    unittest.main()
