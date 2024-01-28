import mysql.connector

# Database connection parameters
host = 'localhost'
user = 'root'
password = '200478503'
database = 'thesis'

# Establish a connection to the MariaDB server
conn = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)

# Create a cursor object to interact with the database
cursor = conn.cursor()

# Define the data you want to insert into the table
data = {
    'username': 'john_doe',
    'mail': 'john@example.com'
}

def insert_data()
# SQL query to insert data into the table
insert_query = "INSERT INTO test (username, mail) VALUES (%(username)s, %(mail)s)"

# Execute the query with the data
cursor.execute(insert_query, data)

# Commit the changes to the database
conn.commit()

# Close the cursor and the database connection
cursor.close()
conn.close()
