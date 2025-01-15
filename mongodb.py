from pymongo import MongoClient, UpdateOne
import pandas as pd

def read_all_from_db(dbName, contractName):
    with MongoClient() as client:
        db=client[dbName]
        collection = db[contractName]
    return pd.DataFrame(list(collection.find()))

# dates=pd.date_range('2010-01-01', '2020-12-31')
def readFromDB(dbName, contractName, start=None, end=None)->pd.DataFrame:
    '''   
    Returns a DataFrame from a MongoDB collection. If the collection does not exist
    or contains no data, an empty DataFrame is returned.

    Returned DataFrame's index is set as 'Date' and '_id' is dropped.    
    '''
    try:
        # Using MongoClient context manager to automatically close the connection
        with MongoClient() as client:
            db=client[dbName]
            collection = db[contractName]
            # Check if the collection exists
            if contractName not in db.list_collection_names():
                return pd.DataFrame()  # Return empty DataFrame if collection doesn't exist

            # Retrieve data from MongoDB collection
            if start is None and end is None:
                query = {}  # Retrieve all data
            else:
                start_ts = int(start.timestamp() * 1000)
                end_ts = int(end.timestamp() * 1000)
                query = {"Date": {"$gte": start_ts, "$lte": end_ts}}

            # The return type of a find query in MongoDB is a cursor, which is a database object that provides a stream of documents
            # Converting the Cursor to Dataframe, 1st, we convert the cursor to the list of dictionary.
            # cursor = collection.find(query)
            # df = pd.DataFrame(list(cursor))

            # Fetch data from MongoDB and convert to DataFrame
            df = pd.DataFrame(collection.find(query))

            # unit=ms is requied for the conversation.  if no unit='ms', it returns 1970!

            df.set_index("Date", inplace=True)
            df.drop("_id", axis=1, inplace=True)
        return df
    except Exception as e:        
        print(f"An error occurred: {e}")
        return pd.DataFrame()

def write2Db(dbName, collectionName, df):
    if df.empty:
        return

    # index is Date alreay when get here
    df = df.rename(columns=lambda x: x.replace(".", "_"))
    # resetting the index ensures that the index, Date, is converted into a column and stored properly.
    df = df.reset_index()  # This converts the index into a column
    try:
        with MongoClient() as client:
            collection = client[dbName][collectionName]
            # docs = json.loads(df.reset_index().to_json(orient="records"))
            dict_list = df.to_dict(
                orient="records"
            )  # no index reset. why bother reset index?
            collection.insert_many(dict_list)  # Insert new documents
    except Exception as e:
        print(f"An error occurred: {e}")


def updateDb(db_name, collection_name, df):
    """    
    What upsert=True Does:

    If a document matching the query (in this case, {"Date": date}) exists in the database, it updates that document with the new values.
    If no matching document exists, it creates (inserts) a new document with the data.
    Why upsert=True is Needed Here:

    You are concatenating new_data to all_data, and the combined DataFrame (all_data) may contain rows with dates that do not already exist in the database.
    Without upsert=True, MongoDB would skip the insertion for any rows with dates not found in the database. This would result in incomplete or outdated data.
    By using upsert=True, the database will ensure that all rows in the concatenated DataFrame (all_data) are reflected in the database, whether they already existed or are new.
    When to Use upsert=False:

    Use upsert=False only when you are certain that all the Date values in all_data already exist in the database, and you only need to update them.
    In this case, if a Date value is not found in the database, it would not be inserted, potentially leading to missing data.
    """
    
    if df.empty:
        print("DataFrame is empty. No updates made.")
        return
    # Normalize data to DataFrame format if it's a Series
    if isinstance(df, pd.Series):
        df = df.to_frame()

    # Ensure 'Date' is a column, not an index
    # if "Date" not in df.columns:
    #     if df.index.name == "Date":
    #         df = df.reset_index()  # Convert index to column
    #     else:
    #         raise KeyError("No 'Date' column or index found in DataFrame.")

    df = df.rename(columns=lambda x: x.replace(".", "_"))
    try:
        with MongoClient() as client:
            collection = client[db_name][collection_name]
            # Prepare updates for existing documents
            updates = [
                UpdateOne(
                    # row["Date"] assumes that "Date" is a regular column in the DataFrame. However, in your input DataFrame, "Date" is the index. When you call row["Date"], it raises a KeyError because "Date" is not a column, but the index.
                    # solution: Accessing the Index Value: In pandas, the index value of a row in iterrows() is accessed using row.name.
                    {"Date": date},  #  row.name},  # Match by _id or another unique field
                    {"$set": row.dropna().to_dict()}
                        # "$set": {symbol: row.dropna().to_dict()}
                    ,  # Add or update the 'd' field
                    # Use upsert=False if you are only updating known existing documents.
                    upsert=True,  # Don't insert new documents
                )
                for date, row in df.iterrows()
            ]

            if not updates:  # Ensure updates are not empty
                raise ValueError('updates is empty in updateDb ')
            
            result = collection.bulk_write(updates)
            print(
                f"Modified: {result.modified_count}, Upserts: {result.upserted_count}"
            )
          
    except Exception as e:
        print(f"An error occurred: {e}")