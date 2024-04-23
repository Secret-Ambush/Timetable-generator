from flask import Flask, request, jsonify
# Import your PDF processing module here

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    pdf_file = request.files['timetablePdf']
    year = request.form['year']
    discipline = request.form['discipline']
    
    # Your PDF processing code here
    
    # Return the result in a JSON response
    return jsonify({"status": "success", "message": "Timetable generated successfully"})

if __name__ == '__main__':
    app.run(debug=True)
