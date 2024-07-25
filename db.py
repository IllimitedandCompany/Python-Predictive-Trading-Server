from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import asyncio as a
from datetime import datetime, timedelta

uri = "YOURMONGODBPYTHONURI"
client = MongoClient(uri, server_api=ServerApi('1'))

database = client['DATABASENAME']
collection = database['COLLECTION-MAIN']
collection2 = database['DIRECTION-COLLECTION']
collection3 = database['COLLECTION-VISITS']

async def get_connection():
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as err:
        print("Connection to DB error: ", err)

async def create_main_db(var):
    try:
        insert_result = collection.insert_one(var)
        print("Main DB created: ", insert_result)
    except Exception as err:
        print("Failed inserting MAIN DB result: ", err)

async def create_visits_db(var):
    try:
        insert_result = collection3.insert_one(var)
        print("Visits DB created: ", insert_result)
    except Exception as err:
        print("Failed inserting VISITS DB result: ", err)

async def create_dir_db(var):
    try:
        insert_result = collection2.insert_one(var)
        print("Inserted Dir DB result: ", insert_result)
    except Exception as err:
        print("Failed inserting DIR DB result: ", err)
    
async def update_clients(var):
    try:
        collection.update_one(
            {"service": "ILLIMITEDPROVIDED"},
            {"$push": {"clients" : var}}
        )
        print("Successfully updated the database.")
        return True
    except Exception as err:
        print(err, f"(err above) Failed updating clients database.")
        return False

async def update_deploy(token, update):
    try:
        document = collection.find_one({'clients.metaapitoken': token})
        if document:
            collection.update_one(
                {'_id': document['_id']},
                {'$pull': {'clients': {'metaapitoken': token}}}
            )

            collection.update_one(
                {"service": "ILLIMITEDPROVIDED"},
                {"$push": {'clients': update}}
            )
        else:
            return False
        print("Successfully updated the deployment value.")
        return True
    except Exception as err:
        print("Failed updating one deployment.", err)
        return False

async def update_direction(update):
    current_minute = datetime.now().minute
    current_hour = datetime.now().hour
    current_day = datetime.now().strftime('%a').upper()

    timing = f"{current_day}-{current_hour:02}:{current_minute:02}"

    try:
        document = collection2.find_one({'service': "ILLIMITEDPROVIDED-direction-template"})
        if document:
            collection2.update_one(
                {'_id': document['_id']},
                {'$set': {'direction': update }}
            )
            collection2.update_one(
                {'_id': document['_id']},
                {'$set': {'direction_date': timing }}
            )
            print("Successfully updated the direction.")
            return

        else:
            print('DB not found on direction update.')
            return
    except Exception as err:
        print("Failed updating direction.", err)
        return

async def log_db():
    try:
        document = collection.find_one({'service': 'ILLIMITEDPROVIDED'})
        print(document, "Entire collection above.")
    except Exception as err:
        print("Failed logging collection: ", err)

async def check_db(token):
    try:
        document = collection.find_one({'clients.metaapitoken': token})
        if document:
            collection.update_one(
                {'_id': document['_id']},
                {'$pull': {'clients': {'metaapitoken': token}}}
            )
            return True
        else:
            return False
    except Exception as err:
        print("Failed checking db for token: ", err)
        return False

async def clean_db():
    try:
        collection.drop()
        print("Collection (MAIN) dropped successfully.")
    except Exception as err:
        print("Failed at dropping collection: ", err)

async def log_clients():
    try: 
        document = collection.find_one({'service': 'ILLIMITEDPROVIDED'})
        clients = document['clients']
        return (len(clients) + 1)
    except Exception as err:
        print('Failed fetching clients: ', err)

async def return_clients():
    try: 
        document = collection.find_one({'service': 'ILLIMITEDPROVIDED'})
        clients = document['clients']
        return clients
    except Exception as err:
        print('Failed returning clients: ', err)

async def return_direction():
    try: 
        document = collection2.find_one({"service": "ILLIMITEDPROVIDED-direction-template"})
        direction = document['direction']
        #print("DIRECTION: ", direction)
        return direction
    except Exception as err:
        print('Failed returning direction: ', err)

async def return_direction_date():
    try: 
        document = collection2.find_one({'service': 'ILLIMITEDPROVIDED-direction-template'})
        direction_date = document['direction_date']
        #print("DIRECTION DATE: ", direction_date)
        return direction_date
    except Exception as err:
        print('Failed returning clients: ', err)

async def return_the_clients():
    document = collection.find_one({'service': 'ILLIMITEDPROVIDED'})
    clients = document['clients']
    return clients

async def return_visits_count():
    try: 
        document = collection3.find_one({'service': 'ILLIMITEDPROVIDED-visits'})
        print(f"Total visits: {document['visits']}")
        return document['visits']
    except Exception as err:
        print('Failed fetching total visits: ', err)

async def log_visits():
    try: 
        document = collection.find_one({'service': 'ILLIMITEDPROVIDED-visits'})
        print(f"Total visits: {document['visits']}")
    except Exception as err:
        print('Failed fetching total visits: ', err)

async def increase_visits():
    try:
        collection3.update_one(
            {"service": "ILLIMITEDPROVIDED-visits"},
            {
                "$inc": {"visits": 1}
            }
        )
        print("Visits have increased by 1.")
    except Exception as err:
        print("Failed increasing visits: ", err)

# 2024 - ILLIMITEDANDCOMPANY