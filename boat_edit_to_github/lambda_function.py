import json
import base64
import json
from datetime import datetime, timedelta
import boto3
import requests

ssm = boto3.client('ssm')
s3 = boto3.client('s3')

def json_from_object(bucket, key):
    r = s3.get_object(Bucket=bucket, Key=key)
    text = r["Body"].read().decode('utf-8')
    return json.loads(text)

def add_one_owner_member_data(name, members):
    members = [row for row in members if f"{row['Firstname']} {row['Lastname']}".upper()==name]
    r = []
    for row in members:
        o = {}
        o['member'] = row['Member Number']
        o['id'] = row['ID']
        if len(members) > 1:
            o['ambiguous'] = True
        r.append(o)
    return r

def add_owner_member_data(boat):
    d = datetime.now()
    prev = (d - timedelta(days=1)).date().isoformat()
    members = json_from_object('boatregister', 'gold/latest.json')
    o = []
    for owner in boat['ownerships']:
        if 'id' in owner:
            if 'name' in owner:
                del owner['name']
            o.append(owner)
        elif 'current' in owner and owner['current'] and 'name' in owner:
            name = name = owner['name'].upper().strip()
            del owner['name']
            l = add_one_owner_member_data(name, members)
            if len(l) > 0:
                for m in l:
                    m.update(owner)
                    o.append(m)
            else:
                o.append(owner) # current owner is not a member
        else:
            o.append(owner)
    boat['ownerships'] = o
    return boat

def lambda_handler(event, context):
    print(json.dumps(event))
    body = json.loads(event['body'])
    boat = body['new']
    if 'ownerships' in boat:
        boat = add_owner_member_data(boat)
    oga_no = boat['oga_no']
    if 'email' in body:
        email = body['email']
    else:
        email = 'boatregister@oga.org.uk'
    b64 = base64.b64encode(json.dumps(boat).encode('utf-8'))
    if 'newItems' in body:
        n = json.dumps(body['newItems'])
    else:
        n = ''
    data = {
        'ref': 'main',
        'inputs': {
            'oga_no': f"{oga_no}",
            'data': b64.decode('ascii'),
            'email': email,
            'new': n
        }
    }
    if 'changes' in body:
        b64 = base64.b64encode(json.dumps(body['changes']).encode('utf-8'))
        data['inputs']['changed_fields'] = b64.decode('ascii')
    url = 'https://api.github.com/repos/oldgaffers/boatregister/actions/workflows/crud.yml/dispatches'
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
        print(outcome)
        return {
            'statusCode': 200,
            'body': json.dumps(outcome)
        }
    print('error', response.text)
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }
