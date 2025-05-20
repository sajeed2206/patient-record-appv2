from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import pandas as pd
import os
from datetime import datetime
import csv
import io

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure secret key

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# Initialize patients CSV file if it doesn't exist
if not os.path.exists('data/patients.csv'):
    with open('data/patients.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'name', 'age', 'gender', 'contact', 'address', 'blood_group', 'conditions', 'medications', 'visit_date'])

# User credentials (In a real app, you would use a database and hash passwords)
users = {
    "admin": "admin123",
    "user": "user123"
}

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid Credentials. Please try again.'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    patients = pd.read_csv('data/patients.csv')
    return render_template('dashboard.html', patients=patients.to_dict('records'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    search_results = []
    if request.method == 'POST':
        search_term = request.form['search_term']
        search_type = request.form['search_type']
        
        patients = pd.read_csv('data/patients.csv')
        
        if search_type == 'name':
            search_results = patients[patients['name'].str.contains(search_term, case=False, na=False)].to_dict('records')
        elif search_type == 'age':
            try:
                age = int(search_term)
                search_results = patients[patients['age'] == age].to_dict('records')
            except ValueError:
                flash('Please enter a valid age for age search', 'danger')
        elif search_type == 'date':
            search_results = patients[patients['visit_date'].str.contains(search_term, case=False, na=False)].to_dict('records')
    
    return render_template('search.html', search_results=search_results)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Read existing patients
        patients = pd.read_csv('data/patients.csv')
        
        # Generate a simple ID (in production, use a more robust method)
        new_id = 1
        if not patients.empty:
            new_id = int(patients['id'].max()) + 1
        
        # Get current date and time
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create new patient record
        new_patient = {
            'id': new_id,
            'name': request.form['name'],
            'age': request.form['age'],
            'gender': request.form['gender'],
            'contact': request.form['contact'],
            'address': request.form['address'],
            'blood_group': request.form['blood_group'],
            'conditions': request.form['conditions'],
            'medications': request.form['medications'],
            'visit_date': current_datetime
        }
        
        # Append to dataframe and save
        patients = patients.append(new_patient, ignore_index=True)
        patients.to_csv('data/patients.csv', index=False)
        
        flash('Patient added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_patient.html')

@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    patients = pd.read_csv('data/patients.csv')
    patient = patients[patients['id'] == patient_id].to_dict('records')[0]
    
    if request.method == 'POST':
        # Update patient data
        patients.loc[patients['id'] == patient_id, 'name'] = request.form['name']
        patients.loc[patients['id'] == patient_id, 'age'] = request.form['age']
        patients.loc[patients['id'] == patient_id, 'gender'] = request.form['gender']
        patients.loc[patients['id'] == patient_id, 'contact'] = request.form['contact']
        patients.loc[patients['id'] == patient_id, 'address'] = request.form['address']
        patients.loc[patients['id'] == patient_id, 'blood_group'] = request.form['blood_group']
        patients.loc[patients['id'] == patient_id, 'conditions'] = request.form['conditions']
        patients.loc[patients['id'] == patient_id, 'medications'] = request.form['medications']
        # Don't update visit_date on edit to preserve the original visit date
        
        patients.to_csv('data/patients.csv', index=False)
        
        flash('Patient updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_patient.html', patient=patient)

@app.route('/delete_patient/<int:patient_id>')
def delete_patient(patient_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    patients = pd.read_csv('data/patients.csv')
    patients = patients[patients['id'] != patient_id]
    patients.to_csv('data/patients.csv', index=False)
    
    flash('Patient deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/export_csv')
def export_csv():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    patients = pd.read_csv('data/patients.csv')
    
    # Create a string buffer to hold the CSV data
    buffer = io.StringIO()
    patients.to_csv(buffer, index=False)
    buffer.seek(0)
    
    return send_file(
        io.BytesIO(buffer.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename='patients_export.csv'
    )

@app.route('/import_csv', methods=['GET', 'POST'])
def import_csv():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # Read the uploaded file
                imported_data = pd.read_csv(file)
                
                # Ensure all required columns are present
                required_columns = ['name', 'age', 'gender', 'contact', 'address', 'blood_group', 'conditions', 'medications']
                for col in required_columns:
                    if col not in imported_data.columns:
                        flash(f'Missing required column: {col}', 'danger')
                        return redirect(request.url)
                
                # Add visit_date column if not present
                if 'visit_date' not in imported_data.columns:
                    imported_data['visit_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Read existing patients
                patients = pd.read_csv('data/patients.csv')
                
                # Generate new IDs for imported patients
                if not patients.empty:
                    last_id = int(patients['id'].max())
                else:
                    last_id = 0
                
                new_ids = range(last_id + 1, last_id + 1 + len(imported_data))
                imported_data['id'] = list(new_ids)
                
                # Append imported data to existing patients
                patients = pd.concat([patients, imported_data])
                patients.to_csv('data/patients.csv', index=False)
                
                flash(f'Successfully imported {len(imported_data)} patients', 'success')
                return redirect(url_for('dashboard'))
            
            except Exception as e:
                flash(f'Error importing CSV: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Please upload a CSV file', 'danger')
            return redirect(request.url)
    
    return render_template('import_csv.html')

if __name__ == '__main__':
    app.run(debug=True)