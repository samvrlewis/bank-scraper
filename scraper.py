#!/usr/bin/python3
import os
import datetime
import requests
import json

import pytz
import gspread
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

USER_AGENT = "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36"

SPREADSHEET_NAME = "Networth"
BANK_ACCOUNTS_WORKSHEET_NAME = "bank_accounts"
CREDIT_ACCOUNTS_WORKSHEET_NAME = "credit"
SUPER_ACCOUNTS_WORKSHEET_NAME = "super"

DRIVE_CREDENTIALS_NAME = 'drivecredentials.json'
MB_CREDENTIALS_NAME = 'moneybrilliantcredentials.json'

base_location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

def write_to_spreadsheet(accounts, sheet):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials_file_path = os.path.join(base_location, DRIVE_CREDENTIALS_NAME)
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file_path, scope)

    gc = gspread.authorize(credentials)
    worksheet = gc.open(SPREADSHEET_NAME).worksheet(sheet)
    cols = worksheet.col_count
    row = [datetime.datetime.now(pytz.timezone('Australia/Melbourne')).strftime("%Y-%m-%d %H:%M")] + [0]*(cols-1)

    for account in accounts['accounts']:
        balance = account['balance']
        name = account['site_name'] + "_" + account['display_name']

        try:
            col = worksheet.find(name).col
            row[col-1] = balance
        except gspread.exceptions.CellNotFound:
            print(f"Column {name} not found in {sheet}")

    worksheet.append_row(row)

def get_moneybrilliant_session(username, password):
    session = requests.session()
    session.headers['User-Agent'] = USER_AGENT

    url = "https://api.moneybrilliant.com.au/login"
    login_page_response = session.get(url)
    soup = BeautifulSoup(login_page_response.text, features="html.parser")
    desc = soup.findAll(attrs={"name":"csrf-token"})
    token = desc[0]['content']

    form_data = {"utf8" : "%E2%9C%93", "authenticity_token":  token,
                "user[email]": username,
                "user[password]": password}

    post_resp = session.post(url, data=form_data)

    auth_token = post_resp.text[post_resp.text.find("window.sessionStorage.auth_token"):]
    auth_token = auth_token[auth_token.find("'")+1:]
    auth_token = auth_token[:auth_token.find("'")]

    headers = {"X-User-Email": username, "X-User-Token": auth_token}

    return session, headers

def get_moneybrilliant_login(credentials_path):
    credentials_file_path = os.path.join(base_location, credentials_path)
    with open(credentials_file_path) as f:
        data = json.load(f)

    return data['username'], data['password']

def main():
    username, password = get_moneybrilliant_login(MB_CREDENTIALS_NAME)
    session, headers = get_moneybrilliant_session(username, password)

    # refresh accounts
    session.post("https://api.moneybrilliant.com.au/api/v1/site_accounts/refresh", headers=headers, json={"site_account":{"id":"refresh"}})

    bank_accounts = session.get("https://api.moneybrilliant.com.au/api/v1/bank_accounts", headers=headers).json()
    credit_accounts = session.get("https://api.moneybrilliant.com.au/api/v1/credit_card_accounts", headers=headers).json()
    super_accounts = session.get("https://api.moneybrilliant.com.au/api/v1/investment_accounts", headers=headers).json()

    write_to_spreadsheet(bank_accounts, BANK_ACCOUNTS_WORKSHEET_NAME)
    write_to_spreadsheet(credit_accounts, CREDIT_ACCOUNTS_WORKSHEET_NAME)
    write_to_spreadsheet(super_accounts, SUPER_ACCOUNTS_WORKSHEET_NAME)

if __name__ == "__main__":
    main()