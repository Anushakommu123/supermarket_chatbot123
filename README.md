# Supermarket Shopping Assistant

A beginner-friendly, local supermarket support chatbot built with Python,
Streamlit, Pandas, regular expressions, and standard-library string matching.
It uses no AI models, APIs, keys, paid services, or external databases.

## Features

- Availability, prices, discounts, and available alternatives in the same category.
- Eight product categories, category offers, and searches by budget.
- Budgets use final discounted prices; “under” and “below” exclude the limit,
  while “between” includes both limits. Prices round to two decimal places.
- Product follow-ups, explicit context switching, basic typo and plural handling.
- Chat history, category sidebar, four working quick actions, and Clear Chat.
- CSV validation and readable errors for missing or invalid data.

## Files

```text
supermarket_chatbot/
├── app.py             # Streamlit interface and per-session history/context
├── chatbot.py         # Data loading, validation, matching, and responses
├── products.csv       # Demonstration inventory
├── requirements.txt   # Streamlit and Pandas
├── test_chatbot.py     # Built-in unittest suite
├── README.md
└── .gitignore
```

## Architecture and workflow

The Streamlit app loads the CSV through `SupermarketChatbot`. Each message is
normalized, matched against product and category names, and checked for intent.
Longer product names take precedence over names contained within them. A small
`difflib` correction handles simple spelling mistakes. Specific names override
previous context; pronouns such as “its” reuse the last product. General offers
always search the whole catalogue unless a category is explicitly requested.
The engine returns Markdown, which the interface adds to session chat history.
The engine itself does not import Streamlit and accepts a normal context dictionary.

## Demonstration dataset

The 54 sample products span Fruits, Vegetables, Dairy, Groceries, Snacks,
Beverages, Personal Care, and Household. All prices are in INR. These are fictional
demonstration prices, stock counts, and offers, not live supermarket information.
The original 30 sample records are retained and extended with units and new rows.

Columns: `product_id` (unique ID), `product_name` (unique name), `category`,
`price` (original price), `stock` (nonnegative whole number), `discount`
(percentage from 0 to 100), and `unit` (quantity for the listed price).
Stock greater than zero is available. Selling price is `price * (1 - discount / 100)`.
Available lists and alternatives exclude zero stock; direct price enquiries can
still describe an unavailable item with a stock warning.

To change inventory, edit products.csv and save. The app reloads it on its next
interaction. Invalid data displays an error instead of producing invented answers.

## Windows setup

Install Python 3.11 or newer. Open PowerShell in this project directory.
The existing environment is named `smbotenv`. On a fresh copy, create it:

```powershell
py -m venv smbotenv
```

Activate and install dependencies:

```powershell
.\smbotenv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit (normally http://localhost:8501).
Stop the server with Ctrl+C. If PowerShell blocks activation, activation is optional:

```powershell
.\smbotenv\Scripts\python.exe -m pip install -r requirements.txt
.\smbotenv\Scripts\python.exe -m streamlit run app.py
```

If pip reports a local issuer certificate error, use Windows' certificate store:

```powershell
.\smbotenv\Scripts\python.exe -m pip install --use-feature=truststore -r requirements.txt
```

## Automated tests

```powershell
.\smbotenv\Scripts\python.exe -m unittest -v
```

Tests exercise stock, prices, discounts, categories, budgets, context switching,
overlapping names, unknown inputs, typo matching, and invalid CSV handling.

## Example conversations

```text
Customer: Is milk available?
Assistant: Yes, Milk is available. Milk — ₹30 / 500 ml
Customer: What is its price?
Assistant: Milk — ₹30 / 500 ml
Customer: Is there any discount on it?
Assistant: Currently, there is no discount on Milk.

Customer: Is butter available?
Assistant: Sorry, Butter is currently out of stock. [Lists available dairy alternatives]
Customer: Show me alternatives.
Assistant: Available alternatives in Dairy: [Lists available dairy products]
Customer: Are there any discounted products?
Assistant: Current supermarket offers: [Lists in-stock offers across categories]
```

Also try `Show me dairy products with discounts`, `Show me snacks under 100`,
`products between 50 and 200 rupees`, or `How much does orange juice cost?`.
Check Availability asks for a product name; the other quick actions run searches.
Clear Chat resets history and the remembered product and category.

## Limitations and future improvements

This POC understands English rules and simple spelling variants, not unrestricted
natural language. Ask about one product or category at a time. Unrecognized names
produce a catalogue/help response; ambiguous matches request clarification.
Alternatives share a category and are not nutritional substitutes. There is no
checkout, authentication, live inventory, or persistent chat storage. Future work
could add curated aliases, richer filtering, sorting, and an inventory editor.
