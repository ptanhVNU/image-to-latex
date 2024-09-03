import time
import zipfile
from flask import Flask, logging, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import pypandoc
from pix2text import Pix2Text  # Adjust this import based on your actual Pix2Text module

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define the allowed file types
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_markdown_file_to_latex(input_file, output_file, resource_path='.'):
    try:
        pypandoc.convert_file(
            input_file,
            'latex',  # Output format
            outputfile=output_file,
            extra_args=['--standalone', f'--resource-path={resource_path}']
        )
        print(f'File {input_file} has been converted to {output_file}')
    except RuntimeError as e:
        print(f'Error during conversion: {e}')

def recognize_page(img_fp: str, output_dir:str, output_markdown: str, output_latex: str, figures_path: str):
    total_config = {
        'layout': {'scores_thresh': 0.45},
        'text_formula': {
            'formula': {
                'model_name': 'mfr',
                'model_backend': 'onnx',
                'more_model_configs': {'provider': 'CPUExecutionProvider'},
            }
        },
    }
    p2t = Pix2Text.from_config(total_configs=total_config)
    out_page = p2t.recognize_page(
        img_fp,
        page_id='test_page_1',
        title_contain_formula=False,
        text_contain_formula=False,
        save_debug_res='./outputs',
    )


    
    out_page.to_markdown(output_dir)
    convert_markdown_file_to_latex(output_markdown, output_latex, figures_path)

def create_zip_with_latex_and_images(output_dir, latex_file, zip_filename):
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                zipf.write(os.path.join(root, file), 
                           os.path.relpath(os.path.join(root, file), output_dir))
        zipf.write(latex_file, os.path.basename(latex_file))

@app.route('/upload', methods=['POST'])
def upload_file():
    start_time = time.time()  # Bắt đầu tính thời gian

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if not file or not file.filename:
        return jsonify({'error': 'No selected file'}), 400

    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        output_dir = "output-md"
        output_markdown = "output-md/output.md"
        output_latex = "output-md/output.tex"
        figures_path = 'output-md/figures/'

        # Đảm bảo rằng các thư mục đã tồn tại
        os.makedirs(figures_path, exist_ok=True)

        # Xử lý hình ảnh
        recognize_page(filepath, output_dir, output_markdown, output_latex, figures_path)

        # Tính toán thời gian thực thi
        execution_time = time.time() - start_time
        print(f"Processing time: {execution_time:.2f} seconds")

        # Trả về tệp LaTeX
        return send_file(output_latex, as_attachment=True)

    return jsonify({'error': 'File type not allowed'}), 400

if __name__ == '__main__':
    # Create the upload folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
