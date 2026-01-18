from flask import Flask, render_template, request, jsonify
from model import HandwritingModel
import numpy as np

app = Flask(__name__)
model = HandwritingModel()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/train_step', methods=['POST'])
def train_step():
    stats = model.train_step()
    return jsonify(stats)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json['image'] # Expecting 28x28 list
    # The frontend should send normalized or raw 0-255 values
    # Model expects 0-1, but I can normalize here if needed.
    # Let's assume frontend sends 0-255.
    data = np.array(data) / 255.0
    result = model.predict(data)
    return jsonify(result)

@app.route('/reset', methods=['POST'])
def reset():
    model.reset_model()
    return jsonify({"status": "reset"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
