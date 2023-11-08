from flask import Flask, render_template, request,session, redirect
from pymysql import connections
import os
import boto3
from config import *
from mysql.connector import connection
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import mysql.connector
import random
import string

app = Flask(__name__)
app.secret_key = 'final'

import secrets

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

@app.route('/register_account', methods=['GET','POST'])
def register_company():
    return render_template('Register.html')

@app.route('/login_account', methods=['GET','POST'])
def login_company():
    return render_template('Login.html')


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
    
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        # Generate a random 6-digit verification code
        verification_code = ''.join(random.choices(string.digits, k=6))

        # Send the verification code via email
        recipient_email = request.form['register-email']
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
    if 'verification_code' in session:
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
    

@app.route('/login_member', methods=['POST','GET'])
def login_member():
    cursor=conn.cursor()

    login_email = request.form['sign-in-email']
    login_password = request.form['sign-in-password']

    # Query the database to check if the email and password match
    query = "SELECT customerId, customerName FROM customer WHERE customerEmail = %s AND customerPassword = %s"
    cursor.execute(query, (login_email, login_password))
    user = cursor.fetchone()

    if user:
        session['user_id'] = user[0]  
        session['user_name'] = user[1]  
        return render_template('Home.html')
    else:
        # Login failed, show an error message
        return render_template('Login.html', error="Invalid email or password.") 
    
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
    return render_template('Property_list_buy.html', property_data=property_data)

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
        p.neighborhoodId, a.agentName, a.agentContact, a.agentEmail, a.agentImage, p.propertyInformation
    FROM property p
    JOIN agent a ON p.agentId = a.agentId
    WHERE p.propertyId = %s
    """, (details_property_id,))
    
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
        property_information=row[21]

        # Fetch associated property images for each property
        cursor.execute("SELECT propertyImage FROM propertyimage WHERE propertyId = %s", (details_property_id,))
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
            "agentImage": agent_image_url,  # Agent image URL
            "propertyInformation": property_information
        }

        # Add the property entry to the list
        property_data.append(property_entry)
        print(property_data)

    return render_template('Property_details.html',property_details=property_data)










if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)






