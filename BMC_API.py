from langchain_community.chat_models import AzureChatOpenAI
# from langchain_community.sql_database import SQLDatabase
from langchain.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from flask import Flask, request, jsonify
from sqlalchemy import create_engine
import pyodbc
import os
import urllib
from langchain.prompts import PromptTemplate

app = Flask(__name__)
# 🔹 Step 1: Configure Azure OpenAI
AZURE_OPENAI_KEY = "3a3822cd96a44d89bcb59e5ddda423d8"
AZURE_OPENAI_ENDPOINT = "https://uwucoai4uyaoa01.openai.azure.com/openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-08-01-preview"
AZURE_DEPLOYMENT_NAME = "gpt-35-turbo"

llm = AzureChatOpenAI(
    deployment_name=AZURE_DEPLOYMENT_NAME,
    openai_api_base=AZURE_OPENAI_ENDPOINT,
    openai_api_key=AZURE_OPENAI_KEY,
    openai_api_version="2023-03-15-preview"
)

os.environ["BROWSER"]= r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --incognito"'

# 🔹 Step 2: Connect to SQL Database
server = "eunppbi000sql00.database.windows.net"
database = "EY_BMC_Dashboards"
username = "A3111060-MSP01@ey.net"
password = "#bjrcnW.hUPct5bkuq=jU6M9="
driver = "{ODBC Driver 17 for SQL Server}"

# Azure AD Password Authentication 

conn_str = (
    f"DRIVER={driver};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    f"Authentication=ActiveDirectoryPassword"
)

conn = pyodbc.connect(conn_str)

# Wrap pyodbc connection in LangChain SQLDatabase (Manual Connection) 
class CustomSQLDatabase(): 
    def run(self, command: str): 
        cursor = conn.cursor() 
        cursor.execute(command) 
        rows = cursor.fetchall() 
        cursor.close() 
        return str(rows) 

# Use Custom Database Class 
db = CustomSQLDatabase() 
cursor=conn.cursor()
views = ['EYCOM_PagePerformance', 'EYCOM_VideoPerformance', 'EYCOM_Conversion'] # Replace with your actual view names 
views_str = "', '".join(views) 
# 🔹 Query to get column details for the selected views 
query = f""" SELECT TABLE_NAME AS ViewName, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN ('{views_str}') ORDER BY TABLE_NAME, ORDINAL_POSITION; """
cursor.execute(query)
# Print schema for reference
rows = cursor.fetchall()
# Build a dictionary of view schemas 
schema_dict = {} 
for row in rows: 
    table, column, data_type = row 
    if table not in schema_dict: 
        schema_dict[table] = [f"{column}{data_type}"] 
    else:
        schema_dict[table].append(f"{column} {data_type}") 
    # Convert the schema dictionary into a formatted string 
schema_str = "\n".join( [f"View: {table} ({', '.join(columns)})" for table, columns in schema_dict.items()] )




 

# Function to get AI-generated SQL query and execute it 
# Custom LLM prompt
#query = "How many page views for URL https://www.ey.com/en_gl/careers/interview-tips in the last 7 days?" 
#print(schema_str)

    
@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    natural_query = data.get('natural_query')
    
    
    # Generate SQL query using OpenAI
    sql_query = llm.predict(f"Convert this to a SQL query: +{natural_query}+ if there is country related query then it can be extrated from SUBSTRING([Content URL (evar77)] with special character _ and [Content URL (evar77)])+1,2),'') from EY_pageperformance, also use mapping table AdobeCountryCodeMapping to convert country code to country name for natural query, Do NOT assume extra columns.use proper groupby where needed,use proper casting and conversion, also use [] for column name, also date column is [date] not daten and use Content URL (evar77) for content url,it shoudl be genuine SQL query, no extra special charcter should be added")
    
    # Execute query using CustomSQLDatabase
    result = db.run(sql_query)
    
    # Generate the formatted response using OpenAI
    formatted_response_prompt = (
        f"Given the result {result} from the SQL query, "
        f"generate a formatted response that answers the user's question. +{natural_query}"
    )
    formatted_response = llm.predict(formatted_response_prompt)
    
    return jsonify({"response": formatted_response})

if __name__ == '__main__':
    app.run(debug=True)

# Close connection 
conn.close()


