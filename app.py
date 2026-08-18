import csv
import os
import subprocess
import sys
import json
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "methods": ["GET", "POST", "OPTIONS"]}})

def load_users_from_csv():
    users = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, 'users_credentials.csv')
    
    try:
        if os.path.exists(csv_path):
            with open(csv_path, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    u_id = str(row['username']).strip()
                    users[u_id] = {
                        "password": str(row['password']).strip(),
                        "role": str(row['role']).strip(),
                        "name": str(row['full_name']).strip() 
                    }
    except Exception as e:
        print(f"CSV Loading Error: {e}")
    return users

@app.route('/get_initial_data')
def get_initial_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    all_data = []
    
    try:
        if os.path.exists(data_dir):
            files = [f for f in os.listdir(data_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
            for filename in sorted(files):
                filepath = os.path.join(data_dir, filename)
                df = pd.read_excel(filepath)
                df.columns = df.columns.str.strip()
                for col in df.columns:
                    if df[col].dtype == 'object' or 'datetime' in str(df[col].dtype):
                        df[col] = df[col].astype(str)
                
                df['Term'] = filename.replace('.xlsx', '').strip()
                df['sourceFile'] = filename
                df = df.fillna("")
                all_data.extend(df.to_dict(orient='records'))
            
            return jsonify(all_data)
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/run_optimization', methods=['POST'])
def run_optimization():
    try:
        req_data = request.get_json()
        if not req_data:
            return jsonify({"status": "error", "message": "Invalid or empty JSON payload"}), 400
            
        selected_dataset = req_data.get('dataset', 'Fall 2024 - 2421.xlsx')
        selected_script = req_data.get('script', 'unisa_modified_copy.py') 
        
        print(f"\n--- [SUS ENGINE START] ---")
        print(f"Excel Target: {selected_dataset} | Selected AI Script: {selected_script}")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.normpath(os.path.join(base_dir, 'static', 'optimizationCodes', selected_script))
        
        print(f"[SUS PATH FIXED] Dynamic script path: {script_path}")
        
        if not os.path.exists(script_path):
            print(f"❌ Error: Script not found at {script_path}")
            return jsonify({"status": "error", "message": f"The script '{selected_script}' was not found inside static/optimizationCodes folder."}), 404
            
        print(f"Executing: python3 {script_path} {selected_dataset}")
        
        result = subprocess.run(
            ['python3', script_path, selected_dataset],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print(f"❌ Python Optimization Script crashed internally!")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return jsonify({
                "status": "error", 
                "message": f"Algorithm interior crash (Code {result.returncode}). Check terminal logs for full traceback.",
                "details": result.stderr
            }), 500
            
        optimized_data = json.loads(result.stdout)
        print(f"✅ [SUS ENGINE SUCCESS] - Transmitted {len(optimized_data)} optimized rows.")
        
        if not optimized_data or len(optimized_data) == 0:
            print("⚠️ [PROTECTION TRIGGERED] Algorithm returned empty data. Excel overwrite blocked!")
            return jsonify({"status": "error", "message": "The optimization script executed but returned empty dataset matrix."}), 400

        try:
            target_excel_path = os.path.join(base_dir, 'data', selected_dataset)
            optimized_df = pd.DataFrame(optimized_data)
            
            if 'Term' in optimized_df.columns:
                optimized_df = optimized_df.drop(columns=['Term'])
            if 'sourceFile' in optimized_df.columns:
                optimized_df = optimized_df.drop(columns=['sourceFile'])
                
            optimized_df.to_excel(target_excel_path, index=False)
            print(f"💾 [AUTO-SAVE SUCCESS] Overwrote optimized matrix directly into: {target_excel_path}")
            
        except Exception as save_error:
            print(f"⚠️ Warning: Optimization succeeded but Excel Overwrite failed: {str(save_error)}")
        
        return jsonify({
            "status": "success",
            "message": f"Optimization matrix generated and saved successfully using {selected_script}.",
            "data": optimized_data
        })
        
    except json.JSONDecodeError as je:
        print(f"❌ JSON Parse Error: Final output was:\n{result.stdout}")
        return jsonify({"status": "error", "message": "The optimization script executed, but its final printed output was not a valid JSON matrix."}), 500
    except Exception as e:
        print(f"❌ Critical Exception in Flask Route: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/submit_instructor_request', methods=['POST'])
def submit_instructor_request():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Missing JSON body"}), 400
            
        instructor_name = data.get('instructor_name', 'Instructor').strip()
        instructor_id = data.get('instructor_id', '').strip()
        course_code = data.get('course_code', '').strip()
        course_name = data.get('course_name', '').strip()
        requested_day = data.get('requested_day', '').strip()
        start_time = data.get('requested_time', '').strip()
        notes = data.get('note', '').strip()
        term_code = data.get('term_code', '').strip()
        
        try:
            h, m = map(int, start_time.split(':'))
            m_end = m + 50
            h_end = h + (m_end // 60)
            m_end = m_end % 60
            end_time = f"{str(h_end).zfill(2)}:{str(m_end).zfill(2)}"
        except:
            end_time = start_time

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'instructor_slots_requests.csv')
        file_exists = os.path.isfile(csv_path)

        with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['instructor_id', 'instructor_name', 'course_code', 'course_name', 'requested_day', 'start_time', 'end_time', 'note', 'term_code', 'status', 'admin_note', 'timestamp'])
            writer.writerow([instructor_id, instructor_name, course_code, course_name, requested_day, start_time, end_time, notes, term_code, 'Pending', '', timestamp])

        print(f"✅ [REQUEST LOGGED] New Pending slot request from Dr. {instructor_name} received.")
        return jsonify({"status": "success", "message": "Your slot request has been transmitted as [Pending] to Master Admin Engine."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_instructor_requests', methods=['GET'])
def get_instructor_requests():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'instructor_slots_requests.csv')
        requests_list = []

        if os.path.exists(csv_path):
            with open(csv_path, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    requests_list.append({
                        "instructor_id": row.get('instructor_id', ''),
                        "instructor_name": row.get('instructor_name', ''),
                        "course_code": row.get('course_code', ''),
                        "course_name": row.get('course_name', ''),
                        "requested_day": row.get('requested_day', ''),
                        "start_time": row.get('start_time', ''),
                        "end_time": row.get('end_time', ''),
                        "note": row.get('note', ''),
                        "term_code": row.get('term_code', ''),
                        "status": row.get('status', 'Pending'),
                        "admin_note": row.get('admin_note', ''),
                        "timestamp": row.get('timestamp', '')
                    })
        return jsonify(requests_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    try:
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not full_name or not email:
            return jsonify({"status": "error", "message": "Missing fields"}), 400

        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'contact_messages.csv')
        file_exists = os.path.isfile(csv_path)

        with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Full Name', 'Email', 'Subject', 'Message'])
            writer.writerow([full_name, email, subject, message])

        print(f"✅ Success: New message from {full_name} saved to CSV.")
        return jsonify({"status": "success", "message": "Message saved successfully"}), 200
    except Exception as e:
        print(f"❌ Critical Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/visitor')
def visitor_page():
    return render_template('visitor.html')

@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()
    all_users = load_users_from_csv()
    
    user = all_users.get(username)
    if user and user['password'] == password:
        return jsonify({
            "status": "success", 
            "role": user['role'], 
            "username": username,
            "full_name": user['name']  
        })
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/instructor')
def instructor_page():
    return render_template('instructor.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/contact')
def contact_page():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)