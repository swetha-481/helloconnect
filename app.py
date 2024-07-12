
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
from werkzeug.utils import secure_filename
import pyrebase

# change
config = {
    "apiKey" : "AIzaSyAAkqgb_IGBeCygiQG-cs6XELII5Ap3OPs",
    "authDomain" : "fir-auth2-826cc.firebaseapp.com",
    "databaseURL" : "https://fir-auth2-826cc-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId" : "fir-auth2-826cc",
    "storageBucket" : "fir-auth2-826cc.appspot.com",
    "messagingSenderId" : "212779795091",
    "appId" : "1:212779795091:web:a6adda556f9bc8e8938366"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()
auth = firebase.auth()
storage = firebase.storage()

app = Flask(__name__)
port = int(os.environ.get('PORT', 5000))

global userid
userid = None

def create_user(email, password, username, user_type):
    user = auth.create_user_with_email_and_password(email, password)
    global userid
    userid = user['localId']
    db.child("users").child(userid).child("username").set(username)
    db.child("users").child(userid).child("user type").set(user_type)
    print("User created successfully:")

def log_in(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        global userid
        userid = user['localId']
        print("User signed in successfully:")
        return userid
    except:
        print("Invalid credentials")
        return "Invalid credentials"

def find_medicine(search_query):
    medicines = db.child("medicines").get()
    result = []
    for medicine in medicines.each():
        if search_query in medicine.val().values():
            result.append(medicine.val())
    print(result)
    return result

def get_requests():
    requests = db.child("requests").child(userid).get()
    res = []
    try:
        for request in requests.each():
            req = request.val()
            user = request.key()
            req["username"] = db.child("users").child(user).child("username").get().val()
            req["user_id"] = user
            res.append(req)
    except:
        pass
    return res


# UPLOAD_FOLDER = 'uploads/prescriptions'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register/<user_type>', methods=['GET', 'POST'])
def register(user_type):
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            return 'Passwords do not match'
        
        try:
            create_user(email, password, username, user_type)
        except:
            print("User already exists")
            return render_template('register.html', user_type=user_type)
        
        if user_type == 'donor':
            return redirect(url_for('donor_dashboard', requests = get_requests()))
        else:
            return redirect(url_for('recipient_dashboard'))

    return render_template('register.html', user_type=user_type)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        res = log_in(username, password)
        if res == "Invalid credentials":
            return render_template('login.html')
        type = db.child("users").child(res).child("user type").get().val()
        if type == "donor":
            return redirect(url_for('donor_dashboard', requests = get_requests()))
        else:
            return redirect(url_for('recipient_dashboard'))
    return render_template('login.html')

@app.route('/donor_dashboard')
def donor_dashboard():
    if userid == None:
        return redirect(url_for('login'))
    medicines = db.child("users").child(userid).child("medicines").get().val()
    return render_template('donor_dashboard.html', medicines=medicines, requests = get_requests())

@app.route('/recipient_dashboard')
def recipient_dashboard():
    if userid == None:
        return redirect(url_for('login'))
    return render_template('recipient_dashboard.html')

@app.route('/add_medicine', methods=['POST'])
def add_medicine():
    if userid == None:
        return redirect(url_for('login'))

    medicine = {
        'name' : request.form['name'],
        'batch_number' : request.form['batch_number'],
        'expiry_date' : request.form['expiry_date'],
        'manufacturing_date' : request.form['manufacturing_date'],
        'details' : request.form['details'],
        'Donor' : userid
    }
    db.child("medicines").push(medicine)
    return redirect(url_for('donor_dashboard', requests = get_requests()))

@app.route('/search_medicine', methods=['GET', 'POST'])
def search_medicine():
    if userid == None:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        search_query = request.form['search']
        medicines = find_medicine(search_query)
        return render_template('medicine_search.html', search_results=medicines)
    
    return render_template('medicine_search.html', search_results=[])

@app.route('/request_medicine/<username> <medicine_name>', methods=['GET', 'POST'])
def request_medicine(username, medicine_name):
    if userid == None:
        return redirect(url_for('login'))
    print(f"username : {username}, medicine_name : {medicine_name}")
    if request.method == 'POST':
        prescription = request.files['prescription']
        if prescription and allowed_file(prescription.filename):
            filename = secure_filename(prescription.filename)
            
            storage.child("prescriptions").child(filename).put(prescription)
            prescription_url = filename
            db.child("requests").child(username).child(userid).child("prescription").set(prescription_url)
            db.child("requests").child(username).child(userid).child("medicine_name").set(medicine_name)
            db.child("requests").child(username).child(userid).child("details").set(request.form['details'])

            return redirect(url_for('recipient_dashboard'))
    return render_template('request_form.html', username = username, medicine_name = medicine_name)


@app.route('/view_request/<username> <details> <medicine_name> <prescription>', methods=['GET', 'POST'])
def view_request(username, details, medicine_name, prescription):
    if userid == None:
        return redirect(url_for('login'))
    return render_template('view_request.html', username=username, details=details, medicine_name=medicine_name, prescription=prescription)

@app.route('/logout')
def logout():
    auth.current_user = None
    global userid
    userid = None
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port, debug=True)

