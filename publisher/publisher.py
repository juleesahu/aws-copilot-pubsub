# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# -------------       Imports      ------------------------
from flask import Flask, request, render_template, redirect, url_for
import os
import sys
import json
import uuid
import boto3
import names
import random
import logging

# ------------       Global config        -----------------
app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
aws_region = os.getenv("AWS_DEFAULT_REGION", default='us-east-1')

# ------------    SNS (Message sending)     ---------------
sns_client = boto3.client('sns', region_name=aws_region)
dest_topic_name = 'ordersTopic'
sns_topics_arn = json.loads(os.getenv("COPILOT_SNS_TOPIC_ARNS"))
topic_arn = sns_topics_arn[dest_topic_name]

# ---------    DynamoDB (NoSQL Database)     --------------
dynamodb = boto3.resource('dynamodb', region_name=aws_region)
table_name = os.getenv("ORDERS_TABLE_NAME")
db_table = dynamodb.Table(table_name)

# ----------        Main Page         ---------------------
@app.route('/', methods=["GET", "POST"])
def submit_order():

     # When "Send" button is clicked
    if request.method == 'POST':
        
        # Generate an Id
        id = str(uuid.uuid4())
        
        # Get data from form
        customer = request.form['customer']
        amount = request.form['amount']
        
        # Save the data to a DynamoDB Table
        db_table.put_item(
            Item={
                'id': id,
                'customer': customer,
                'amount': amount,
            }
        )
        logging.info('Request saved in database')
        
        # Send a message to the SNS topic
        sns_client.publish(
            TargetArn=topic_arn,
            Message=json.dumps({
                'customer': customer,
                'amount': amount,
            }),
            MessageAttributes={
                'amount': {
                    'DataType': 'Number',
                    'StringValue': str(amount)
                }
            }
        )
        logging.info(f'Message sent to {topic_arn}')
        
        
        return redirect(url_for('request_page', request_id=id))

    
    # Generate a random name and amount to prepopulate the text box
    name = names.get_full_name()
    amount = round(random.uniform(0, 100), 2)
       
    return render_template('index.html', customer=name, amount=amount)

# ------------      Request Redirection Page      -------------------
@app.route('/request/<uuid:request_id>')
def request_page(request_id):
    response = db_table.get_item(
        Key={ 'id': str(request_id) }
    )
    return render_template('order.html', response=response['Item'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
