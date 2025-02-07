import json
import os
from flask import Flask, render_template, request, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__, static_folder='static', template_folder='templates')

# Load credentials from environment variable instead of file
creds_json = os.getenv("GOOGLE_CREDENTIALS")
if creds_json:
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    client = gspread.authorize(creds)
else:
    raise Exception("GOOGLE_CREDENTIALS not set in Render environment variables.")

# Open the Google Sheets workbook
workbook = client.open('xarkids')
sheet1 = workbook.worksheet("Sheet1")
sheet2 = workbook.worksheet("Sheet2")



#database for account details
account_details = {
    "10007210": {"passcode": "1811"},
    "10007211": {"passcode": "0000"},
    "10007212": {"passcode": "0000"},
    "10007213": {"passcode": "0000"},
    "10007214": {"passcode": "0000"},
    "10007215": {"passcode": "0000"},
    "10007216": {"passcode": "0000"},
    "10007217": {"passcode": "0000"},
    "10007218": {"passcode": "0000"},
    "10007219": {"passcode": "0000"},
}

sender_pin_codes = {
    "10007210": {"passcode": "1811"},
    "10007211": {"passcode": "0000"},
    "10007212": {"passcode": "0000"},
    "10007213": {"passcode": "0000"},
    "10007214": {"passcode": "0000"},
    "10007215": {"passcode": "0000"},
    "10007216": {"passcode": "0000"},
    "10007217": {"passcode": "0000"},
    "10007218": {"passcode": "0000"},
    "10007219": {"passcode": "0000"},
}

# Hardcoded PIN code for the sender

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        passcode = request.form['passcode']

        # Generate new account number
        new_acc_number = str(int(max(account_details.keys())) + 1)

        # Add new user to the database
        account_details[new_acc_number] = {"passcode": passcode, "balance": 0}

        # Add new user to Sheet2
        sheet2.append_row([new_acc_number, 1])
        return(account_details)
        return redirect('/login')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        acc_number = request.form['acc_number']
        passcode = request.form['passcode']

        # Dummy authentication logic
        if acc_number in account_details and account_details[acc_number]["passcode"] == passcode:
            return redirect('/home?acc_number=' + acc_number)
        else:
            return "Login failed. Please check your credentials."

    return render_template('login.html')

@app.route('/home')
def home():
    acc_number = request.args.get('acc_number')

    # Find the row corresponding to the account number
    for row in range(2, len(sheet2.get_all_values()) + 1):
        if acc_number == sheet2.cell(row, 1).value:
            balance = sheet2.cell(row, 2).value
            return render_template('home.html', account_number=acc_number, balance=balance)

    # If the account number is not found, return an error message
    return "Account not found"

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if request.method == 'POST':
        sender_acc = request.form['sender_acc']
        sender_pin = request.form['sender_pin']
        receiver_acc = request.form['receiver_acc']
        amount = float(request.form['amount'])

        # Check if sender PIN is hardcoded
        if sender_acc not in sender_pin_codes or sender_pin_codes[sender_acc]["passcode"] != sender_pin:
            return "Incorrect sender pin"

        sender_balance = None
        receiver_balance = None

        # Find sender's balance
        for row in range(2, len(sheet2.get_all_values()) + 1):
            if sender_acc == sheet2.cell(row, 1).value:
                sender_balance = float(sheet2.cell(row, 2).value)
                break

        # Find receiver's balance
        for row in range(2, len(sheet2.get_all_values()) + 1):
            if receiver_acc == sheet2.cell(row, 1).value:
                receiver_balance = float(sheet2.cell(row, 2).value)
                break

        # Check if sender and receiver accounts are found
        if sender_balance is None:
            return "Sender account not found"
        if receiver_balance is None:
            return "Receiver account not found"

        # Calculate transaction fee (2% of the transaction amount)
        transaction_fee = amount * 0.02

        # Deduct transaction fee from sender's balance
        sender_balance -= transaction_fee

        # Check if sender has sufficient balance (including transaction fee)
        if sender_balance < amount:
            return "Insufficient balance"

        # Deduct the transaction amount (including fee) from sender's balance
        sender_balance -= amount
        
        timestamp = time.time()
        miner_account = "10007215"
        miner_award =  transaction_fee * 0.5

        # Generate hashcode for the transaction
        transaction_details = f"{sender_acc}-{amount}-{timestamp}-{receiver_acc}-{miner_account}"
        hashcode = hashlib.sha256(transaction_details.encode()).hexdigest()

        # Get the previous hash
        previous_hash = sheet1.cell(len(sheet1.get_all_values()), 3).value if len(sheet1.get_all_values()) > 1 else "0"

        # Add transaction data to Sheet1
        
        # Assume miner is awarded the transaction fee XARCOIN for each transaction

        sheet1.append_row([sender_acc, amount, hashcode, previous_hash, receiver_acc, timestamp, transaction_fee, miner_account, miner_award])

        # Update balances
        for row in range(2, len(sheet2.get_all_values()) + 1):
            if sender_acc == sheet2.cell(row, 1).value:
                sheet2.update_cell(row, 2, sender_balance)
            elif receiver_acc == sheet2.cell(row, 1).value:
                sheet2.update_cell(row, 2, receiver_balance + amount)

        # Update miner's balance
        for row in range(2, len(sheet2.get_all_values()) + 1):
            if miner_account == sheet2.cell(row, 1).value:
                miner_balance = float(sheet2.cell(row, 2).value)
                sheet2.update_cell(row, 2, miner_balance + miner_award)
                break

        # Redirect to success page with transaction details
        return render_template('transaction_success.html',
                               transaction_id = hashcode,
                               sender_acc = sender_acc,
                               receiver_acc = receiver_acc,
                               amount = amount,
                               transaction_fee = transaction_fee,
                               timestamp = timestamp)
                              
    else:
        return render_template('transfer.html')

@app.route('/price')
def price():
    sheet2_data = sheet2.get_all_values()
    
    # Check if sheet2_data has any rows
    if len(sheet2_data) < 2:  # Assuming the first row is header
        return render_template('price.html',
                               total_coin_supply=0,
                               total_investment=0,
                               price_per_coin=0)

    total_coin_supply = sum(float(row[2]) for row in sheet2_data[1:] if row[2])  # Check if row[2] is not empty
    total_investment = sum(float(row[3]) for row in sheet2_data[1:] if row[3])  # Check if row[3] is not empty
    price_per_coin = total_coin_supply / total_investment if total_coin_supply else 0

    return render_template('price.html',
                           total_coin_supply=total_investment,
                           total_investment=total_coin_supply,
                           price_per_coin=price_per_coin)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))