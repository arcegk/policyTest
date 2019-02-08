# You will probably need more methods from flask but this one is a good start.
from flask import render_template, request, jsonify

# Import things from Flask that we need.
from accounting import app
from .utils import PolicyAccounting


# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')


@app.route("/get-policy/")
def get_policy():
    policy_id = request.args.get('policy', type=int)
    date = request.args.get('date')
    if policy_id:
        try:
            policy_accounting = PolicyAccounting(policy_id)
            response = {'balance': policy_accounting.return_account_balance(date),
                        'invoices': [x.serialize for x in policy_accounting.policy.invoices],
                        'success': True}
        except Exception as e:
            response = {'success': False, 'msg': str(e)}
    else:
        response = {'success': False, 'msg': 'invalid policy_id'}

    return jsonify(response)
