"""beta.18: real stage outcomes, additive API snapshots and persistence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ha-reporting/app'))
import main
import automation_store

class ProductPolishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = automation_store.AUTOMATION_FILE
        automation_store.AUTOMATION_FILE = Path(self.temp.name)/'automations.json'
        main.AUTOMATION_JOBS.clear()
        self.report = {'id':'r','name':'Test','ai_analysis':{'enabled':True}}
        self.item = automation_store.create_automation({'name':'Test','report_id':'r','schedule':{'type':'daily','time':'12:00'},'pipeline':{'ai_analysis':True,'generate_pdf':True,'destinations':['paperless']},'notification':{'persistent':True}})

    def tearDown(self):
        main.AUTOMATION_JOBS.clear()
        automation_store.AUTOMATION_FILE = self.original
        self.temp.cleanup()

    def seed(self, **changes):
        options = main._scheduled_automation_payload(self.item, trigger='manual')
        options.update(changes)
        with patch.object(main,'load_report',return_value=self.report), patch.object(threading.Thread,'start'):
            return main.start_automation_report_job(options)['id']

    def run_job(self, job_id, *, export_error=False, ai_error=False, pdf_error=False):
        with patch.object(main,'load_report',return_value=self.report), patch.object(main,'home_assistant_timezone',return_value='Europe/Zurich'), patch.object(main,'execute_report',return_value={'summary':{},'resolved_period':{}}), patch.object(main,'_automation_ai_analysis',return_value={'status':'error' if ai_error else 'completed','text':'OK'}), patch.object(main,'generate_report_pdf',side_effect=RuntimeError('PDF failed') if pdf_error else None,return_value={'id':'doc','filename':'test.pdf'}), patch.object(main,'export_document',side_effect=RuntimeError('Offline') if export_error else None,return_value={'result':{}}), patch.object(main,'_persistent_notification_for_job',return_value={}), patch.object(main,'_safe_home_assistant_event'):
            main._run_automation_job(job_id)
        return main.get_automation_job(job_id)

    def test_success_is_persisted_and_available_after_job_cache_is_lost(self):
        job = self.run_job(self.seed())
        self.assertEqual(job['status'],'completed')
        self.assertEqual({step['state'] for step in job['steps'].values()},{'completed'})
        history=automation_store.list_history(self.item['id'])
        self.assertEqual(history[0]['progress']['steps'],job['steps'])
        main.AUTOMATION_JOBS.clear()
        with patch.object(main,'home_assistant_timezone',return_value='Europe/Zurich'):
            overview=main.scheduled_automation_overview()[0]
        self.assertEqual(overview['progress']['steps'],job['steps'])

    def test_optional_steps_are_skipped(self):
        job=self.run_job(self.seed(ai_analysis=False, generate_pdf=False, destinations=[], notification={'persistent':False}))
        self.assertEqual(job['status'],'completed')
        for key in ['ai','pdf','export','notification']:
            self.assertEqual(job['steps'][key]['state'],'skipped')

    def test_partial_failure_retains_successful_pdf_and_distinguishes_warnings(self):
        job=self.run_job(self.seed(),export_error=True,ai_error=True)
        self.assertEqual(job['status'],'completed_with_errors')
        self.assertEqual(job['steps']['ai']['state'],'warning')
        self.assertEqual(job['steps']['export']['state'],'warning')
        self.assertEqual(job['steps']['pdf']['state'],'completed')
        self.assertEqual(job['steps']['notification']['state'],'completed')
        self.assertIsNone(automation_store.get_automation(self.item['id'])['runtime']['next_retry_at'])

    def test_failed_pdf_does_not_mark_unreached_steps_complete(self):
        job=self.run_job(self.seed(),pdf_error=True)
        self.assertEqual(job['status'],'error')
        self.assertEqual(job['steps']['pdf']['state'],'error')
        self.assertEqual(job['steps']['export']['state'],'pending')
        self.assertEqual(job['steps']['notification']['state'],'pending')

    def test_overview_uses_live_stage_and_does_not_leak_mutable_state(self):
        jid=self.seed()
        main._set_pipeline_step(jid,'data','running')
        with patch.object(main,'home_assistant_timezone',return_value='Europe/Zurich'):
            live=main.scheduled_automation_overview()[0]['progress']
        self.assertEqual(live['steps']['data']['state'],'running')
        live['steps']['data']['state']='error'
        self.assertEqual(main.get_automation_job(jid)['steps']['data']['state'],'running')

    def test_interrupted_job_does_not_reuse_previous_success_progress(self):
        self.run_job(self.seed())
        automation_store.update_runtime(self.item['id'],last_status='interrupted')
        with patch.object(main,'home_assistant_timezone',return_value='Europe/Zurich'):
            self.assertIsNone(main.scheduled_automation_overview()[0]['progress'])

    def test_static_images_work_with_ingress_prefix_and_correct_content_type(self):
        for asset in ['icon.png','logo.png','favicon.png']:
            handler=object.__new__(main.Handler)
            handler.path=f'/api/hassio_ingress/test/{asset}'
            with patch.object(handler,'send_payload') as send:
                handler.do_GET()
            code,body,content_type=send.call_args.args
            self.assertEqual(code,200)
            self.assertEqual(content_type,'image/png')
            self.assertTrue(body.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_preview_ai_without_cached_statistics_still_works(self):
        with patch.object(main,'load_report',return_value={'ai_analysis':{'enabled':False}}), patch.object(main,'_cached_report_result',return_value=None), patch.object(main,'execute_report',return_value={}), patch.object(main,'_cache_report_result'):
            self.assertEqual(main.start_ai_analysis('r')['status'],'disabled')

if __name__=='__main__':unittest.main()
