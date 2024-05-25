import logging
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import os
import cv2
import joblib
import numpy as np
import json
from keras.models import load_model

app = Flask(__name__)

HOG_WINDOW_SIZE = (96, 96)
logging.basicConfig(level=logging.INFO)

app.config['UPLOAD_FOLDER'] = 'uploads/'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

model_redn, model_espirales, model_ondas, hog_espirales, hog_ondas = None, None, None, None, None

def load_hog_descriptor_from_json(file_path):
    with open(file_path, 'r') as f:
        params = json.load(f)
    hog = cv2.HOGDescriptor(
        tuple(params['winSize']),
        tuple(params['blockSize']),
        tuple(params['blockStride']),
        tuple(params['cellSize']),
        params['nbins']
    )
    return hog

def load_models_and_transformers():
    global model_redn, model_espirales, model_ondas, hog_espirales, hog_ondas
    try:
        model_redn = load_model('Models/NeuronalCNN_LeNet5_Batch32_Transformadas.h5')
        app.logger.info("Neuronal Network model loaded successfully.")
    except Exception as e:
        app.logger.error(f"Failed to load Neuronal Network model: {e}")

    try:
        model_espirales = joblib.load('Models/RandomForest_Spirales2.pkl')
        model_ondas = joblib.load('Models/RandomForest_Wave2.pkl')
        app.logger.info("Random Forest models loaded successfully.")
    except Exception as e:
        app.logger.error(f"Failed to load Random Forest models: {e}")

    try:
        hog_espirales = load_hog_descriptor_from_json('Models/hog_params_spiral.json')
        hog_ondas = load_hog_descriptor_from_json('Models/hog_params_wave.json')
        app.logger.info("HOG descriptors loaded successfully.")
    except Exception as e:
        app.logger.error(f"Failed to load HOG descriptors: {e}")

load_models_and_transformers()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

def prepare_image(image_path, hog_descriptor=None):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            app.logger.error("Error: Failed to read image")
            return None, None
        
        # Comprobar si la imagen está vacía antes de redimensionar
        if img.size == 0:
            app.logger.error("Error: Empty image")
            return None, None
        
        # Usa la constante HOG_WINDOW_SIZE para el redimensionamiento
        img_resized = cv2.resize(img, HOG_WINDOW_SIZE)
        # Comprobar si la imagen redimensionada está vacía
        if img_resized.size == 0:
            app.logger.error("Error: Resized image is empty")
            return None, None
        
        if hog_descriptor is not None:
            # Computa las características HOG
            features_hog = hog_descriptor.compute(img_resized)
            
            # Verificar si hay un error al calcular las características HOG
            if features_hog is None:
                app.logger.error("Error: Failed to compute HOG features")
                return None, None
            
            # Asegurarse de que las características HOG tengan la forma correcta
            features_hog = features_hog.flatten()  # Aplanar las características HOG
            if len(features_hog) != hog_descriptor.getDescriptorSize():
                app.logger.error("Error: Incorrect number of HOG features")
                return None, None
            
            # Imprime algunas características HOG
            app.logger.info("HOG Features:")
            app.logger.info(features_hog[:5])  # Imprime las primeras 5 características HOG
            
            # Imprime el total de características HOG
            app.logger.info("Total HOG Features: %d", len(features_hog))
            
            # Verificar si el número de características HOG coincide con el esperado por el modelo
            expected_num_features = 4356
            if len(features_hog) != expected_num_features:
                app.logger.error(f"Error: Expected {expected_num_features} HOG features, but got {len(features_hog)}")
                return None, None
            
            return img_resized, features_hog
        else:
            return img_resized, None
    except Exception as e:
        app.logger.error(f"Error during image processing: {e}")
        return None, None

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

    try:
        app.logger.info(f"Predicting with {model_type.capitalize()} model...")
        label = None
        if model_type == 'espirales' or model_type == 'ondas':
            hog_descriptor = hog_espirales if model_type == 'espirales' else hog_ondas
            img, features = prepare_image(file_path, hog_descriptor)
            if img is not None and features is not None:
                app.logger.info(f"Features extracted and transformed for {model_type} model.")
                model = model_espirales if model_type == 'espirales' else model_ondas

                app.logger.info(f"Feature vector shape: {features.shape}")

                prediction = model.predict([features])[0]
                app.logger.info(f"Prediction: {prediction}")

                # Mapear las etiquetas a los valores esperados por el modelo
                label = "Parkinson" if prediction == 1 else "Sano"

        elif model_type == 'redn':
            app.logger.info("Predicting with redn model...")
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            img = cv2.resize(img, (96, 96))
            img = np.expand_dims(img, axis=0) / 255.0
            probability = model_redn.predict(img)[0]
            prediction = 1 if probability >= 0.5 else 0
            label = 'Parkinson' if prediction == 1 else 'Sano'

        if label is not None:
            return jsonify(result=label)
        else:
            return jsonify(error='Prediction failed'), 500
    except Exception as e:
        app.logger.error(f"Error during prediction: {e}")
        return jsonify(error='Prediction failed'), 500
        return jsonify(result=label)
    except Exception as e:
        app.logger.error(f"Error during prediction: {e}")
        return jsonify(error='Prediction failed'), 500

@app.route('/upload', methods=['POST'])
def upload():
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

    return jsonify(filename=filename)

if __name__ == '__main__':
    app.run(debug=True, port=5021)