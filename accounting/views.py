# You will probably need more methods from flask but this one is a good start.
from flask import render_template, request, jsonify

# Import things from Flask that we need.
from accounting import app, db
from .utils import PolicyAccounting

# Import our models
from models import Contact, Invoice, Policy

# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')


@app.route("/get-policy/")
def get_policy():
    policy_id = request.args.get('policy', type=int)
    date = request.args.get('date')
    policy_accounting = PolicyAccounting(policy_id)
    response = {'balance': policy_accounting.return_account_balance(date),
                'invoices': [x.serialize for x in policy_accounting.policy.invoices]}

    return jsonify(response)
