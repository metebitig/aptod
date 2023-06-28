import random

data = {}
god_exist = random.choice([True, False])
if god_exist:
    data['text']  = 'hello god'
else:
    data['error'] = 'God is not exist'

def function(data, func):
    if data.get("error"):
        print(data['error'])
    else:
        func(data)

def lambda_function(data, func):
    if data.get("error"):
        print(data['error'])
    else:
        func()


def do_print(data):
    print(data['text'])

function(data, do_print)
lambda_function(data, lambda: do_print(data))