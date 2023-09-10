import json
import base64
import json
from datetime import datetime, timedelta
import boto3
import requests

url = 'https://api.github.com/repos/oldgaffers/boatregister/actions/workflows/crud.yml/dispatches'

ssm = boto3.client('ssm')
s3 = boto3.client('s3')

def json_from_object(bucket, key):
    r = s3.get_object(Bucket=bucket, Key=key)
    text = r["Body"].read().decode('utf-8')
    return json.loads(text)

def get_members_by_name(name, members):
    matching = [row for row in members if f"{row['Firstname']} {row['Lastname']}".upper()==name]
    r = []
    for row in matching:
        o = {}
        o['member'] = row['Member Number']
        o['id'] = row['ID']
        r.append(o)
    return r

def owner_record(o, members):
    name = o.get('name', '').upper().strip()
    owner = {**o}
    if 'name' in owner:
        del owner['name']
    if 'id' in owner:
        return owner
    if 'ID' in owner:
        owner['id'] = owner['ID']
        del owner['ID']
        return owner
    else:
        l = get_members_by_name(name, members)
        if len(l) == 0:
            pass # current owner is not a member or the name didn't match, fall to default
        elif len(l) == 1:
            owner['id'] = l[0]['id']
            owner['member'] = l[0]['member']
            return owner
        else:
            owner['might be'] = l
    return { 'name': name.title(), **owner }

def make_change_record(oga_no, body, members):
    boat = body['new']
    if 'ownerships' in boat:
        boat['ownerships'] = [owner_record(o, members) for o in boat['ownerships']]
    if 'email' in body:
        email = body['email']
    else:
        email = 'boatregister@oga.org.uk'
    b64 = base64.b64encode(json.dumps(boat).encode('utf-8'))
    if 'newItems' in body:
        n = json.dumps(body['newItems'])
    else:
        n = ''
    return {
        'ref': 'main',
        'inputs': {
            'oga_no': f"{oga_no}",
            'data': b64.decode('ascii'),
            'email': email,
            'new': n
        }
    }

def deliver(oga_no, data):
    r = ssm.get_parameter(Name='GITHUB_TOKEN', WithDecryption=True)
    github_token = r['Parameter']['Value']
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.ok:
        outcome = f'pr requested for {oga_no}'
        return {
            'statusCode': 200,
            'body': json.dumps(outcome)
        }
    print('error', response.text)
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }

def lambda_handler(event):
    print(json.dumps(event))
    members = json_from_object('boatregister', 'gold/latest.json')
    body = json.loads(event['body'])
    oga_no = body['new']['oga_no']
    data = make_change_record(oga_no, body, members)
    useChanges = False
    if 'changes' in body and useChanges:
        b64 = base64.b64encode(json.dumps(body['changes']).encode('utf-8'))
        data['inputs']['changed_fields'] = b64.decode('ascii')
    return deliver(oga_no, data)