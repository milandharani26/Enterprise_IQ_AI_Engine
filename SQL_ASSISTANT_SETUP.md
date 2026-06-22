# SQL Assistant Setup Guide

This guide explains how to properly configure an AI Assistant to query your PostgreSQL/MySQL databases using the `sql_query` tool.

## 1. Create Database Credentials
Before connecting to a database, you must store its credentials securely.
1. Navigate to the **Credentials** page.
2. Click **Add Credential** and select your database provider (e.g., PostgreSQL or MySQL).
3. Fill in your database details:
   - **Host:** e.g., `localhost` or `db.example.com`
   - **Port:** `5432` for PostgreSQL, `3306` for MySQL
   - **Database Name:** The target database you want to query.
   - **Username & Password:** Read-only credentials are highly recommended.
4. Use the **Test Connection** button to ensure the engine can successfully reach the database.
5. Save the credential.

## 2. Configure the Database Connector
Once credentials exist, you must register the database as a connector so the engine can index its schema.
1. Navigate to the **Connectors** page and create a new connector.
2. Select your target database provider.
3. Select the credential you created in Step 1.
4. Click **Sync**. 
   > The engine will securely connect to the database, crawl the schema (tables and columns), and index it into the vector database. This is what allows the assistant to automatically route user questions to the correct tables without needing human intervention.

## 3. Set Up the SQL Assistant
Now you can create an assistant with the `sql_query` tool.
1. Navigate to the **Assistants** page and create a new assistant.
2. **Assign the Tool:** Add the `sql_query` tool to the assistant's tools list. 
   > *Note:* The system automatically handles the prompt injection, tool binding, and LLM context size. You do not need to write complex SQL instructions in your system prompt.

## 4. Add Guardrails (Strict Database-Only Responses)
To ensure your assistant doesn't hallucinate or use its general knowledge to answer specific data questions (e.g., guessing roles instead of querying the database), you must add a Guardrail.

Under the assistant's **Guardrails** section, add the following configuration:

- **Type:** `Data Isolation` or `Content Restriction`
- **Enforcement Level:** `strict`
- **Instructions:** 
  > "Never invent or hallucinate answers. If the user asks for data (like a list of roles, names, or records), you MUST only answer using the exact data returned by the sql_query tool. If the tool returns no data, explicitly state that the information was not found in the database. Do not use your general training knowledge to guess organizational data."

## Usage
Once configured, users can chat with the assistant using natural language:
- *"Give me the count of users in the user table"*
- *"List all the roles in the organization"*

The assistant will automatically embed the question, find the relevant tables using vector search, generate a secure SQL query, execute it against your connection pool, and format the results beautifully in the chat interface!
