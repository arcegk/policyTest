#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy

"""
#######################################################
This is the base code for the engineer project.
#######################################################
"""


class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    billing_schedules = {'Annual': 1, 'Semi-Annual': 3, 'Quarterly': 4, 'Monthly': 12,
                         'Two-Pay': 2}

    def __init__(self, policy_id):
        self.policy = Policy.query.filter_by(id=policy_id).one()

        if not self.policy.invoices:
            self.make_invoices()

    def return_account_balance(self, date_cursor=None):
        """
        Calculates and returns the balance at a given date

        :param date_cursor: datetime.date instance
        :return: int - calculated balance
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .filter(Invoice.deleted.is_(False))\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()
        for payment in payments:
            due_now -= payment.amount_paid

        return due_now

    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        """
        Creates a payment for a given contact

        :param contact_id: int representing a Contact primary key
        :param date_cursor: datetime.date instance - transaction dat
        :param amount: int - amount of the payment made
        :return: Payment instance
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        if not contact_id:
            try:
                contact_id = self.policy.named_insured
            except:
                pass

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id) \
                                .filter(Invoice.due_date <= date_cursor) \
                                .order_by(Invoice.bill_date) \
                                .all()

        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        payments = Payment.query.filter_by(policy_id=self.policy.id) \
                                .filter(Payment.transaction_date <= date_cursor) \
                                .all()
        for payment in payments:
            due_now -= payment.amount_paid

        if due_now:
            return True

        return False

    def evaluate_cancel(self, date_cursor=None):
        """
        Checks if a policy should cancelled
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.cancel_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if not self.return_account_balance(invoice.cancel_date):
                continue
            else:
                return True
        else:
            return False

    def create_invoice(self, first_invoice, period):
        """
        :param first_invoice: Invoice instance
        :param billing_schedules: dict with the schedules available
        :param period: int with the number of periods (number of invoices)
        :return: list with Invoice instances
        """
        invoices = []
        first_invoice.amount_due = first_invoice.amount_due / self.billing_schedules.get(self.policy.billing_schedule)
        for i in range(1, self.billing_schedules.get(self.policy.billing_schedule)):
            months_after_eff_date = i*period
            bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
            amount = self.policy.annual_premium / self.billing_schedules.get(self.policy.billing_schedule)
            invoice = Invoice(self.policy.id,
                                bill_date,
                                bill_date + relativedelta(months=1), #due date
                                bill_date + relativedelta(months=1, days=14), #cancel date
                                amount)
            invoices.append(invoice)
        return invoices

    def make_invoices(self):
        """
        Create invoices for new Policy's instances
        """
        for invoice in self.policy.invoices:
            invoice.delete()

        invoices = []
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date, #bill_date
                                self.policy.effective_date + relativedelta(months=1), #due
                                self.policy.effective_date + relativedelta(months=1, days=14), #cancel
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        if self.policy.billing_schedule == "Annual":
            invoices += self.create_invoice(first_invoice, 12)
        elif self.policy.billing_schedule == "Two-Pay":
            invoices += self.create_invoice(first_invoice, 6)
        elif self.policy.billing_schedule == "Quarterly":
            invoices += self.create_invoice(first_invoice, 3)
        elif self.policy.billing_schedule == "Monthly":
            invoices += self.create_invoice(first_invoice, 1)
        else:
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()

    def change_billing_schedule(self, new_schedule):
        """
        changes current schedule to a given one

        :param new_schedule: str with the new schedule to set
        :return:
        """
        if new_schedule in self.billing_schedules:
            if self.policy.billing_schedule != new_schedule:
                self.policy.billing_schedule = new_schedule
                db.session.add(self.policy)
                db.session.commit()
                self.make_invoices()
                return
            else:
                print 'Nothing to change'
                return
        print "You have chosen a bad billing schedule."

    def make_cancelation(self, description=None, date_cursor=None, cancelation_date=None):
        """
        Cancels a policy if possible

        :param description: str
        :param date_cursor: datetime.date
        :param cancelation_date: datetime.date
        :return:
        """
        if self.evaluate_cancel(date_cursor):
            self.policy.cancel(description, cancelation_date)
            print "Policy cancelled"
        else:
            print "Policy can't be cancelled"

################################
# The functions below are for the db and 
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"


def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.agent = bob_smith.id
    p1.named_insured = john_doe_insured.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    p4 = Policy('Policy Four', date(2015, 2, 1), 500)
    p4.billing_schedule = 'Two-Pay'
    p4.named_insured = ryan_bucket.id
    p4.agent = john_doe_agent.id
    policies.append(p4)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()
