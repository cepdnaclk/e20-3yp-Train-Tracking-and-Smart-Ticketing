import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def set_latest_location(train_name, data):
    r.set(train_name, json.dumps(data))

def get_all_latest_locations():
    keys = r.keys('*')
    data = {}
    for key in keys:
        data[key] = json.loads(r.get(key))
    return data

def get_latest_location(train_name):
    data = r.get(train_name)
    if data:
        return json.loads(data)
    return None
