#!/user/bin/env python2.7

import unittest
from datetime import date
import json

from flask import Flask

from accounting import db, views
from models import Contact, Invoice, Policy
from utils import PolicyAccounting

"""
#######################################################
Test Suite for Accounting
#######################################################
"""


class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()


class TestBillingSchedules(BaseTest):

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_annual_billing_schedule(self):
        self.policy.billing_schedule = "Annual"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 1)
        self.assertEquals(self.policy.invoices[0].amount_due, self.policy.annual_premium)

    def test_monthly_billing_schedule(self):
        self.policy.billing_schedule = "Monthly"
        self.assertFalse(self.policy.invoices)
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 12)
        self.assertEquals(self.policy.invoices[0].amount_due, 100)


class TestReturnAccountBalance(BaseTest):

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_annual_on_eff_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 1200)

    def test_quarterly_on_eff_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 300)

    def test_quarterly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[3].bill_date), 1200)

    def test_quarterly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                             date_cursor=invoices[1].bill_date, amount=600))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)


class TestPolicyCancel(BaseTest):

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_policy_cancelation(self):
        pa = PolicyAccounting(self.policy.id)
        pa.make_cancelation()
        self.assertEquals(self.policy.status, 'Canceled')


class TestPolicyView(unittest.TestCase):
    s_app = Flask(__name__)

    @staticmethod
    @s_app.route("/get-policy/")
    def get_mek_policy():
        return views.get_policy()

    @classmethod
    def setUpClass(cls):
        with cls.s_app.app_context():
            cls.test_agent = Contact('Test Agent', 'Agent')
            cls.test_insured = Contact('Test Insured', 'Named Insured')
            db.session.add(cls.test_agent)
            db.session.add(cls.test_insured)
            db.session.commit()

            cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
            db.session.add(cls.policy)
            cls.policy.named_insured = cls.test_insured.id
            cls.policy.agent = cls.test_agent.id
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        with cls.s_app.app_context():
            db.session.delete(cls.test_insured)
            db.session.delete(cls.test_agent)
            db.session.delete(cls.policy)
            db.session.commit()

    def tearDown(self):
        with self.s_app.app_context():
            for invoice in self.policy.invoices:
                db.session.delete(invoice)
            db.session.commit()

    def test_invalid_request(self):
        with self.s_app.app_context():
            pa = PolicyAccounting(self.policy.id)
            print self.policy.id
            with self.s_app.test_client() as c:
                data = c.get("/get-policy/").data
                print data
            data = json.loads(data)
            self.assertEquals(data['success'], False)

    def test_valid_request(self):
        with self.s_app.app_context():
            pa = PolicyAccounting(self.policy.id)
            with self.s_app.test_client() as c:
                data = c.get("/get-policy/?policy={}".format(self.policy.id)).data
                print data
            data = json.loads(data)
            self.assertEquals(data['success'], True)
            self.assertEquals(data['balance'], 1200)

    def test_invalid_number_request(self):
        with self.s_app.app_context():
            pa = PolicyAccounting(self.policy.id)
            print self.policy.id
            with self.s_app.test_client() as c:
                data = c.get("/get-policy/?policy=abc").data
                print data
            data = json.loads(data)
            self.assertEquals(data['success'], False)
