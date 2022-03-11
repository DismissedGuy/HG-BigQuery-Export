import datetime
import os

import honeygain
from google.cloud import bigquery
from honeygain.schemas import HoneygainBalance, Balance

import config

# allow the lib to find our credentials
creds_path = os.path.join(os.getcwd(), config.GOOGLE_APP_CREDENTIALS)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path

# setup clients
bq = bigquery.Client()
hg = honeygain.Client()

# log into honeygain
if not os.path.isfile('.honeygain_token'):
    print('Logging in with username + password')
    hg.login(config.HG_EMAIL, config.HG_PASS)
    with open('.honeygain_token', 'w+') as token_file:
        token_file.write(hg.token)
else:
    print('Logging in with saved token')
    with open('.honeygain_token', 'r') as token_file:
        hg.token = token_file.read().strip()

TABLE = bq.get_table(config.TARGET_DB)


def add_datapoint(balance: dict, jt_balance: dict):
    now = datetime.datetime.utcnow()
    errors = bq.insert_rows(
        TABLE,
        [
            (now.strftime('%Y-%m-%d %H:%M:%S'), [balance], [jt_balance])
        ]
    )

    if errors:
        raise RuntimeError(errors)

    return True


def get_balance():
    balance: HoneygainBalance = hg.get_balance()

    return {
        'credits': balance.lifetime.credits,
        'usd_cents': balance.lifetime.usd_cents
    }


def get_jt_balance():
    balance: Balance = hg.get_jt_balance()

    return {
        'credits': balance.credits,
        'usd_cents': balance.usd_cents,

        'bonus_credits': balance.bonus_credits,
        'bonus_usd_cents': balance.bonus_usd_cents
    }


if __name__ == '__main__':
    print('Retrieving account balance...')
    try:
        _balance = get_balance()
        _jt_balance = get_jt_balance()
    except honeygain.ClientException as e:
        print(f'ERROR: {e}')

        raise e

    print('Inserting data into BigQuery...')
    add_datapoint(_balance, _jt_balance)

    print('Done!')
