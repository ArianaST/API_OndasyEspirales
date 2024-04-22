import logging
from flask import Flask, request, render_template, jsonify, make_response
from werkzeug.utils import secure_filename
import os
import cv2
import joblib
from skimage.feature import hog
from keras.models import load_model

app = Flask(__name__)

# Configuración básica del logging
logging.basicConfig(level=logging.INFO)

app.config['UPLOAD_FOLDER'] = 'uploads/'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Carga de modelos y transformadores
try:
    model_redn = load_model('Models/NeuronalCNN_LeNet5_Batch32_Transformadas.h5')
    app.logger.info("Neuronal Network model loaded successfully.")
except Exception as e:
    app.logger.error(f"Failed to load Neuronal Network model: {e}")

try:
    model_espirales = joblib.load('Models/SVM_Espirales.pkl')
    model_ondas = joblib.load('Models/SVM_Ondas.pkl')
    pca_espirales = joblib.load('Models/pca_model_wave.pkl')
    pca_ondas = joblib.load('Models/pca_model_spiral.pkl')
    hog_espirales = joblib.load('Models/hog_model_spiral.pkl')
    hog_ondas = joblib.load('Models/hog_model_wave.pkl')
    app.logger.info("All models and transformers loaded successfully.")
except Exception as e:
    app.logger.error(f"Failed to load one or more models/transformers: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def prepare_image(file_path, pca, hog_descriptor):
    img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        app.logger.error("Failed to read image file.")
        raise ValueError("Failed to read image file.")
    img_resized = cv2.resize(img, (96, 96), interpolation=cv2.INTER_AREA)
    features_hog = hog(img_resized, pixels_per_cell=(8, 8), cells_per_block=(2, 2), visualize=False)
    features_pca = pca.transform([features_hog])
    return features_pca[0]

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/predict/<model_type>', methods=['POST'])
def predict(model_type):
    if 'file' not in request.files:
        return jsonify(error='No file part'), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error='No selected file'), 400
    if not allowed_file(file.filename):
        return jsonify(error='Invalid file type'), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    if file.filename == '':
        return jsonify(error='No selected file'), 400

    try:
        if model_type == 'espirales':
            app.logger.info("Predicting with Espirales model...")
            model = model_espirales
            pca = pca_espirales
            hog_descriptor = hog_espirales
            features = prepare_image(file_path, pca, hog_descriptor)
            pred = model.predict([features])[0]
        elif model_type == 'ondas':
            app.logger.info("Predicting with Ondas model...")
            model = model_ondas
            pca = pca_ondas
            hog_descriptor = hog_ondas
            features = prepare_image(file_path, pca, hog_descriptor)
            pred = model.predict([features])[0]
        elif model_type == 'redn':
            app.logger.info("Predicting with Red Neuronal model...")
            img = cv2.imread(file_path, cv2.IMREAD_COLOR)
            img = cv2.resize(img, (96, 96))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.reshape(1, 96, 96, 3) / 255.0
            pred = model_redn.predict(img)
            result = 'healthy' if pred < 0.5 else 'parkinson'
            response = jsonify(result=result)
            response.headers["Cache-Control"] = "no-store"
            return response
        else:
            app.logger.warning(f"Invalid model type requested: {model_type}")
            return jsonify(error='Invalid model type'), 400
        
        result = 'healthy' if pred == 0 else 'parkinson'
        response = jsonify(result=result)
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception as e:
        app.logger.error(f"ERROR DURANTE LA PREDICCIÓN: {e}")
        response = jsonify(error=f"Failed to predict: {str(e)}"), 500
        response.headers["Cache-Control"] = "no-store"
        return response

if __name__ == '__main__':
    app.run(debug=True, port=5021)