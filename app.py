from flask import Flask, render_template_string
import requests
import time
import threading
import random

app = Flask(__name__)

last_debt = 0
# How much the debt increases per second (around 74400 in 2024)
rate_per_second = 74400
debt_lock = threading.Lock()

TEMPLATE = """
<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <title>US National Debt</title>
    <style>
        body { font-family: Arial, sans-serif; background: #333; text-align: center; padding-top: 50px; color: #fff; }
        .debt { font-size: 2em; color: #4287f5; margin-top: 20px; }
        .container { background: #444; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); }
        h1 { color: #add8e6; }
        a { color: #add8e6; }
    </style>
    <script>
        let currentDebt = 0;
        let nextDebt = 0;
        let step = 0;
        let frames = 60; // 60 fps

        function fetchDebt() {
            fetch('/get_debt')
                .then(response => response.json())
                .then(data => {
                    let numeric = Number(data.debt.replace(/[^0-9.-]+/g,""));
                    currentDebt = nextDebt;
                    nextDebt = numeric;
                    step = (nextDebt - currentDebt) / frames;
                });
        }

        function animateDebt() {
            currentDebt += step;
            // Add a small random variation to the ones place for visual dynamism
            let variation = Math.random() * 10 - 5;
            let displayDebt = Math.round(currentDebt + variation);
            document.getElementById('debt').innerText = '$' + displayDebt.toLocaleString();
        }

        fetchDebt(); // initial
        setInterval(fetchDebt, 1000);
        setInterval(animateDebt, 1000 / 60);
    </script>
</head>
<body>
    <div class='container'>
        <h1>Current US National Debt</h1>
        <div id='debt' class='debt'>${{ debt }}</div>
        <p>Source: <a href='https://fiscaldata.treasury.gov/api-documentation/' target='_blank'>U.S. Treasury API</a></p>
    </div>
</body>
</html>
"""

def fetch_debt():
    global last_debt
    url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny"
    params = {"sort": "-record_date", "page[size]": 1}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data['data']:
            with debt_lock:
                last_debt = int(float(data['data'][0]['tot_pub_debt_out_amt']))
    except Exception as e:
        print(f"Error fetching debt: {e}")
        with debt_lock:
            last_debt = 0

def increase_debt():
    global last_debt
    updates_per_second = 60
    base_increment = rate_per_second / updates_per_second
    while True:
        time.sleep(1 / updates_per_second)
        variation = random.uniform(-0.1, 0.1) * base_increment
        with debt_lock:
            last_debt += int(base_increment + variation)

@app.route('/')
def index():
    with debt_lock:
        current_debt = last_debt
    return render_template_string(TEMPLATE, debt=f"{current_debt:,}")

@app.route('/get_debt')
def get_debt():
    with debt_lock:
        current_debt = last_debt
    return {"debt": f"{current_debt:,}"}

if __name__ == '__main__':
    fetch_debt()
    threading.Thread(target=increase_debt, daemon=True).start()
    app.run(debug=True)
