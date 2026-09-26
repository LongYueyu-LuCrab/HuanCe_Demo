import tempfile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import LabOrder, LabDevice, Experiment


class NoSalesConfirmationFiveOrderTests(TestCase):
    """Five fresh orders exercise the real HTTP workflow through final invoicing."""

    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.users = {}
        for key, role in [('sales','销售'),('dept','商务部'),('chair','董事长'),('gm','总经理'),('sz','苏州实验室'),('jy','江阴实验室'),('finance','会计')]:
            u=get_user_model().objects.create_user(key)
            u.groups.add(Group.objects.get_or_create(name=role)[0]);self.users[key]=u
        self.devices={key:LabDevice.objects.create(device_code=key,device_name=key,lab_type=typ) for key,typ in [('sz',1),('jy',2)]}

    def action(self, who, name, expected=200, **kw):
        self.client.force_login(self.users[who])
        data={'action':name,'order_no':self.order.order_no,**kw}
        response=self.client.post(reverse('lims_action'),data,**({} if 'sample_photos' in kw else {'content_type':'application/json'}))
        self.assertEqual(response.status_code,expected,response.content)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.sales_confirmed_at)
        return response

    def run_order(self, owner, routes, reschedule=False, change=False):
        self.client.force_login(self.users[owner])
        response=self.client.post(reverse('create_order'),{'customer_name':'免销售确认-虚拟测试','project_name':self._testMethodName,'test_requirements':'虚拟流程回归','quoted_amount':'1000','expected_sample_arrival':'2026-12-01','industry_category':'other','execution_attributes':['autonomous']},content_type='application/json')
        self.assertEqual(response.status_code,200,response.content)
        self.order=LabOrder.objects.get(project_name=self._testMethodName)
        self.action('chair','review_pass')
        self.action('gm','review_pass',execution_routes=['suzhou' if x=='sz' else 'jiangyin' for x in routes],suzhou_manager_id=self.users['sz'].pk,jiangyin_manager_id=self.users['jy'].pk,lead_lab_manager_id=self.users[routes[0]].pk)
        self.action(owner,'sales_confirm',expected=410)
        for schedule in self.order.schedules.order_by('pk'):
            lab='sz' if schedule.test_type==1 else 'jy'
            self.action(lab,'start_test',expected=400,schedule_id=schedule.pk)
            kwargs={'schedule_id':schedule.pk,'device_id':self.devices[lab].pk,'plan_start_time':'2026-12-01','plan_end_time':'2026-12-02'}
            self.action('dept','schedule_assign',**kwargs)
            self.action(lab,'start_test',expected=400,schedule_id=schedule.pk)  # Sample gate remains.
            if reschedule:
                kwargs.update(plan_start_time='2026-11-30',plan_end_time='2026-11-30')
                self.action('dept','schedule_assign',**kwargs)
            self.action(lab,'sample_arrival',schedule_id=schedule.pk,sample_photos=SimpleUploadedFile(f'{lab}.png',b'test-photo',content_type='image/png'))
            if change:
                self.action(owner,'create_change',new_test_demand='修改后的虚拟需求',change_content='验证变更后不回流销售确认')
                self.action(lab,'start_test',expected=400,schedule_id=schedule.pk)
                self.action(lab,'process_change',sample_arrived=True,**kwargs)
            self.action(lab,'start_test',schedule_id=schedule.pk)
            self.action(lab,'end_test',schedule_id=schedule.pk,result_status=Experiment.Result.PASS,test_raw_data='完整虚拟数据',test_conclusion_temp='合格')
            self.action(lab,'submit_test',schedule_id=schedule.pk)
        self.action(routes[0],'issue_report',final_conclusion='虚拟回归合格')
        report=self.order.reports.get()
        self.action(owner,'report_sales_pass',report_no=report.report_no)
        self.action('gm','report_gm_pass',report_no=report.report_no)
        self.action('finance','invoice_create',report_no=report.report_no,invoice_amount=str(self.order.total_quote))
        self.assertEqual(self.order.order_status,LabOrder.Status.INVOICED_CLOSED)
        self.client.force_login(self.users['chair'])
        progress=self.client.get(reverse('order_detail',kwargs={'order_no':self.order.order_no})).json()['order']['workflow_progress']
        self.assertEqual(progress['total_steps'],12)
        self.assertNotIn('sales_confirmation',[s['key'] for s in progress['steps']])
        self.assertEqual([s['sequence'] for s in progress['steps']],list(range(1,13)))
        print(f'FIVE-ORDER PASS: {self._testMethodName}; stages=create/review/schedule/sample/test/result/report/audit/invoice; sales_confirmed_at=NULL')

    def test_01_sales_suzhou(self):self.run_order('sales',['sz'])
    def test_02_department_jiangyin(self):self.run_order('dept',['jy'])
    def test_03_advance_reschedule_without_confirmation(self):self.run_order('dept',['sz'],reschedule=True)
    def test_04_change_closed_without_reconfirmation(self):self.run_order('dept',['jy'],change=True)
    def test_05_parallel_labs_without_confirmation(self):self.run_order('sales',['sz','jy'])
