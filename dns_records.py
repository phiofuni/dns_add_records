from flask import Flask, request, redirect, url_for, render_template, flash
import os
import subprocess

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.secret_key = 'supersecretkey'


NAMED_CONF_PATH = '/opt/homebrew/etc/bind/named.conf'
ZONE_PATH = '/opt/homebrew/etc/bind/zones'

# Ensure the uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('upload.html')

@app.route('/process', methods=['POST'])
def process_file():
    # Check if the file is part of the request
    if 'file' not in request.files:
        flash('No file part in the request')
        return redirect(url_for('home'))

    file = request.files['file']
    zone_name = request.form.get('zone_name')

    # Ensure the user uploaded a valid file
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('home'))
    
    if not zone_name:
        flash('Zone name empty')
        return redirect(url_for('home'))

    if file and file.filename.endswith('.txt'):
        # Save the uploaded file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # move the file to bind9 server
        zone_path = os.path.join(ZONE_PATH,file.filename)
        os.rename(file_path,zone_path)

        #add zone config to named.conf
        new_zone = f"""
zone "<{zone_name}>" {{
    type primary;
    file "{zone_path}";
    notify yes;
}};"""

        try:
            with open(NAMED_CONF_PATH,'a') as conf_file:
                conf_file.write(new_zone)
            
            #check 'named-checkzone <origin> <filename>.txt'
            check_zone_command = ['named-checkzone',zone_name,zone_path]
            check_zone_result = subprocess.run(check_zone_command, capture_output=True, text=True, timeout=10)
            if check_zone_result.stderr:
                flash(f'Check zone error {check_zone_result.stderr}')
                # return redirect(url_for('home')) 
            flash(f'Check zone Result {check_zone_result.stdout}')

            #check 'named-checkconf'
            check_conf_command = ['named-checkconf']
            check_conf_result = subprocess.run(check_conf_command, capture_output=True, text=True, timeout=10)
            if check_conf_result.stderr:
                flash(f'Check named.conf error {check_conf_result.stderr}')
                # return redirect(url_for('home'))
            flash(f'Check named.conf Result {check_conf_result.stdout}')

            # check rndc reconfig
            reconfig_command = ['rndc', 'reconfig']
            reconfig_result = subprocess.run(reconfig_command,capture_output=True,timeout=10)
            if reconfig_result.stderr:
                flash(f'Reconfig error {reconfig_result.stderr}')
                # return redirect(url_for('home')) 
            flash(f'Reconfig Result {reconfig_result.stdout}')

            #check 'rndc reload'
            reload_command = ['rndc', 'reload']
            reload_result = subprocess.run(reload_command,capture_output=True,timeout=10)
            if reload_result.stderr:
                flash(f'Reload error {reload_result.stderr}')
                # return redirect(url_for('home')) 
            flash(f'Reload Result {reload_result.stdout}')

            # check 'rndc reload <origin>'
            reload_zone_command = ['rndc','reload',zone_name]
            reload_zone_result = subprocess.run(reload_zone_command,capture_output=True,timeout=10)
            if reload_zone_result.stderr:
                flash(f'Reload zone error {reload_zone_result.stderr}')
                # return redirect(url_for('home')) 
            flash(f'Reload zone Result {reload_zone_result.stdout}')

            # check 'dig <address-in-the-zonefile>'
            verify_command = ['dig',zone_name]
            verify_result = subprocess.run(verify_command,capture_output=True,timeout=10)
            if verify_result.stderr:
                flash(f'verify dns error {verify_result.stderr}')
                # return redirect(url_for('home')) 
            flash(f'verify dns Result {verify_result.stdout}')            

            return redirect(url_for('home'))
        
        except Exception as e:
            flash(f'Error {str(e)}')
            return redirect(url_for('home'))

    else:
        flash('Only .txt files are allowed')
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
