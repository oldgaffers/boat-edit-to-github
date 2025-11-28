import json
import base64
import json
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
    return [row for row in members if f"{row['Firstname']} {row['Lastname']}".upper()==name]

def get_member_by_id(gold_id, members):
    m = [m for m in members if m['ID'] == gold_id]
    if len(m) > 0:
        return m[0]
    return None

def owner_record(o, members):
    owner = {**o}
    if 'id' in owner:
        member = get_member_by_id(owner['id'], members)
        if member['Status'] in ['Deceased', 'Left OGA']:
            del owner['id']
            del owner['member']
            owner['name'] = f"{member['Firstname']} {member['Lastname']}".title()
        return owner
    if 'end' in owner: # leave names in if not current
        return owner
    if 'start' in owner and int(owner['start']) < 1963: # probably not a member 
        return owner
    name = owner.get('name', '').upper().strip()
    l = get_members_by_name(name, members)
    if len(l) != 1:
        return owner # current owner is not a member or the name didn't match
    member = l[0]
    if member['Status'] in ['Deceased', 'Left OGA']:
        return owner
    del owner['name']
    owner['id'] = member['ID']
    owner['member'] = member['Member Number']
    owner['note'] = 'please check this is not a namesake'
    return owner

def make_boat_change_record(body):
    members = json_from_object('boatregister', 'gold/latest.json')
    boat = body['new']
    if 'ownerships' in boat:
        boat['ownerships'] = [owner_record(o, members) for o in boat['ownerships']]
    b64 = base64.b64encode(json.dumps(boat).encode('utf-8'))
    if 'newItems' in body:
        n = json.dumps(body['newItems'])
    else:
        n = ''
    return {
        'ref': 'main',
        'inputs': {
            'oga_no': f"{boat['oga_no']}",
            'data': b64.decode('ascii'),
            'email': body.get('email', 'boatregister@oga.org.uk'),
            'new': n
        }
    }

def make_merge_change(body):
    change = { 'merge': body['merge'], 'keep': body['keep'], 'field': body['field'] }
    b64 = base64.b64encode(json.dumps(change).encode('utf-8'))
    return {
        'ref': 'main',
        'inputs': {
            'id': f"{body['id']}",
            'data': b64.decode('ascii'),
            'email': body.get('email', 'boatregister@oga.org.uk'),
        }
    }

def deliver(body, data, outcome):
    r = ssm.get_parameter(Name='GITHUB_TOKEN', WithDecryption=True)
    github_token = r['Parameter']['Value']
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.ok:
        return {
            'statusCode': 200,
            'body': json.dumps(outcome)
        }
    print('error', response.text)
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }

def lambda_handler(event, context):
    # print(json.dumps(event))
    if 'body' in event:
        body = json.loads(event['body'])
        if 'new' in body:
            data = make_boat_change_record(body)
            print(data)
            useChanges = False
            if 'changes' in body and useChanges:
                b64 = base64.b64encode(json.dumps(body['changes']).encode('utf-8'))
                data['inputs']['changed_fields'] = b64.decode('ascii')
            return deliver(body, data, f"pr requested for {body['new']['oga_no']}")
        elif 'merge' in body:
            data = make_merge_change(body)
            return deliver(body, data, 'pr requested for a non-boat change')
        else:
            print('unrecognised body', json.dumps(body))
    else:
        print('unrecognised event', json.dumps(event))
    return {
        'statusCode': 500,
        'body': json.dumps('something went wrong')
    }
