from flask import Flask, render_template, request,session, redirect,jsonify,url_for
import time 
import os
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import euclidean_distances
from config import *
from mysql.connector import connection
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from Levenshtein import distance
from werkzeug.utils import secure_filename
import json

import mysql.connector
import random
import string
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import nltk
import seaborn as sns
from io import BytesIO
import base64

nltk.download('stopwords')
nltk.download('vader_lexicon')

positive_words = {
    "accessibility": ["accessible", "easy access", "inclusive", "user-friendly", "smooth", "effortless", "convenient", "excellent", "superior", "well-connected", "proximity to amenities", "well-designed"],
    "safety": ["safety", "safe", "secure", "protected", "reliable", "guarded", "sound", "excellent", "commendable", "gated community", "security systems", "well-lit"],
    "convenience": ["convenience", "convenient", "efficiency", "streamlined", "user-friendly", "handy", "time-saving", "simple", "efficient", "superb", "splendid", "nearby services", "easy access to public transport"],
    "traffic": ["traffic", "flow", "smooth", "efficient", "well-organized", "uninterrupted", "easy commute", "excellent", "remarkable", "good road infrastructure", "low congestion"]
}

negative_words = {
    "accessibility": ["barrier", "obstacle", "difficulty", "challenging", "restricted", "cumbersome", "hard to reach", "poor", "inferior", "inaccessible", "remote location", "limited access"],
    "safety": ["danger", "hazard", "risk", "unsafe", "vulnerable", "precarious", "perilous", "poor", "unsatisfactory", "lack of security", "high crime rate", "poor lighting"],
    "convenience": ["inefficient", "complicated", "difficult", "unwieldy", "inconvenient", "time-consuming", "complicated", "poor", "suboptimal", "lack of nearby amenities", "limited public transport options"],
    "traffic": ["congestion", "jam", "gridlock", "slow", "chaotic", "stalled", "delayed", "poor", "unpleasant", "high congestion", "frequent traffic jams", "poor road conditions"]
}

positive_word_weights = {
    "accessible": 1.0,
    "user-friendly": 1.2,
    "excellent": 1.5,
    "well-connected": 1.3,
    "proximity to amenities": 1.4,
    "well-designed": 1.2,
    "safe": 1.3,
    "reliable": 1.2,
    "commendable": 1.4,
    "efficiency": 1.2,
    "streamlined": 1.2,
    "handy": 1.1,
    "time-saving": 1.3,
    "simple": 1.1,
    "efficient": 1.2,
    "superb": 1.4,
    "splendid": 1.3,
    "flow": 1.2,
    "uninterrupted": 1.3,
    "easy commute": 1.4,
    "remarkable": 1.3
}

negative_word_weights = {
    "barrier": -1.0,
    "difficult": -1.2,
    "poor": -1.5,
    "inaccessible": -1.3,
    "remote location": -1.4,
    "danger": -1.3,
    "hazard": -1.2,
    "risk": -1.1,
    "unsafe": -1.2,
    "vulnerable": -1.3,
    "precarious": -1.4,
    "perilous": -1.2,
    "unsatisfactory": -1.5,
    "inefficient": -1.2,
    "complicated": -1.3,
    "unwieldy": -1.2,
    "inconvenient": -1.3,
    "time-consuming": -1.4,
    "suboptimal": -1.3,
    "congestion": -1.2,
    "jam": -1.3,
    "gridlock": -1.4,
    "slow": -1.2,
    "chaotic": -1.3,
    "stalled": -1.4,
    "delayed": -1.3,
    "unpleasant": -1.2,
    "dangerous": -1.4,
    "lack of security": -1.3,
    "high crime rate": -1.4,
    "poor lighting": -1.2,
    "inefficient": -1.3,
    "limited access": -1.4,
    "limited public transport options": -1.3,
    "high congestion": -1.4,
    "frequent traffic jams": -1.3,
    "poor road conditions": -1.4
}

app = Flask(__name__)
app.secret_key = 'final'



conn = mysql.connector.connect(
    host='localhost',
    username='root',
    password='Tarc@385',
    database='realestate')
# Email server settings
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587  # Replace with your SMTP server's port
EMAIL_USE_TLS = True  # Use TLS (or adjust based on your server's requirements)
EMAIL_USERNAME = 'metroviewacc@gmail.com'
EMAIL_PASSWORD = 'umyw opvi gyre fiqr'


@app.route('/')
def index():
    return render_template('Home.html', number=1)


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('Home.html')

@app.route('/click_home', methods=['GET','POST'])
def click_home():
    properties_details = []
    recommend_properties = session.get('recommend_properties')

    if recommend_properties:
        for property_id in recommend_properties:
            property_detail = fetch_property_details(property_id)
            
            if property_detail:
                properties_details.append(property_detail)

        return render_template('Home.html', recommended_properties=properties_details)

    return render_template('Home.html', recommended_properties=properties_details)

@app.route('/register_account', methods=['GET','POST'])
def register_company():
    return render_template('Register.html')

@app.route('/login_account', methods=['GET','POST'])
def login_company():
    return render_template('Login.html')

@app.route('/neighborhood_page', methods=['GET','POST'])
def neighborhood_page():
    return render_template('Neighborhood.html')

def send_email(subject, recipient, verification_code):
    # Create the message
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USERNAME
    msg['To'] = recipient
    msg['Subject'] = subject

    # Email body with verification code
    body = f'Your verification code is: {verification_code}'
    msg.attach(MIMEText(body, 'plain'))

    # Connect to the email server and send the email
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USERNAME, recipient, msg.as_string())
        server.quit()
        print('Email sent successfully')
        return True
    except Exception as e:
        print(f'Error sending email: {str(e)}')
        return False
    
def email_exists(email):
    cursor=conn.cursor()
    sql = "SELECT COUNT(*) as count FROM customer WHERE customerEmail = %s"
    cursor.execute(sql, (email,))
    result = cursor.fetchone()
    return result[0]
    
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        # Generate a random 6-digit verification code
        verification_code = ''.join(random.choices(string.digits, k=6))

        # Send the verification code via email
        recipient_email = request.form['register-email']
        if email_exists(recipient_email) >0:
            error_message = '*Email already exists. Please use a different email address.'
            return render_template('Register.html', error_message=error_message)
        print("Recipient Email:", recipient_email)  # Add this line to print the recipient email

        if send_email('Verification Code', recipient_email, verification_code):
            # Store the verification code in a session
            session['verification_code'] = verification_code
            session['register-full-name'] = request.form['register-full-name']
            session['register-email'] = request.form['register-email']
            session['register-phone'] = request.form['register-phone']
            session['register-password'] = request.form['register-password']
            return render_template('RegisterVerification.html')
        else:
            return 'Failed to send the verification code. Please try again.'
        

@app.route('/verify', methods=['POST','GET'])
def verify():
    cursor = conn.cursor()  # Define cursor within the verify function
    user_verification_code = request.form['register-verification']
    stored_verification_code = session.get('verification_code')

    if user_verification_code == stored_verification_code:
        # Verification successful, insert user data into the database
        stored_customerName = session.get('register-full-name')
        stored_customerEmail = session.get('register-email')
        stored_customerPhone = session.get('register-phone')
        stored_customerPassword = session.get('register-password')

        # Insert data into the 'customer' table
        insert_query = "INSERT INTO customer (customerName, customerEmail, customerPhone, customerPassword) VALUES (%s, %s, %s, %s)"
        data = (stored_customerName, stored_customerEmail, stored_customerPhone, stored_customerPassword)

        cursor.execute(insert_query, data)
        conn.commit()

        return render_template('Home.html')
    else:
        return render_template('RegisterVerification.html',msg="Invalid verification code.")
    
    
@app.route('/resend_code', methods=['POST','GET'])
def resend_code():
    print("Resend code route triggered.")
    stored_verification_code = session.get('verification_code')
    print("Code:",stored_verification_code)
    if stored_verification_code:
        # Generate a new random 6-digit verification code
        new_verification_code = ''.join(random.choices(string.digits, k=6))
        
        # Send the new verification code via email
        recipient_email = session.get('register-email')  # Get the recipient's email from the session
        if send_email('Verification Code', recipient_email, new_verification_code):
            session['verification_code'] = new_verification_code  # Update the verification code in the session
            print('Verification code sent successfully.')
            return render_template('RegisterVerification.html')
        else:
            return 'Failed to send the verification code. Please try again.'
    else:
        return 'No existing verification code found. Please try the initial registration.'
    
@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():
    return render_template("forgotPassword.html")

@app.route('/verify_email', methods=['GET','POST'])
def verify_email():
    cursor=conn.cursor()

    verifyEmail = request.form['forgot-email']

    # Check if the email exists in the database
    cursor.execute('SELECT customerId FROM customer WHERE customerEmail = %s', (verifyEmail,))
    result = cursor.fetchone()
    if result:
        verification_code = ''.join(random.choices(string.digits, k=6))
        print("Recipient Email:", verifyEmail)  # Add this line to print the recipient email

        if send_email('Verification Code', verifyEmail, verification_code):
            # Store the verification code in a session
            session['forgot_email']=verifyEmail
            session['verification_code'] = verification_code
        return render_template('forgot_verification.html',verifyEmail=verifyEmail,customerId=result[0])
    else:
        return render_template('forgotPassword.html',errorMessage="Email not found. Please enter a valid email address.",)

@app.route('/verify_forgot_code', methods=['GET','POST'])
def verify_forgot_code():
    verification_code=session.get('verification_code')
    cursor=conn.cursor()

    user_verification_code = request.form['forgot-verification']
    verifyEmail=session.get('forgot_email')
    cursor.execute('SELECT customerId FROM customer WHERE customerEmail = %s', (verifyEmail,))
    result = cursor.fetchone()
    forgot_user_id = result[0]
    session['forgot_id']=forgot_user_id
    forgot_email=request.form['forgot-email']
    if user_verification_code ==verification_code:
        return render_template('resetPassword.html',forgot_user_id=forgot_user_id,forgot_email=forgot_email)
    else:
        return render_template('forgot_verification.html',errorMessage="Invalid Verification Code, Please enter again")
    
@app.route('/resend_forgot_code', methods=['POST','GET'])
def resend_forgot_code():
    print("Resend code route triggered.")
    new_verification_code = ''.join(random.choices(string.digits, k=6))
    forgot_email=session.get('forgot_email')
    print("Forgot Email:",forgot_email)
    if send_email('Verification Code', forgot_email, new_verification_code):
        session['verification_code'] = new_verification_code  # Update the verification code in the session
        print('Verification code sent successfully.')
        return render_template('forgot_verification.html')
    else:
        return 'Failed to send the verification code. Please try again.'
    
@app.route('/reset_password', methods=['POST'])
def reset_password():
    try:
        forgot_user_id = session.get('forgot_id')
        print("Forgot Id:",forgot_user_id)
        reset_password = request.form['input-reset-new-password']
        new_reset_password = request.form['input-reset-confirm-password']

        # Validate if passwords match
        if reset_password != new_reset_password:
            error_message = "Passwords do not match. Please try again."
            return render_template('resetPassword.html', error_message=error_message)

        cursor = conn.cursor()

        # Update the password in the customer table
        update_query = "UPDATE customer SET customerPassword = %s WHERE customerId = %s"
        cursor.execute(update_query, (reset_password, forgot_user_id))

        conn.commit()
        cursor.close()

        return render_template("Login.html")
    except Exception as e:
        return f"An error occurred: {str(e)}"


def fetch_property_details(property_id):
    # Fetch property details
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM property WHERE propertyId = %s", (property_id,))
    property_row = cursor.fetchone()

    # Check if the property exists
    if not property_row:
        return None

    property_id, property_title, property_address, property_price, property_type, furniture, built_in_size, built_in_price, \
    property_status, facility, bathroom, bedroom, house_hold, land_title, type_title, posted_date, neighborhood_id, \
    agent_name, agent_contact, agent_email, agent_image = property_row + (None,)

    # Fetch one associated property image for each property
    cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s LIMIT 1", (property_id,))
    # Convert bytes to a regular string for property image URL
    property_image = cursor.fetchone()
    property_image_url = property_image[0].decode('utf-8').replace("\\", "/").replace("static/", "") if property_image else None

    # Create a dictionary for the property details
    property_details = {
        'property_id': property_id,
        'property_title': property_title,
        'property_address': property_address,
        'property_price': property_price,
        'property_type': property_type,
        'furniture': furniture,
        'built_in_size': built_in_size,
        'built_in_price': built_in_price,
        'property_status': property_status,
        'facility': facility,
        'bathroom': bathroom,
        'bedroom': bedroom,
        'house_hold': house_hold,
        'land_title': land_title,
        'type_title': type_title,
        'posted_date': posted_date,
        'neighborhood_id': neighborhood_id,
        'agent_name': agent_name,
        'agent_contact': agent_contact,
        'agent_email': agent_email,
        'agent_image': agent_image,
        'property_image': property_image_url,
    }

    return property_details

@app.route('/login_member', methods=['POST', 'GET'])
def login_member():
    # Assuming 'conn' is your database connection
    cursor = conn.cursor()

    try:
        login_email = request.form['sign-in-email']
        login_password = request.form['sign-in-password']

        # Query the database to check if the email and password match
        query = """SELECT customerId, customerName, customerPicture FROM customer 
        WHERE customerEmail = %s AND customerPassword = %s"""
        cursor.execute(query, (login_email, login_password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            user_images = user[2]

            if user_images is not None:
                user_image_url = user_images.decode('utf-8').replace("\\", "/").replace("static/", "")
                session['user_profile_picture'] = user_image_url

                # Call the recommend_properties function with the logged-in user's ID
                recommended_properties = recommend_properties_content_based(user[0])
                session['recommend_properties'] = recommended_properties

                # Fetch property details for recommended properties
                properties_details = []

                if recommended_properties:
                    for property_id in recommended_properties:
                        property_detail = fetch_property_details(property_id)
                        if property_detail:
                            properties_details.append(property_detail)

                return render_template('Home.html', recommended_properties=properties_details)
            else:
                recommended_properties = recommend_properties_content_based(user[0])
                session['recommend_properties'] = recommended_properties

                # Fetch property details for recommended properties
                properties_details = []

                if recommended_properties:
                    for property_id in recommended_properties:
                        property_detail = fetch_property_details(property_id)
                        if property_detail:
                            properties_details.append(property_detail)
                return render_template('Home.html', recommended_properties=properties_details)
        else:
            # Login failed, show an error message
            return render_template('Login.html', error="Invalid email or password.")
    finally:
        cursor.close()

@app.route('/logout', methods=['POST','GET'])
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_profile_picture',None)

    return render_template('Home.html')

@app.route('/add_neighborhood', methods=['POST'])
def add_neighborhood():
    cursor = conn.cursor()
    if 'image' not in request.files:
        return 'No file part'

    neighborhood_id=request.form.get('neighborhoodId')
    neighborhood_name = request.form.get('neighborhoodName')
    city = request.form.get('city')
    state = request.form.get('state')
    description = request.form.get('description')

    # Create a directory to save agent images
    agent_image_directory = os.path.join("static/uploads/neighborhood")
    os.makedirs(agent_image_directory, exist_ok=True)

    # Initialize a list to store image file paths
    image_paths = []

    # Process uploaded agent images
    files = request.files.getlist('image')  # Use getlist to handle multiple files

    for file in files:
        if file.filename == '':
            continue

        # Construct the file path based on the agent ID and the file name
        filename = os.path.join("static/neighborhood", f"neighborhood_{neighborhood_id}", file.filename)

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Save the uploaded file
        file.save(filename)

        # Add the image file path to the list
        image_paths.append(filename)

    # Insert agent details and image file paths into the database
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO neighborhood (neighborhoodId,neighborhoodName, city, state, description,neighborhoodImage) VALUES (%s,%s, %s, %s, %s,%s)",
        (neighborhood_id,neighborhood_name, city, state, description, ",".join(image_paths))
    )
    conn.commit()

    return 'Neighborhood information and images uploaded successfully'
    
def save_property_and_images(property_data, files):
    cursor = conn.cursor()

    # Check if builtInPrice is a valid integer before inserting
    if property_data['built_in_size'].isdigit():
        property_data['built_in_size'] = int(property_data['built_in_size'])
    else:
        # Handle the case where the input is not a valid integer
        return 'Invalid input for builtInPrice'

    # Insert property information into the database
    cursor.execute("""
        INSERT INTO property 
        (propertyId, propertyTitle, propertyAddress, propertyPrice, propertyType, furnishing, builtInSize, propertyStatus, facility, bathroom, bedroom, propertyHold,landTitle,propertyTitleType,postedDate,propertyInformation) 
        VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s,%s)
    """, (
        property_data['property_id'], property_data['property_title'], property_data['property_address'],
        property_data['property_price'], property_data['property_type'], property_data['furnishing'],
        property_data['built_in_size'], property_data['property_status'], property_data['facility'],
        property_data['bathroom'], property_data['bedroom'], property_data['property_hold'],
        property_data['land_title'], property_data['property_title_type'], property_data['postedDate'],
        property_data['property_information']
    ))
    conn.commit()

    # Create a directory for property images
    image_dir = os.path.join("static/uploads", f"property_{property_data['property_id']}")
    os.makedirs(image_dir, exist_ok=True)

    for file in files:
        if file.filename == '':
            continue

        # Construct the file path based on the property ID and the file name
        filename = os.path.join(image_dir, file.filename)

        # Save the uploaded file
        file.save(filename)

        # Insert the image file path and property ID into the database
        cursor.execute("INSERT INTO propertyimage (propertyId, propertyImage) VALUES (%s, %s)",
                       (property_data['property_id'], filename))
        conn.commit()

    cursor.close()

    return 'Property information and images uploaded successfully'


def save_agent_and_images(agent_data, files):
    cursor = conn.cursor()

    # Get agent information from the form
    agent_id = agent_data['agentId']
    agent_name = agent_data['agent_name']
    agent_contact = agent_data['agent_contact']
    agent_email = agent_data['agent_email']
    agency_name = agent_data['agency_name']

    # Create a directory to save agent images
    agent_image_directory = os.path.join("static/uploads/agents")
    os.makedirs(agent_image_directory, exist_ok=True)

    # Initialize a list to store image file paths
    image_paths = []

    # Process uploaded agent images
    for file in files:
        if file.filename == '':
            continue

        # Construct the file path based on the agent ID and the file name
        filename = os.path.join("static/uploads", f"agent_{agent_id}", file.filename)

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Save the uploaded file
        file.save(filename)

        # Add the image file path to the list
        image_paths.append(filename)

    # Insert agent details and image file paths into the database
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO agent (agentName, agentContact, agentEmail, agencyName, agentImage) VALUES (%s, %s, %s, %s, %s)",
        (agent_name, agent_contact, agent_email, agency_name, ",".join(image_paths))
    )
    conn.commit()

    cursor.close()

    return 'Agent information and images uploaded successfully'


@app.route('/upload_combined', methods=['POST', 'GET'])
def upload_combined():
    if request.method == 'POST':
        if 'file' not in request.files or 'agentFile' not in request.files:
            return redirect(request.url)

        # Property data
        property_data = {
            'property_id': request.form.get('property_id'),
            'property_title': request.form.get('property_title'),
            'property_address': request.form.get('property_address'),
            'property_price': request.form.get('property_price'),
            'property_type': request.form.get('property_type'),
            'furnishing': request.form.get('furnishing'),
            'built_in_size': request.form.get('built_in_size'),
            'property_status': request.form.get('property_status'),
            'facility': request.form.get('facility'),
            'bathroom': request.form.get('bathroom'),
            'bedroom': request.form.get('bedroom'),
            'property_hold': request.form.get('property_hold'),
            'land_title': request.form.get('land_title'),
            'property_title_type': request.form.get('property_title_type'),
            'postedDate': request.form.get('postedDate'),
            'property_information': request.form.get('property_information'),
        }

        # Agent data
        agent_data = {
            'agentId': request.form.get('agentId'),
            'agent_name': request.form.get('agent_name'),
            'agent_contact': request.form.get('agent_contact'),
            'agent_email': request.form.get('agent_email'),
            'agency_name': request.form.get('agency_name'),
        }

        # Files
        property_files = request.files.getlist('file')  # Use getlist to handle multiple files
        agent_files = request.files.getlist('agentFile')  # Use getlist to handle multiple files

        # Save both property and agent information and images
        save_property_and_images(property_data, property_files)
        save_agent_and_images(agent_data, agent_files)

        return 'Property and agent information along with images uploaded successfully'
    else:
        return render_template('uploadCombine.html')
    
@app.route('/upload', methods=['POST', 'GET'])
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        files = request.files.getlist('file')  # Use getlist to handle multiple files

        property_id = request.form.get('property_id')  # Adjust based on your input field
        property_title = request.form.get('property_title')
        property_address = request.form.get('property_address')
        property_price = request.form.get('property_price')
        property_type = request.form.get('property_type')
        furnishing = request.form.get('furnishing')
        built_in_size = request.form.get('built_in_size')
        built_in_price = request.form.get('built_in_price')
        property_status = request.form.get('property_status')
        facility = request.form.get('facility')
        bathroom = request.form.get('bathroom')
        bedroom = request.form.get('bedroom')
        property_hold = request.form.get('property_hold')
        land_title=request.form.get('land_title')
        property_title_type=request.form.get('property_title_type')
        property_information=request.form.get('property_information')
        postedDate=request.form.get('postedDate')


        # Check if builtInPrice is a valid integer before inserting
        if built_in_size.isdigit():
            built_in_size = int(built_in_size)
        else:
        # Handle the case where the input is not a valid integer
            return 'Invalid input for builtInPrice'
        cursor = conn.cursor()

        # Insert property information into the database
        cursor.execute("INSERT INTO property (propertyId, propertyTitle, propertyAddress, propertyPrice, propertyType, furnishing, builtInSize, propertyStatus, facility, bathroom, bedroom, propertyHold,landTitle,propertyTitleType,postedDate,propertyInformation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s,%s)",
                       (property_id, property_title, property_address, property_price, property_type, furnishing, built_in_size, property_status, facility, bathroom, bedroom, property_hold,land_title,property_title_type,postedDate,property_information))
        conn.commit()

        # Create a directory for property images
        image_dir = os.path.join("static/uploads", f"property_{property_id}")
        os.makedirs(image_dir, exist_ok=True)

        for file in files:
            if file.filename == '':
                continue

            # Construct the file path based on the property ID and the file name
            filename = os.path.join(image_dir, file.filename)

            # Save the uploaded file
            file.save(filename)

            # Insert the image file path and property ID into the database
            cursor.execute("INSERT INTO propertyimage (propertyId, propertyImage) VALUES (%s, %s)", (property_id, filename))
            conn.commit()

        cursor.close()

        return 'Property information and images uploaded successfully'
    else:
        return render_template('upload.html')

@app.route('/upload_agent', methods=['POST'])
def upload_agent():
    cursor = conn.cursor()
    if 'agentFile' not in request.files:
        return 'No file part'

    # Get agent information from the form
    agent_id = request.form.get('agentId')
    agent_name = request.form.get('agentName')
    agent_contact = request.form.get('agentContact')
    agent_email = request.form.get('agentEmail')
    agency_name = request.form.get('agencyName')

    # Create a directory to save agent images
    agent_image_directory = os.path.join("static/uploads/agents")
    os.makedirs(agent_image_directory, exist_ok=True)

    # Initialize a list to store image file paths
    image_paths = []

    # Process uploaded agent images
    files = request.files.getlist('agentFile')  # Use getlist to handle multiple files

    for file in files:
        if file.filename == '':
            continue

        # Construct the file path based on the agent ID and the file name
        filename = os.path.join("static/uploads", f"agent_{agent_id}", file.filename)

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Save the uploaded file
        file.save(filename)

        # Add the image file path to the list
        image_paths.append(filename)

    # Insert agent details and image file paths into the database
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO agent (agentName, agentContact, agentEmail, agencyName, agentImage) VALUES (%s, %s, %s, %s, %s)",
        (agent_name, agent_contact, agent_email, agency_name, ",".join(image_paths))
    )
    conn.commit()

    return 'Agent information and images uploaded successfully'
    
@app.route('/property_list_buy', methods=['GET', 'POST'])
def property_list_buy():
    cursor = conn.cursor()
    
    # Perform a query to retrieve all property information and associated agent details
    cursor.execute("""
    SELECT 
        p.propertyId, p.propertyTitle, p.propertyAddress, p.propertyPrice, p.propertyType, p.furnishing, 
        p.builtInSize, p.builtInPrice, p.propertyStatus, p.facility, p.bathroom, p.bedroom, p.propertyHold,
        p.landTitle,p.propertyTitleType,p.postedDate, 
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage
    FROM property p
    JOIN agent a ON p.agentId = a.agentId
    WHERE p.propertyStatus='Sales'
    """)
    
    property_data = []
    for row in cursor.fetchall():
        # Access data by index
        property_id = row[0]
        property_title = row[1]
        property_address = row[2]
        property_price = row[3]
        property_type = row[4]
        furniture = row[5]
        built_in_size = row[6]
        built_in_price = row[7]
        property_status = row[8]
        facility = row[9]
        bathroom = row[10]
        bedroom = row[11]
        house_hold = row[12]
        land_title=row[13]
        type_title=row[14]
        posted_date=row[15]
        neighborhood_id = row[16]
        agent_name = row[17]
        agent_contact = row[18]
        agent_email = row[19]
        agent_image = row[20]

        # Fetch associated property images for each property
        cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s", (property_id,))
        # Convert bytes to regular strings for property image URLs
        property_images = [image[0].decode('utf-8').replace("\\", "/").replace("static/", "") for image in cursor.fetchall()]

        # Convert bytes to regular strings for agent image URL
        agent_image_url = agent_image.decode('utf-8').replace("\\", "/").replace("static/", "")

        # Format the property price with commas for six or more digits
        try:
            numeric_price = float(property_price)
            if numeric_price >= 100000:
                property_price = "{:,.0f}".format(numeric_price)
        except (ValueError, TypeError):
            pass

        # Create a dictionary to store property and agent data
        property_entry = {
            "propertyId": property_id,
            "propertyTitle": property_title,
            "propertyAddress": property_address,
            "propertyPrice": property_price,
            "propertyType": property_type,
            "furniture": furniture,
            "builtInSize": built_in_size,
            "builtInPrice": built_in_price,
            "propertyStatus": property_status,
            "facility": facility,
            "bathroom": bathroom,
            "bedroom": bedroom,
            "houseHold": house_hold,
            "landTitle": land_title,
            "typeTitle": type_title,
            "postedDate": posted_date,
            "neighborhoodId": neighborhood_id,
            "agentName": agent_name,
            "agentContact": agent_contact,
            "agentEmail": agent_email,
            "propertyImages": property_images,  # List of associated property images
            "agentImage": agent_image_url  # Agent image URL
        }

        # Add the property entry to the list
        property_data.append(property_entry)

    # Close the cursor
    cursor.close()
    
    # Pass the property data to the template for rendering
    return render_template('Property_list_buy.html', property_data=property_data)


@app.route('/property_list_rent', methods=['GET', 'POST'])
def property_list_rent():
    cursor = conn.cursor()
    
    # Perform a query to retrieve all property information and associated agent details
    cursor.execute("""
    SELECT 
        p.propertyId, p.propertyTitle, p.propertyAddress, p.propertyPrice, p.propertyType, p.furnishing, 
        p.builtInSize, p.builtInPrice, p.propertyStatus, p.facility, p.bathroom, p.bedroom, p.propertyHold,
        p.landTitle,p.propertyTitleType,p.postedDate,
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage
    FROM property p
    JOIN agent a ON p.agentId = a.agentId
    WHERE p.propertyStatus='Rent'
    """)
    
    property_data = []
    for row in cursor.fetchall():
        # Access data by index
        property_id = row[0]
        property_title = row[1]
        property_address = row[2]
        property_price = row[3]
        property_type = row[4]
        furniture = row[5]
        built_in_size = row[6]
        built_in_price = row[7]
        property_status = row[8]
        facility = row[9]
        bathroom = row[10]
        bedroom = row[11]
        house_hold = row[12]
        land_title=row[13]
        type_title=row[14]
        posted_date=row[15]
        neighborhood_id = row[16]
        agent_name = row[17]
        agent_contact = row[18]
        agent_email = row[19]
        agent_image = row[20]

        # Fetch associated property images for each property
        cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s", (property_id,))
        # Convert bytes to regular strings for property image URLs
        property_images = [image[0].decode('utf-8').replace("\\", "/").replace("static/", "") for image in cursor.fetchall()]

        # Convert bytes to regular strings for agent image URL
        agent_image_url = agent_image.decode('utf-8').replace("\\", "/").replace("static/", "")

        # Format the property price with commas for six or more digits
        try:
            numeric_price = float(property_price)
            if numeric_price >= 100000:
                property_price = "{:,.0f}".format(numeric_price)
        except (ValueError, TypeError):
            pass

        # Create a dictionary to store property and agent data
        property_entry = {
            "propertyId": property_id,
            "propertyTitle": property_title,
            "propertyAddress": property_address,
            "propertyPrice": property_price,
            "propertyType": property_type,
            "furniture": furniture,
            "builtInSize": built_in_size,
            "builtInPrice": built_in_price,
            "propertyStatus": property_status,
            "facility": facility,
            "bathroom": bathroom,
            "bedroom": bedroom,
            "houseHold": house_hold,
            "landTitle": land_title,
            "typeTitle": type_title,
            "postedDate": posted_date,
            "neighborhoodId": neighborhood_id,
            "agentName": agent_name,
            "agentContact": agent_contact,
            "agentEmail": agent_email,
            "propertyImages": property_images,  # List of associated property images
            "agentImage": agent_image_url  # Agent image URL
        }

        # Add the property entry to the list
        property_data.append(property_entry)

    # Close the cursor
    cursor.close()
    
    # Pass the property data to the template for rendering
    return render_template('Property_list_rent.html', property_data=property_data)

@app.route('/property_details_buy', methods=['GET', 'POST'])
def property_details_buy():
    details_property_id = request.form.get('propertyID')
    print('Your Property ID is %s' % details_property_id)

    cursor = conn.cursor()

    # Perform a query to retrieve all property information and associated agent details
    cursor.execute("""
    SELECT 
        p.propertyId, p.propertyTitle, p.propertyAddress, p.propertyPrice, p.propertyType, p.furnishing, 
        p.builtInSize, p.builtInPrice, p.propertyStatus, p.facility, p.bathroom, p.bedroom, p.propertyHold,
        p.landTitle,p.propertyTitleType,p.postedDate,
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage, p.propertyInformation,a.agentId
    FROM property p
    JOIN agent a ON p.agentId = a.agentId
    WHERE p.propertyId = %s
    """, (details_property_id,))

    property_data = []
    template_name = 'Property_details.html'  # Default template

    for row in cursor.fetchall():
        # Access data by index
        property_status = row[8]

        # Check propertyStatus and set template accordingly
        if property_status == 'Rent':
            template_name = 'Property_details_Rent.html'
        elif property_status == 'Sales':
            template_name = 'Property_details.html'
        else:
            # Handle other cases if needed
            template_name = 'Property_details.html'

        # Fetch associated property images for each property
        cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s", (details_property_id,))
        # Convert bytes to regular strings for property image URLs
        property_images = [image[0].decode('utf-8').replace("\\", "/").replace("static/", "") for image in cursor.fetchall()]

        # Convert bytes to regular strings for agent image URL
        agent_image = row[20]
        agent_image_url = agent_image.decode('utf-8').replace("\\", "/").replace("static/", "")

        # Format the property price with commas for six or more digits
        try:
            numeric_price = float(row[3])
            if numeric_price >= 100000:
                row[3] = "{:,.0f}".format(numeric_price)
        except (ValueError, TypeError):
            pass

        # Create a dictionary to store property and agent data
        property_entry = {
            "propertyId": row[0],
            "propertyTitle": row[1],
            "propertyAddress": row[2],
            "propertyPrice": row[3],
            "propertyType": row[4],
            "furniture": row[5],
            "builtInSize": row[6],
            "builtInPrice": row[7],
            "propertyStatus": row[8],
            "facility": row[9],
            "bathroom": row[10],
            "bedroom": row[11],
            "houseHold": row[12],
            "landTitle": row[13],
            "typeTitle": row[14],
            "postedDate": row[15],
            "neighborhoodId": row[16],
            "agentName": row[17],
            "agentContact": row[18],
            "agentEmail": row[19],
            "propertyImages": property_images,  # List of associated property images
            "agentImage": agent_image_url,  # Agent image URL
            "propertyInformation": row[21],
            "agentId":row[22]
        }

        # Add the property entry to the list
        property_data.append(property_entry)
        print(property_data)

    cursor.execute("""
         SELECT city 
        FROM property p
        LEFT JOIN neighborhood n ON n.neighborhoodId = p.neighborhoodId
        WHERE p.propertyId=%s 
        """, (details_property_id,))
    find_city = cursor.fetchone()

    if property_status == 'Sales':
        cursor.execute("""
    SELECT 
        p.propertyId, 
        p.propertyTitle, 
        p.propertyPrice, 
        MAX(pi.propertyImage) AS propertyImage,
        n.city
    FROM property p
    LEFT JOIN propertyimage pi ON pi.propertyId = p.propertyId
    LEFT JOIN neighborhood n ON n.neighborhoodId = p.neighborhoodId
    WHERE p.propertyStatus = 'Sales' AND n.city = %s AND p.propertyId != %s
    GROUP BY p.propertyId, p.propertyTitle, p.propertyPrice, n.city
    """, (find_city[0], details_property_id))

    else:
        cursor.execute("""
    SELECT 
        p.propertyId, 
        p.propertyTitle, 
        p.propertyPrice, 
        MAX(pi.propertyImage) AS propertyImage,
        n.city
    FROM property p
    LEFT JOIN propertyimage pi ON pi.propertyId = p.propertyId
    LEFT JOIN neighborhood n ON n.neighborhoodId = p.neighborhoodId
    WHERE p.propertyStatus = 'Rent' AND n.city = %s AND p.propertyId != %s
    GROUP BY p.propertyId, p.propertyTitle, p.propertyPrice, n.city
    """, (find_city[0], details_property_id))


    similar_list=[]
    similar_city = cursor.fetchall()

    for row in similar_city:
        similar_dict = {
            'propertyId': row[0],
            'propertyTitle': row[1],
            'propertyPrice': row[2],
            'propertyImage': row[3].decode('utf-8').replace("\\", "/").replace("static/", "") if row[3] else None,
            'city': row[4]
        }

        similar_list.append(similar_dict)
    print("Similar city:",similar_list)
    # Render the template based on propertyStatus
    return render_template(template_name, property_details=property_data,similar_list=similar_list)

def find_similar_neighborhood(user_input):
    similar_neighborhoods = []

    cursor = conn.cursor()

    cursor.execute('SELECT * FROM neighborhood')

    neighborhoods_data = cursor.fetchall()

    for neighborhood in neighborhoods_data:
        try:
            similar_neighborhood = {
                'neighborhoodId': neighborhood[0],  # Assuming the first element is the ID
                'neighborhoodName': neighborhood[1],
                'city': neighborhood[2],
                'state': neighborhood[3]
            }

            # Calculate Levenshtein distance and similarity score for neighborhoodName
            neighborhood_similarity = 1 - (
                distance(similar_neighborhood['neighborhoodName'].lower(), user_input.lower()) /
                max(len(similar_neighborhood['neighborhoodName']), len(user_input))
            )

            # Calculate Levenshtein distance and similarity score for city
            city_similarity = 1 - (
                distance(similar_neighborhood['city'].lower(), user_input.lower()) /
                max(len(similar_neighborhood['city']), len(user_input))
            )
            combined_similarity = (neighborhood_similarity + city_similarity) / 2

            if combined_similarity > 0.4:
                similar_neighborhoods.append(similar_neighborhood)
        except Exception as e:
            print("Error fetching neighborhood data:", e)

    return similar_neighborhoods

# Update the api_find_similar_neighborhoods route
@app.route('/api/find_similar_neighborhoods', methods=['POST'])
def api_find_similar_neighborhoods():
    try:
        user_input = request.form['neighborhood-search']
        print('User Input:',user_input)
        similar_neighborhoods = find_similar_neighborhood(user_input)

        print("Similar Neighborhoods:", similar_neighborhoods)
        return jsonify(similar_neighborhoods)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/neighborhood_result', methods=['GET', 'POST'])
def neighborhood_result():
    neighborhood_input = session.get('neighborhood_input')

    if request.method == 'POST':
        neighborhood_input = request.form.get('neighborhood-search')

    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
        MIN(CASE WHEN p.propertyStatus = 'Sales' THEN p.propertyPrice END) AS minSalesPrice, 
        MAX(CASE WHEN p.propertyStatus = 'Sales' THEN p.propertyPrice END) AS maxSalesPrice,
        MIN(CASE WHEN p.propertyStatus = 'Rent' THEN p.propertyPrice END) AS minRentPrice,
        MAX(CASE WHEN p.propertyStatus = 'Rent' THEN p.propertyPrice END) AS maxRentPrice,
        SUM(CASE WHEN p.propertyStatus = 'Sales' THEN 1 ELSE 0 END) AS salesCount,
        SUM(CASE WHEN p.propertyStatus = 'Rent' THEN 1 ELSE 0 END) AS rentCount,
        n.neighborhoodName, n.city, n.state, n.description, n.neighborhoodImage
        FROM neighborhood n
        LEFT JOIN property p ON n.neighborhoodId = p.neighborhoodId
        WHERE n.neighborhoodName = %s
        GROUP BY n.neighborhoodName, n.city, n.state, n.description, n.neighborhoodImage;
    ''', (neighborhood_input,))

    # Fetch property details
    property_data = cursor.fetchall()

    # Query for review details
    cursor.execute('''
        SELECT 
        r.reviewId, r.reviewDate, r.reviewContent, r.reviewRating,
        r.reviewConvinient, r.reviewTraffic, r.reviewSafety, r.reviewAccessibility,
        c.customerName, c.customerPicture
        FROM review r
        LEFT JOIN customer c ON r.customerId = c.customerId
        WHERE r.neighborhoodId = (SELECT neighborhoodId FROM neighborhood WHERE neighborhoodName = %s)
        ORDER BY r.reviewDate DESC;
    ''', (neighborhood_input,))

    # Fetch review details
    review_data = cursor.fetchall()

    # Calculate average ratings
    overall_rating = 0
    traffic_rating = 0
    safety_rating = 0
    convenient_rating = 0
    accessibility_rating = 0

    # Process and format the data
    formatted_property_data = []
    for row in property_data:
        min_sales_price, max_sales_price, min_rent_price, max_rent_price, sales_count, rent_count, neighborhood_name, city, state, description, neighborhoodImage = row
        neighborhood_image_url=None
        if neighborhoodImage is not None:
            neighborhood_image_url = neighborhoodImage.decode('utf-8').replace("\\", "/").replace("static/", "")
        formatted_property_data.append({
            'minSalesPrice': min_sales_price,
            'maxSalesPrice': max_sales_price,
            'minRentPrice': min_rent_price,
            'maxRentPrice': max_rent_price,
            'salesCount': sales_count,
            'rentCount': rent_count,
            'neighborhoodName': neighborhood_name,
            'city': city,
            'state': state,
            'description': description,
            'neighborhoodImage': neighborhood_image_url,
        })

    formatted_review_data = []
    for row in review_data:
        review_id, review_date, review_content, review_rating, review_convenient, review_traffic, review_safety, review_accessibility, customer_name, customer_picture = row
        customer_image_url=None
        if customer_picture is not None:
            customer_image_url = customer_picture.decode('utf-8').replace("\\", "/").replace("static/", "")

        overall_rating += review_rating
        traffic_rating += review_traffic
        safety_rating += review_safety
        convenient_rating += review_convenient
        accessibility_rating += review_accessibility

        formatted_review_data.append({
            'reviewId': review_id,
            'reviewDate': review_date,
            'reviewContent': review_content,
            'reviewRating': review_rating,
            'reviewConvenient': review_convenient,
            'reviewTraffic': review_traffic,
            'reviewSafety': review_safety,
            'reviewAccessibility': review_accessibility,
            'customerName': customer_name,
            'customerImage': customer_image_url,
        })
    
                # Calculate averages
    total_reviews = len(review_data)
    if total_reviews > 0:
        # Calculate averages
        overall_rating /= total_reviews
        traffic_rating /= total_reviews
        safety_rating /= total_reviews
        convenient_rating /= total_reviews
        accessibility_rating /= total_reviews
    else:
        # Handle the case where there are no reviews
        overall_rating = traffic_rating = safety_rating = convenient_rating = accessibility_rating = 0

    session['neighborhood_input'] = neighborhood_input

    # Pass these calculated values to the template
    return render_template('NeighborhoodDetails.html', property_data=formatted_property_data, review_data=formatted_review_data,
                           overall_rating=overall_rating, traffic_rating=traffic_rating, safety_rating=safety_rating,
                           convenient_rating=convenient_rating, accessibility_rating=accessibility_rating)
    
def preprocess_text(text):
    lower_case = text.lower()
    cleaned_text = lower_case.translate(str.maketrans('', '', string.punctuation))
    tokenized_words = word_tokenize(cleaned_text, "english")
    final_words = [word for word in tokenized_words if word not in stopwords.words('english')]
    lemma_words = [WordNetLemmatizer().lemmatize(word) for word in final_words]
    
    return lemma_words

def sentiment_to_star_rating(score):
    # Normalize the sentiment score to a scale between 0.0 and 5.0
    normalized_score = (score + 1) * 2.5
    # Ensure the result is within the specified range
    return max(0.0, min(5.0, normalized_score))

def identify_aspects(text):
    aspect_scores = {"accessibility": 0, "safety": 0, "convenience": 0, "traffic": 0}
    
    processed_text = preprocess_text(text)
    
    for i in range(len(processed_text)):
        if processed_text[i] == "not" and i + 1 < len(processed_text):
            processed_text[i + 1] = "not_" + processed_text[i + 1]
    
    for aspect in aspect_scores.keys():
        for i in range(len(processed_text)):
            word = processed_text[i]
            if word in positive_words.get(aspect, []):
                aspect_scores[aspect] += positive_word_weights.get(word, 1.0)
            elif word in negative_words.get(aspect, []):
                aspect_scores[aspect] += negative_word_weights.get(word, -1.0)
            elif word in positive_words.get("generic", []) and i + 1 < len(processed_text) and processed_text[i + 1] in ["very", "extremely"]:
                aspect_scores[aspect] += 1.5
            elif word in negative_words.get("generic", []) and i + 1 < len(processed_text) and processed_text[i + 1] in ["very", "extremely"]:
                aspect_scores[aspect] -= 1.5
    
    aspect_scores = {aspect: max(0, min(5, score + 2.5)) for aspect, score in aspect_scores.items()}
    
    return aspect_scores

def analyze_review(review_text):
    analyzer = SentimentIntensityAnalyzer()
    score = analyzer.polarity_scores(review_text)['compound']
    
    # Convert sentiment score to star rating
    star_rating = sentiment_to_star_rating(score)
    
    aspect_scores = identify_aspects(review_text)

    return star_rating, aspect_scores

@app.route('/get_sentiment_rating', methods=['POST','GET'])
def get_sentiment_rating():
    cursor = conn.cursor()
    # Retrieve the customer review from the POST request
    customer_review = request.form.get('review')
    print("Customer Review:", customer_review)
    neighborhood_input = session.get('neighborhood_input')

    # Execute SQL query
    cursor = conn.cursor()
    select_query = "SELECT * FROM neighborhood WHERE neighborhoodName = %s"
    cursor.execute(select_query, (neighborhood_input,))

    # Fetch the result
    neighborhood_data = cursor.fetchone()

    if neighborhood_data:
        neighborhood_id = neighborhood_data[0]
    else:
        # Handle the case where the neighborhood does not exist
        return jsonify({'error': 'Neighborhood not found'})

    user_id = session.get('user_id')
    user_name = session.get('user_name')

    # Perform sentiment analysis using your existing functions
    star_rating, aspect_scores = analyze_review(customer_review)

    insert_query = """
    INSERT INTO review 
    (reviewDate, reviewContent, reviewRating, reviewConvinient, 
    reviewTraffic, reviewSafety, reviewAccessibility, 
    customerId, neighborhoodId) 
    VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(insert_query, (
            customer_review,
            star_rating,
            aspect_scores['convenience'],
            aspect_scores['traffic'],
            aspect_scores['safety'],
            aspect_scores['accessibility'],
            user_id,
            neighborhood_id
        ))
    conn.commit()

    return redirect('/neighborhood_result')

@app.route('/get_user_session', methods=['GET'])
def get_user_session():
    user_id = session.get('user_id')
    return jsonify({'user_id': user_id})

@app.route('/login_review', methods=['POST','GET'])
def login_review():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = conn.cursor()
        query = "SELECT * FROM customer WHERE customerEmail = %s AND customerPassword = %s"
        cursor.execute(query, (email, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            return redirect('/neighborhood_result')
        else:
            # Return a JSON response with an error message
             return jsonify({'error': 'Invalid Email or Password'}), 400
        
@app.route('/user_profile', methods=['POST','GET'])
def user_profile():
    user_id = session.get('user_id')
    user_profile_picture =session.get('user_profile_picture')
    print("user profile:",user_profile_picture)
    cursor=conn.cursor()

    cursor.execute("SELECT customerId, customerName, customerEmail, customerPhone, customerPicture,income, preferredLocation,preferredPropertyType,preferredSize, maximumPrice,preferredBedroom,preferredBathroom,dateOfBirth FROM customer WHERE customerId = %s", (user_id,))
    user_data = cursor.fetchone()  

    if user_data:
        customer_id, customer_name, customer_email, customer_phone, customer_images,income, preferred_Location,preferred_Property_Type,preferred_Size, maximum_Price,preferred_Bedroom,preferred_Bathroom,date_Of_Birth= user_data
        if income:
            formatted_income = round(income, 2)
        else:
            formatted_income=None
        if maximum_Price:
            formatted_maximumPrice=round(maximum_Price,2)
        else:
            formatted_maximumPrice=None
        if customer_images:
            customer_image_url = customer_images.decode('utf-8').replace("\\", "/").replace("static/", "")
        else:
            # Handle the case where customer_images is None (no image data)
            customer_image_url = None
    return render_template("userProfile.html", 
                               customer_id=customer_id,
                               customer_name=customer_name,
                               customer_email=customer_email,
                               customer_phone=customer_phone,
                               customer_images=customer_image_url,
                               income=formatted_income,
                               preferred_Location=preferred_Location,
                               preferred_Property_Type=preferred_Property_Type,
                               preferred_Size=preferred_Size,
                               maximum_Price=formatted_maximumPrice,
                               preferred_Bedroom=preferred_Bedroom,
                               preferred_Bathroom=preferred_Bathroom,
                               date_Of_Birth=date_Of_Birth)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        # Redirect to login page if the user is not logged in
        return redirect(url_for('login'))

    cursor = conn.cursor()
    # Fetch user ID from the session
    user_id = session['user_id']

    # Get form data
    full_name = request.form['full_name']
    phone_number = request.form['phone_number']
    date_of_birth = request.form['dateOfBirth']
    if not date_of_birth:
        date_of_birth = None
    month_income = request.form['monthIncome']
    income = float(month_income) if month_income else None
    preferred_location = request.form['preferred_location']
    preferred_property_type = request.form['preferred_property_type']
    max_price = request.form['max_price']
    max_price = int(max_price) if max_price.isdigit() else None
    preferred_size = request.form['preferred_size']
    preferred_size = int(preferred_size) if preferred_size.isdigit() else None
    num_bedrooms = request.form['num_bedrooms']
    num_bedrooms = int(num_bedrooms) if num_bedrooms.isdigit() else None
    num_bathrooms = request.form['num_bathrooms']
    num_bathrooms = int(num_bathrooms) if num_bathrooms.isdigit() else None

    # Check if a new password is provided
    new_password = request.form.get('password')

    # Initialize a list to store image file paths
    image_paths = []

    files = request.files.getlist('profile_picture')  # Use getlist to handle multiple files
    print("File:",files)
    # Handle profile picture upload
    if files and files[0].filename:
        # Create a directory to save customer images
        customer_image_directory = os.path.join("static/uploads/customer", f"customer_{user_id}")
        os.makedirs(customer_image_directory, exist_ok=True)

        for file in files:
            if file.filename == '':
                continue

            # Construct the file path based on the customer ID and the file name
            filename = secure_filename(file.filename)
            file_path = os.path.join(customer_image_directory, filename)

            # Save the uploaded file
            file.save(file_path)

            # Add the image file path to the list
            image_paths.append(file_path)
    else:
        print("No file uploaded. Fetching original picture path.")
        get_picture_query = """
        SELECT customerPicture FROM customer
        WHERE customerId = %s
        """
        cursor.execute(get_picture_query, (user_id,))
        get_picture = cursor.fetchone()
        print("Original picture path:", get_picture)
        if get_picture and get_picture[0] is not None:
            original_picture_path = get_picture[0].decode('utf-8').replace("\\", "/").replace("static/", "")
            image_paths.append(original_picture_path)
            print("Image paths:", image_paths)

    # Check if a new password is provided
    if new_password:
        # Update the password only if a new password is provided
        update_query_with_password = """
        UPDATE customer SET 
        customerName = %s, customerPhone = %s, dateOfBirth = %s, income = %s, 
        preferredLocation = %s, preferredPropertyType = %s, preferredSize = %s, 
        maximumPrice = %s, preferredBedroom = %s, preferredBathroom = %s, 
        customerPassword = %s, customerPicture = %s 
            WHERE customerId = %s
        """
        cursor.execute(update_query_with_password, (full_name, phone_number, date_of_birth, income,
                                                    preferred_location, preferred_property_type, preferred_size,
                                                    max_price, num_bedrooms, num_bathrooms, new_password,
                                                    ",".join(image_paths), user_id))
    else:
        update_query = """
    UPDATE customer SET 
    customerName = %s, customerPhone = %s, dateOfBirth = %s, income = %s, 
    preferredLocation = %s, preferredPropertyType = %s, preferredSize = %s, 
    maximumPrice = %s, preferredBedroom = %s, preferredBathroom = %s, customerPicture = %s 
        WHERE customerId = %s
"""
        cursor.execute(update_query, (full_name, phone_number, date_of_birth, income,
                                      preferred_location, preferred_property_type, preferred_size,
                                      max_price, num_bedrooms, num_bathrooms, ",".join(image_paths), user_id))

    conn.commit()

    cursor = conn.cursor()
    query = "SELECT customerPicture FROM customer WHERE customerId=%s"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()

    if user and user[0] is not None:
        user_image_url = user[0].decode('utf-8').replace("\\", "/").replace("static/", "")
        session['user_profile_picture'] = user_image_url

    recommended_properties = recommend_properties_content_based(user_id)
    session['recommend_properties'] = recommended_properties

    # Fetch property details for recommended properties
    properties_details = []

    if recommended_properties:
        for property_id in recommended_properties:
            property_detail = fetch_property_details(property_id)
            if property_detail:
                    properties_details.append(property_detail)
    return render_template("Home.html",recommended_properties=properties_details)

@app.route('/search_property', methods=['POST', 'GET'])
def search_property():
    home_state = request.form.get('home-state')
    property_mode = request.form.get('property-mode')
    print("Property Mode:",property_mode)
    property_type = request.form.get('property-type')
    property_content = request.form.get('property-content')

    cursor = conn.cursor()

    # Base query to fetch all properties
    
    if property_mode =='Rent':
        query = """
        SELECT 
        p.propertyId, p.propertyTitle, p.propertyAddress, p.propertyPrice, p.propertyType, p.furnishing, 
        p.builtInSize, p.builtInPrice, p.propertyStatus, p.facility, p.bathroom, p.bedroom, p.propertyHold,
        p.landTitle, p.propertyTitleType, p.postedDate, 
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage
        FROM property p
        JOIN agent a ON p.agentId = a.agentId
        WHERE propertyStatus='Rent' AND 1
        """
    else:
        query = """
        SELECT 
        p.propertyId, p.propertyTitle, p.propertyAddress, p.propertyPrice, p.propertyType, p.furnishing, 
        p.builtInSize, p.builtInPrice, p.propertyStatus, p.facility, p.bathroom, p.bedroom, p.propertyHold,
        p.landTitle, p.propertyTitleType, p.postedDate, 
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage
        FROM property p
        JOIN agent a ON p.agentId = a.agentId
        WHERE propertyStatus='Sales' AND 1
        """


    # Build the WHERE clause based on selected criteria
    conditions = []

    if home_state:
        conditions.append(f"propertyAddress LIKE '%{home_state}%'")

    if property_type:
        conditions.append(f"propertyType = '{property_type}'")

    if property_content:
        conditions.append(f"(propertyTitle LIKE '%{property_content}%' OR propertyAddress LIKE '%{property_content}%' OR neighborhoodId IN (SELECT neighborhoodId FROM neighborhood WHERE neighborhoodName LIKE '%{property_content}%'))")

    if conditions:
        query += " AND " + " AND ".join(conditions)

    cursor.execute(query)

    property_data = []
    for row in cursor.fetchall():
        print(row)
        # Access data by index
        property_id = row[0]
        property_title = row[1]
        property_address = row[2]
        property_price = row[3]
        property_type = row[4]
        furniture = row[5]
        built_in_size = row[6]
        built_in_price = row[7]
        property_status = row[8]
        facility = row[9]
        bathroom = row[10]
        bedroom = row[11]
        house_hold = row[12]
        land_title=row[13]
        type_title=row[14]
        posted_date=row[15]
        neighborhood_id = row[16]
        agent_name = row[17]
        agent_contact = row[18]
        agent_email = row[19]
        agent_image = row[20]

        cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s", (property_id,))
        property_images = [image[0].decode('utf-8').replace("\\", "/").replace("static/", "") for image in cursor.fetchall()]

        agent_image_url = agent_image.decode('utf-8').replace("\\", "/").replace("static/", "")

        try:
            numeric_price = float(property_price)
            if numeric_price >= 100000:
                property_price = "{:,.0f}".format(numeric_price)
        except (ValueError, TypeError):
            pass

        # Create a dictionary to store property and agent data
        property_entry = {
            "propertyId": property_id,
            "propertyTitle": property_title,
            "propertyAddress": property_address,
            "propertyPrice": property_price,
            "propertyType": property_type,
            "furniture": furniture,
            "builtInSize": built_in_size,
            "builtInPrice": built_in_price,
            "propertyStatus": property_status,
            "facility": facility,
            "bathroom": bathroom,
            "bedroom": bedroom,
            "houseHold": house_hold,
            "landTitle": land_title,
            "typeTitle": type_title,
            "postedDate": posted_date,
            "neighborhoodId": neighborhood_id,
            "agentName": agent_name,
            "agentContact": agent_contact,
            "agentEmail": agent_email,
            "propertyImages": property_images,  # List of associated property images
            "agentImage": agent_image_url  # Agent image URL
        }

        # Add the property entry to the list
        property_data.append(property_entry)

    if property_mode == 'Rent':
        return render_template('property_list_rent.html', property_data=property_data)
    else:
        return render_template('property_list_buy.html', property_data=property_data)
    
@app.route('/filter', methods=['POST','GET'])
def filter():
    min_price = request.form.get('select-min-price')
    max_price = request.form.get('select-max-price')
    property_size = request.form.get('property-size')
    property_bedroom = request.form.get('property-bedroom')
    property_mode=request.form.get('property-mode')


    cursor = conn.cursor()

    if property_mode =='Sales':
    # Base query to fetch filtered properties for sales
        query = """
    SELECT 
        p.propertyId, p.propertyTitle, p.propertyAddress, p.propertyPrice, p.propertyType, p.furnishing, 
        p.builtInSize, p.builtInPrice, p.propertyStatus, p.facility, p.bathroom, p.bedroom, p.propertyHold,
        p.landTitle, p.propertyTitleType, p.postedDate, 
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage
    FROM property p
    JOIN agent a ON p.agentId = a.agentId
    WHERE propertyStatus = 'Sales' AND 1
    """
    else:
        query = """
    SELECT 
        p.propertyId, p.propertyTitle, p.propertyAddress, p.propertyPrice, p.propertyType, p.furnishing, 
        p.builtInSize, p.builtInPrice, p.propertyStatus, p.facility, p.bathroom, p.bedroom, p.propertyHold,
        p.landTitle, p.propertyTitleType, p.postedDate, 
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage
    FROM property p
    JOIN agent a ON p.agentId = a.agentId
    WHERE propertyStatus = 'Rent' AND 1
    """

    # Build the WHERE clause based on selected filter criteria
    conditions = []

    if min_price:
        conditions.append(f"propertyPrice >= {min_price}")

    if max_price:
        conditions.append(f"propertyPrice <= {max_price}")

    if property_size:
        # Fix the typo in the value
        conditions.append(f"builtInSize >= {property_size}")

    if property_bedroom:
        # Use placeholder for the value
        conditions.append(f"bedroom >= {property_bedroom}")

    if conditions:
        query += " AND " + " AND ".join(conditions)

    cursor.execute(query)

    property_data = []
    for row in cursor.fetchall():
        # Access data by index
        property_id = row[0]
        property_title = row[1]
        property_address = row[2]
        property_price = row[3]
        property_type = row[4]
        furniture = row[5]
        built_in_size = row[6]
        built_in_price = row[7]
        property_status = row[8]
        facility = row[9]
        bathroom = row[10]
        bedroom = row[11]
        house_hold = row[12]
        land_title=row[13]
        type_title=row[14]
        posted_date=row[15]
        neighborhood_id = row[16]
        agent_name = row[17]
        agent_contact = row[18]
        agent_email = row[19]
        agent_image = row[20]

        cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s", (property_id,))
        property_images = [image[0].decode('utf-8').replace("\\", "/").replace("static/", "") for image in cursor.fetchall()]

        agent_image_url = agent_image.decode('utf-8').replace("\\", "/").replace("static/", "")

        # Create a dictionary to store property and agent data
        property_entry = {
            "propertyId": property_id,
            "propertyTitle": property_title,
            "propertyAddress": property_address,
            "propertyPrice": property_price,
            "propertyType": property_type,
            "furniture": furniture,
            "builtInSize": built_in_size,
            "builtInPrice": built_in_price,
            "propertyStatus": property_status,
            "facility": facility,
            "bathroom": bathroom,
            "bedroom": bedroom,
            "houseHold": house_hold,
            "landTitle": land_title,
            "typeTitle": type_title,
            "postedDate": posted_date,
            "neighborhoodId": neighborhood_id,
            "agentName": agent_name,
            "agentContact": agent_contact,
            "agentEmail": agent_email,
            "propertyImages": property_images,
            "agentImage": agent_image_url  
        }

        property_data.append(property_entry)

    if property_mode =='Sales':
        return render_template('Property_list_buy.html', property_data=property_data)
    else:
        return render_template('Property_list_rent.html', property_data=property_data)
    
@app.route('/neighborhood_property', methods=['GET','POST'])
def neighborhood_property():
    popular_neighborhood = request.args.get('neighborhood')
    print("Popular:", popular_neighborhood)
    
    cursor = conn.cursor()

    # Using parameterized query to avoid SQL injection
    query = """
    SELECT 
        p.propertyId, p.propertyTitle, p.propertyAddress, p.propertyPrice, p.propertyType, p.furnishing, 
        p.builtInSize, p.builtInPrice, p.propertyStatus, p.facility, p.bathroom, p.bedroom, p.propertyHold,
        p.landTitle, p.propertyTitleType, p.postedDate, 
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage
    FROM property p
    JOIN agent a ON p.agentId = a.agentId
    JOIN neighborhood n ON p.neighborhoodId = n.neighborhoodId
    WHERE n.city LIKE %s
    """

    # Use the popular_neighborhood variable as a parameter in the execute method
    cursor.execute(query, ('%' + popular_neighborhood + '%',))

    property_data = []
    for row in cursor.fetchall():
        # Access data by index
        property_id = row[0]
        property_title = row[1]
        property_address = row[2]
        property_price = row[3]
        property_type = row[4]
        furniture = row[5]
        built_in_size = row[6]
        built_in_price = row[7]
        property_status = row[8]
        facility = row[9]
        bathroom = row[10]
        bedroom = row[11]
        house_hold = row[12]
        land_title=row[13]
        type_title=row[14]
        posted_date=row[15]
        neighborhood_id = row[16]
        agent_name = row[17]
        agent_contact = row[18]
        agent_email = row[19]
        agent_image = row[20]

        cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s", (property_id,))
        property_images = [image[0].decode('utf-8').replace("\\", "/").replace("static/", "") for image in cursor.fetchall()]

        agent_image_url = agent_image.decode('utf-8').replace("\\", "/").replace("static/", "")

        try:
            numeric_price = float(property_price)
            if numeric_price >= 100000:
                property_price = "{:,.0f}".format(numeric_price)
        except (ValueError, TypeError):
            pass

        # Create a dictionary to store property and agent data
        property_entry = {
            "propertyId": property_id,
            "propertyTitle": property_title,
            "propertyAddress": property_address,
            "propertyPrice": property_price,
            "propertyType": property_type,
            "furniture": furniture,
            "builtInSize": built_in_size,
            "builtInPrice": built_in_price,
            "propertyStatus": property_status,
            "facility": facility,
            "bathroom": bathroom,
            "bedroom": bedroom,
            "houseHold": house_hold,
            "landTitle": land_title,
            "typeTitle": type_title,
            "postedDate": posted_date,
            "neighborhoodId": neighborhood_id,
            "agentName": agent_name,
            "agentContact": agent_contact,
            "agentEmail": agent_email,
            "propertyImages": property_images,  # List of associated property images
            "agentImage": agent_image_url  # Agent image URL
        }

        property_data.append(property_entry)
    return render_template('property_list_buy.html', property_data=property_data)

def get_data_from_database(user_id):
    # Assuming you have a database connection (conn) established earlier in your code

    cursor = conn.cursor()

    # Use user_id in the SQL query to retrieve customer data
    cursor.execute(
        "SELECT preferredLocation, preferredPropertyType, maximumPrice, preferredBedroom, preferredSize, income FROM customer WHERE customerId=%s",
        (user_id,)
    )
    customer_data = cursor.fetchall()

    # Convert the fetched customer data to a DataFrame
    df_customer = pd.DataFrame(
        customer_data,
        columns=['preferredLocation', 'preferredPropertyType', 'maximumPrice', 'preferredBedroom', 'preferredSize', 'income']
    )

    # Build the SQL query for property data using JOIN clause
    query = """
    SELECT 
        CASE
            WHEN neighborhoodName LIKE %s THEN neighborhoodName
            WHEN city LIKE %s THEN city
            ELSE NULL
        END AS selectedLocation,
        propertyId, propertyType, propertyPrice, bedroom, builtInSize 
    FROM property
    INNER JOIN neighborhood ON property.neighborhoodId = neighborhood.neighborhoodId
    WHERE (neighborhoodName LIKE %s OR city LIKE %s) AND propertyStatus='Sales'
"""

    # Extract 'preferredLocation' from the first tuple in customer_data
    preferred_location = customer_data[0][0]
    print("preferred_location:", preferred_location)

    # Check if 'preferredLocation' is not None before concatenating
    if preferred_location is not None:
        # Execute the query with the tuple of preferred locations
        cursor.execute(query, ('%' + preferred_location + '%', '%' + preferred_location + '%', '%' + preferred_location + '%', '%' + preferred_location + '%'))

        property_data = cursor.fetchall()

        # Convert the fetched property data to a DataFrame
        df_property = pd.DataFrame(
            property_data,
            columns=['selectedLocation', 'propertyId', 'propertyType', 'propertyPrice', 'bedroom', 'builtInSize']
        )

        print("customer data:", df_customer)
        print("property data:", df_property)
        return df_customer, df_property
    else:
        # Handle the case when 'preferredLocation' is None (e.g., return an empty DataFrame)
        return df_customer, pd.DataFrame(columns=['selectedLocation', 'propertyId', 'propertyType', 'propertyPrice', 'bedroom', 'builtInSize'])


def calculate_mortgage(property_prices, margin_finance, tenure_years, interest_rate, incomes):
    if isinstance(property_prices, list):
        # Calculate mortgage for each property price and income in the list
        monthly_payments = []
        dti_ratios = []

        for property_price in property_prices:
            # Calculate loan amount for each property price
            loan_amount = (margin_finance / 100) * property_price

            # Calculate monthly interest rate
            monthly_interest_rate = interest_rate / 100 / 12

            # Calculate number of monthly payments
            number_of_payments = tenure_years * 12

            # Calculate mortgage monthly payment
            monthly_payment = (loan_amount * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** -number_of_payments)
            monthly_payments.append(monthly_payment)

            # Check for zero income to avoid division by zero
            if incomes != 0:
                # Calculate Debt-to-Income (DTI) ratio for each property
                dti_ratio = monthly_payment / incomes
            else:
                # Handle the case where income is zero
                dti_ratio = float('inf')  # Use infinity for DTI ratio in case of zero income
            dti_ratios.append(dti_ratio)

        print("Monthly Payments:", monthly_payments)
        print("DTI Ratios:", dti_ratios)
        return monthly_payments, dti_ratios
    else:
        raise ValueError("Invalid property_prices type. Should be a list.")

def recommend_properties_content_based(user_id, top_n=3, max_dti=0.4):
    # Get customer and property data based on the user_id
    df_customer, df_property = get_data_from_database(user_id)

    print("Customer Data:")
    print(df_customer)

    print("Property Data:")
    print(df_property)

    # Convert 'preferredPrice' and 'propertyPrice' columns to numeric
    df_customer['maximumPrice'] = pd.to_numeric(df_customer['maximumPrice'], errors='coerce')
    df_property['propertyPrice'] = pd.to_numeric(df_property['propertyPrice'], errors='coerce')


    # Merge customer and property data on relevant columns
    merged_data = pd.merge(
        df_customer,
        df_property,
        left_on=['preferredLocation', 'preferredPropertyType', 'preferredBedroom'],
        right_on=['selectedLocation', 'propertyType', 'bedroom'],
        how='inner'
    )

    print("Merged Data After Merge:")
    print(merged_data)

    # Check if there are any rows left after filtering
    if merged_data.shape[0] == 0:
        print("No properties left after filtering. Recommendation not possible.")
        return None

    # Standardize numeric columns for Euclidean distance calculation
    scaler = StandardScaler()
    numeric_columns = ['preferredBedroom', 'preferredSize', 'income', 'bedroom', 'builtInSize', 'propertyPrice']
    merged_data[numeric_columns] = scaler.fit_transform(merged_data[numeric_columns])
    print("Income:", df_customer['income'].iloc[0])
    # Calculate mortgage and DTI ratio
    start_index, end_index = 1, 3
    property_prices = df_property['propertyPrice'].iloc[start_index:end_index + 1].tolist()

    margin_finance = 90
    tenure_years = 35
    interest_rate = 3.85
    merged_data['monthly_payments'], merged_data['dti_ratio'] = calculate_mortgage(property_prices, margin_finance, tenure_years, interest_rate, df_customer['income'].iloc[0])


    # Use Euclidean distance for similarity
    distance_matrix = euclidean_distances(merged_data[['preferredBedroom', 'preferredSize', 'income', 'dti_ratio']],
                                          merged_data[['bedroom', 'builtInSize', 'propertyPrice', 'dti_ratio']])

    # Add a new column 'distance' to merged_data
    merged_data['distance'] = distance_matrix.mean(axis=1)

    # Apply affordability filter based on DTI ratio
    merged_data = merged_data[merged_data['dti_ratio'] <= max_dti]

    # Get the top N properties with the smallest distance
    recommended_properties = merged_data.nlargest(top_n, 'distance')['propertyId'].tolist()

    print("Content-Based Filtering - Recommended Properties:", recommended_properties)
    return recommended_properties

@app.route('/agent_details_buy', methods=['GET', 'POST'])
def agent_details_buy():
    agent_id = request.args.get('agentId')

    # Execute a SELECT query to get agent details based on agentId
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent WHERE agentId = %s", (agent_id,))
    agent_data = cursor.fetchone()

    # Check if agent_data is not None (agent found)
    if agent_data:
        # Access values using integer indices instead of string keys
        agent_id = agent_data[0]
        agent_name = agent_data[1]
        agent_contact = agent_data[2]
        agent_email = agent_data[3]
        agency_name = agent_data[4]
        agent_image = agent_data[5]
        agent_image_url = agent_image.decode('utf-8').replace("\\", "/").replace("static/", "")
        agent_description = agent_data[6]

        # Execute a query to get the count of properties for sale
        cursor.execute("SELECT COUNT(*) FROM property WHERE agentId = %s AND propertyStatus='Sales'", (agent_id,))
        properties_for_sale = cursor.fetchone()[0]

        # Execute a query to get the count of properties for rent
        cursor.execute("SELECT COUNT(*) FROM property WHERE agentId = %s AND propertyStatus='Rent'", (agent_id,))
        properties_for_rent = cursor.fetchone()[0]

        # Execute a query to get property details for sales
        cursor.execute("SELECT propertyId, propertyTitle, propertyPrice, propertyStatus FROM property WHERE agentId = %s AND propertyStatus='Sales'", (agent_id,))
        property_rows = cursor.fetchall()

        properties = []  
        property_status = None

        if property_rows:
            # If there are rows, get property details
            for property_row in property_rows:
                property_id = property_row[0]
                cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s LIMIT 1", (property_id,))
                property_image = cursor.fetchone()
                property_image_url = property_image[0].decode('utf-8').replace("\\", "/").replace("static/", "")

                # Append property details to the list
                properties.append({
                    'property_id': property_id,
                    'property_title': property_row[1],
                    'property_price': property_row[2],
                    'property_status': property_row[3],
                    'property_image_url': property_image_url
                })

            # Set property_status to the status of the first property
            property_status = properties[0]['property_status']

        # Render the template and pass the variables
        return render_template("agentDetails.html",
                               agentId=agent_id,
                               agent_name=agent_name,
                               agent_contact=agent_contact,
                               agent_email=agent_email,
                               agency_name=agency_name,
                               agent_image=agent_image_url,
                               property_status=property_status,
                               agent_description=agent_description,
                               properties=properties,
                               properties_for_sale=properties_for_sale,
                               properties_for_rent=properties_for_rent)

@app.route('/agent_details_rent', methods=['GET', 'POST'])
def agent_details_rent():
    agent_id = request.args.get('agentId')

    # Execute a SELECT query to get agent details based on agentId
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent WHERE agentId = %s", (agent_id,))
    agent_data = cursor.fetchone()

    # Check if agent_data is not None (agent found)
    if agent_data:
        # Access values using integer indices instead of string keys
        agent_id = agent_data[0]
        agent_name = agent_data[1]
        agent_contact = agent_data[2]
        agent_email = agent_data[3]
        agency_name = agent_data[4]
        agent_image = agent_data[5]
        agent_image_url = agent_image.decode('utf-8').replace("\\", "/").replace("static/", "")
        agent_description = agent_data[6]

        # Execute a query to get the count of properties for sale
        cursor.execute("SELECT COUNT(*) FROM property WHERE agentId = %s AND propertyStatus='Sales'", (agent_id,))
        properties_for_sale = cursor.fetchone()[0]

        # Execute a query to get the count of properties for rent
        cursor.execute("SELECT COUNT(*) FROM property WHERE agentId = %s AND propertyStatus='Rent'", (agent_id,))
        properties_for_rent = cursor.fetchone()[0]

        # Execute a query to get property details for sales
        cursor.execute("SELECT propertyId, propertyTitle, propertyPrice, propertyStatus FROM property WHERE agentId = %s AND propertyStatus='Rent'", (agent_id,))
        property_rows = cursor.fetchall()

        properties = []  # List to store property details
        property_status = None  # Initialize property_status to None

        if property_rows:
            # If there are rows, get property details
            for property_row in property_rows:
                property_id = property_row[0]
                cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s LIMIT 1", (property_id,))
                property_image = cursor.fetchone()
                property_image_url = property_image[0].decode('utf-8').replace("\\", "/").replace("static/", "")

                # Append property details to the list
                properties.append({
                    'property_id': property_id,
                    'property_title': property_row[1],
                    'property_price': property_row[2],
                    'property_status': property_row[3],
                    'property_image_url': property_image_url
                })

            # Set property_status to the status of the first property
            property_status = properties[0]['property_status']

        # Render the template and pass the variables
        return render_template("agentDetails.html",
                               agentId=agent_id,
                               agent_name=agent_name,
                               agent_contact=agent_contact,
                               agent_email=agent_email,
                               agency_name=agency_name,
                               agent_image=agent_image_url,
                               property_status=property_status,
                               agent_description=agent_description,
                               properties=properties,
                               properties_for_sale=properties_for_sale,
                               properties_for_rent=properties_for_rent)
    
@app.route('/compare_Analysis', methods=['GET', 'POST'])
def compare_Analysis():
    if request.method == 'POST':
        selected_neighborhoods_json = request.form.get('selectedNeighborhoods')
        print("Selected_neighborhood:", selected_neighborhoods_json)
        selected_neighborhoods = json.loads(selected_neighborhoods_json) if selected_neighborhoods_json else []
        plot_data = generate_plot(selected_neighborhoods)
    else:
        # Default: show all neighborhoods
        plot_data = generate_plot()

    return render_template('compareAnalysis.html', plot_data=plot_data)


def generate_plot(selected_neighborhoods=None):
    file_path = r"C:\Users\user\OneDrive - Tunku Abdul Rahman University College\Documents\Final-Year-Project\prediction.csv"
    data = pd.read_csv(file_path)

    data['Price'] = data['Price'].replace('RM', '', regex=True)
    data['Price'] = data['Price'].replace('[\$,]', '', regex=True).astype(float)
    data['Neighborhood'] = data['Location'].str.split(',').str[0]

    # Handle missing values
    data.dropna(subset=['Price', 'Location'], inplace=True)

    # Filter the data based on selected neighborhoods
    if selected_neighborhoods:
        data = data[data['Neighborhood'].isin(selected_neighborhoods)]

    # Calculate the median price for each neighborhood
    median_prices = data.groupby('Neighborhood')['Price'].median().reset_index()

    # Take the top 10 neighborhoods by median price
    top_neighborhoods = median_prices.nlargest(10, 'Price')['Neighborhood']
    data = data[data['Neighborhood'].isin(top_neighborhoods)]

    # Recalculate the median prices for the top 10 neighborhoods
    median_prices = data.groupby('Neighborhood')['Price'].median().reset_index()

    # Sort the DataFrame by median price in ascending order
    median_prices = median_prices.sort_values(by='Price')

    # Set Matplotlib to use the 'Agg' backend
    plt.switch_backend('Agg')

    # Example: Create a bar chart
    plt.figure(figsize=(12, 8))
    sns.set(style="whitegrid")

    # Assuming you have a 'median_prices' DataFrame
    ax = sns.barplot(x='Neighborhood', y='Price', data=median_prices, palette='viridis')

    for p in ax.patches:
        ax.annotate(f'RM {p.get_height():,.0f}', (p.get_x() + p.get_width() / 2., p.get_height()), ha='center',
                    va='center', fontsize=10, color='black', xytext=(0, 5), textcoords='offset points')

    plt.title('Median Price Range by Neighborhoods') 
    plt.xlabel('Neighborhood')
    plt.ylabel('Median Price (RM)')
    plt.xticks(rotation=45, ha='right')

    # Save the plot to a BytesIO object
    image_stream = BytesIO()
    plt.savefig(image_stream, format='png')
    image_stream.seek(0)
    plot_data = base64.b64encode(image_stream.read()).decode('utf-8')

    plt.close()

    return plot_data

@app.route('/get_all_neighborhoods')
def get_all_neighborhoods():
    file_path = r"C:\Users\user\OneDrive - Tunku Abdul Rahman University College\Documents\Final-Year-Project\prediction.csv"
    data = pd.read_csv(file_path)
    data['Neighborhood'] = data['Location'].str.split(',').str[0]
    # Get all unique neighborhoods from the data
    all_neighborhoods = data['Neighborhood'].unique().tolist()

    return jsonify(all_neighborhoods)

@app.route('/news_pages', methods=['GET', 'POST'])
def news_pages():
    cursor = conn.cursor()

    news_list = []  # List to store news data

    try:
        # Retrieve news data
        cursor.execute(
            """SELECT n.newsId, n.newsTitle, n.newsDate, nc.newsSubTitle, nc.newsImages, nc.newsDescription
               FROM news n
               LEFT JOIN newscontent nc ON nc.newsId = n.newsId
               WHERE nc.newsId IS NOT NULL
               AND nc.newsContentId = (
                   SELECT newsContentId
                   FROM newscontent
                   WHERE newsId = n.newsId
                   LIMIT 1
               )
               ORDER BY n.newsDate DESC"""
        )
        news_data = cursor.fetchall()
        print("news_data", news_data)

        for row in news_data:
            # Access the inner tuple using indices
            news_dict = {
                'newsId': row[0],
                'newsTitle': row[1],
                'newsDate': row[2],
                'newsSubTitle': row[3],
                'newsImages': row[4].decode('utf-8').replace("\\", "/").replace("static/", "") if row[4] else None,
                'newsDescription': row[5]
            }

            news_list.append(news_dict)
            print("news_list", news_list)

    except Exception as e:
        print(f"Error: {str(e)}")

    return render_template("event.html", news_list=news_list)


@app.route('/input_news', methods=['GET', 'POST'])
def input_news():
    message = ""

    if request.method == 'POST':
        # Collect form data
        newsId=request.form.get('newsId')
        newsSubTitle = request.form.get('newsSubTitle')
        newsDescription = request.form.get('newsdescription')

        # Handle image upload
        files = request.files.getlist('newsPicture')
        
        # Create a directory to save news images
        news_image_directory = os.path.join("static/uploads/news")
        os.makedirs(news_image_directory, exist_ok=True)

        # Initialize a list to store image file paths
        image_paths = []

        # Process uploaded news images
        for file in files:
            if file.filename == '':
                continue

            # Construct the file path based on the current timestamp and the file name
            timestamp = int(time.time())  # Use current timestamp to ensure uniqueness
            filename = f"{timestamp}_{secure_filename(file.filename)}"
            filepath = os.path.join(news_image_directory, filename)

            # Save the uploaded file
            file.save(filepath)

            # Add the image file path to the list
            image_paths.append(filepath)

        cursor = conn.cursor()

        try:
            # Insert data into the database
            sql = "INSERT INTO newscontent (newsSubTitle, newsDescription, newsImages,newsId) VALUES (%s, %s, %s,%s)"
            cursor.execute(sql, (newsSubTitle, newsDescription, image_paths[0] if image_paths else None,newsId))
            conn.commit()
            message = "News content inserted successfully"
        except Exception as e:
            conn.rollback()
            message = f"Error: {str(e)}"
        finally:
            # Close the database connection
            cursor.close()
            conn.close()

    return message

@app.route('/news_details', methods=['GET', 'POST'])
def news_details():
    news_id = request.args.get('newsId')

    news_details_list=[]
    cursor = conn.cursor()
    cursor.execute(
    """SELECT n.newsId, n.newsTitle, n.newsDate
       FROM news n
       WHERE n.newsId = %s""", (news_id,)
    )

    result = cursor.fetchone()

    if result:
        news_id, news_title, news_date = result
        cursor.execute("""SELECT nc.newsSubTitle, nc.newsImages, nc.newsDescription
                       FROM newscontent nc
                       WHERE nc.newsId=%s""",(news_id,))
        result_data=cursor.fetchall()
        for row in result_data:
            # Access the inner tuple using indices
            news_dict = {
                'newsSubTitle': row[0],
                'newsImages': row[1].decode('utf-8').replace("\\", "/").replace("static/", "") if row[1] else None,
                'newsDescription': row[2]
            }
            news_details_list.append(news_dict)

    return render_template("eventDetails.html",news_id=news_id, news_title=news_title, news_date=news_date, news_details=news_details_list)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)