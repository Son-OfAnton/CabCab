#!/usr/bin/env python3

import json
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Path to the JSON database file
DB_FILE = 'data/db.json'

def read_db():
    """Read the database from the JSON file."""
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def write_db(data):
    """Write data to the JSON file."""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def get_root():
    """Get the entire database."""
    return jsonify(read_db())

@app.route('/<collection>', methods=['GET', 'POST'])
def manage_collection(collection):
    """Get all items or add a new item to a collection."""
    db = read_db()
    
    # Check if collection exists
    if collection not in db:
        return jsonify({"error": f"Collection '{collection}' not found"}), 404
    
    if request.method == 'GET':
        # Return all items in the collection
        return jsonify(db[collection])
    
    elif request.method == 'POST':
        # Add a new item to the collection
        new_item = request.json
        db[collection].append(new_item)
        write_db(db)
        return jsonify(new_item), 201

@app.route('/<collection>/<item_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_item(collection, item_id):
    """Get, update or delete a specific item."""
    db = read_db()
    
    # Check if collection exists
    if collection not in db:
        return jsonify({"error": f"Collection '{collection}' not found"}), 404
    
    # Find the item by ID
    item_index = None
    for i, item in enumerate(db[collection]):
        if str(item.get('id')) == str(item_id):
            item_index = i
            break
    
    # Return 404 if item not found
    if item_index is None:
        return jsonify({"error": f"Item with ID '{item_id}' not found in '{collection}'"}), 404
    
    if request.method == 'GET':
        # Return the specific item
        return jsonify(db[collection][item_index])
    
    elif request.method == 'PUT':
        # Update the item
        updated_item = request.json
        db[collection][item_index] = updated_item
        write_db(db)
        return jsonify(updated_item)
    
    elif request.method == 'DELETE':
        # Delete the item
        deleted_item = db[collection].pop(item_index)
        write_db(db)
        return jsonify(deleted_item)

@app.route('/<collection>/query', methods=['GET'])
def query_collection(collection):
    """Query items in a collection based on parameters."""
    db = read_db()
    
    # Check if collection exists
    if collection not in db:
        return jsonify({"error": f"Collection '{collection}' not found"}), 404
    
    # Get query parameters
    params = request.args
    
    # Filter items based on parameters
    filtered_items = []
    for item in db[collection]:
        match = True
        for key, value in params.items():
            if key not in item or str(item[key]) != value:
                match = False
                break
        if match:
            filtered_items.append(item)
    
    return jsonify(filtered_items)

if __name__ == '__main__':
    # Make sure the database file exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({
                "users": [],
                "drivers": [],
                "vehicles": [],
                "locations": [],
                "rides": [],
                "payments": []
            }, f, indent=2)
    
    app.run(debug=True, host='0.0.0.0', port=3000)