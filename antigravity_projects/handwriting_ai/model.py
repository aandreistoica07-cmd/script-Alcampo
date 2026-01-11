import numpy as np
import os
import urllib.request

class HandwritingModel:
    def __init__(self):
        self.input_size = 784
        self.hidden_size = 256
        self.output_size = 10
        self.learning_rate = 0.1 # Increased LR slightly for Momentum
        self.momentum = 0.9
        
        # Initialize weights (He initialization)
        self.W1 = np.random.randn(self.input_size, self.hidden_size) * np.sqrt(2. / self.input_size)
        self.b1 = np.zeros((1, self.hidden_size))
        self.W2 = np.random.randn(self.hidden_size, self.output_size) * np.sqrt(2. / self.hidden_size)
        self.b2 = np.zeros((1, self.output_size))
        
        # Velocity for Momentum
        self.vW1 = np.zeros_like(self.W1)
        self.vb1 = np.zeros_like(self.b1)
        self.vW2 = np.zeros_like(self.W2)
        self.vb2 = np.zeros_like(self.b2)
        
        self.load_data()
        self.batch_size = 32
        self.current_idx = 0
        
    def load_data(self):
        path = 'mnist.npz'
        if not os.path.exists(path):
            print("Downloading MNIST...", end='')
            url = 'https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz'
            urllib.request.urlretrieve(url, path)
            print("Done.")
            
        with np.load(path, allow_pickle=True) as f:
            self.x_train, self.y_train = f['x_train'], f['y_train']
            self.x_test, self.y_test = f['x_test'], f['y_test']
            
        # Normalize and Flatten
        self.x_train = self.x_train.reshape(-1, 784).astype('float32') / 255.0
        self.x_test = self.x_test.reshape(-1, 784).astype('float32') / 255.0
        
        # One-hot encode labels
        self.y_train_enc = np.eye(10)[self.y_train]
        self.y_test_enc = np.eye(10)[self.y_test]

    def reset_model(self):
        self.W1 = np.random.randn(self.input_size, self.hidden_size) * np.sqrt(2. / self.input_size)
        self.b1 = np.zeros((1, self.hidden_size))
        self.W2 = np.random.randn(self.hidden_size, self.output_size) * np.sqrt(2. / self.hidden_size)
        self.b2 = np.zeros((1, self.output_size))
        
        self.vW1 = np.zeros_like(self.W1)
        self.vb1 = np.zeros_like(self.b1)
        self.vW2 = np.zeros_like(self.W2)
        self.vb2 = np.zeros_like(self.b2)

    def relu(self, Z):
        return np.maximum(0, Z)

    def softmax(self, Z):
        expZ = np.exp(Z - np.max(Z, axis=1, keepdims=True))
        return expZ / np.sum(expZ, axis=1, keepdims=True)
        
    def forward(self, X):
        # Layer 1
        Z1 = np.dot(X, self.W1) + self.b1
        A1 = self.relu(Z1)
        # Layer 2
        Z2 = np.dot(A1, self.W2) + self.b2
        A2 = self.softmax(Z2)
        return Z1, A1, Z2, A2

    def train_step(self):
        # Get batch
        if self.current_idx + self.batch_size > len(self.x_train):
            self.current_idx = 0
            # Shuffle
            indices = np.arange(len(self.x_train))
            np.random.shuffle(indices)
            self.x_train = self.x_train[indices]
            self.y_train_enc = self.y_train_enc[indices]

        X_batch = self.x_train[self.current_idx : self.current_idx + self.batch_size]
        y_batch = self.y_train_enc[self.current_idx : self.current_idx + self.batch_size]
        self.current_idx += self.batch_size
        
        # Forward
        Z1, A1, Z2, A2 = self.forward(X_batch)
        
        # Loss (Categorical Crossentropy)
        m = y_batch.shape[0]
        loss = -np.sum(y_batch * np.log(A2 + 1e-9)) / m
        
        # Accuracy
        predictions = np.argmax(A2, axis=1)
        true_labels = np.argmax(y_batch, axis=1)
        accuracy = np.mean(predictions == true_labels)

        # Backward (Backprop)
        dZ2 = A2 - y_batch
        dW2 = np.dot(A1.T, dZ2) / m
        db2 = np.sum(dZ2, axis=0, keepdims=True) / m
        
        dA1 = np.dot(dZ2, self.W2.T)
        dZ1 = dA1 * (Z1 > 0) # ReLU derivative
        dW1 = np.dot(X_batch.T, dZ1) / m
        db1 = np.sum(dZ1, axis=0, keepdims=True) / m
        
        # Update weights (SGD with Momentum)
        self.vW1 = self.momentum * self.vW1 - self.learning_rate * dW1
        self.vb1 = self.momentum * self.vb1 - self.learning_rate * db1
        self.vW2 = self.momentum * self.vW2 - self.learning_rate * dW2
        self.vb2 = self.momentum * self.vb2 - self.learning_rate * db2
        
        self.W1 += self.vW1
        self.b1 += self.vb1
        self.W2 += self.vW2
        self.b2 += self.vb2
        
        return {
            "loss": float(loss),
            "accuracy": float(accuracy)
        }

    def center_image(self, img_2d):
        # Calculate Center of Mass
        y_grid, x_grid = np.indices(img_2d.shape)
        total_mass = np.sum(img_2d)
        if total_mass == 0: return img_2d
        
        cy = np.sum(y_grid * img_2d) / total_mass
        cx = np.sum(x_grid * img_2d) / total_mass
        
        # Shift to center (13.5, 13.5 since 0-27) - let's say 14,14
        shift_y = 14 - cy
        shift_x = 14 - cx
        
        # Manual shift integer implementation for simplicity without scipy
        sy, sx = int(round(shift_y)), int(round(shift_x))
        
        # Pad and roll
        img_shifted = np.roll(img_2d, sy, axis=0)
        img_shifted = np.roll(img_shifted, sx, axis=1)
        
        # Zero out wrapped around parts
        if sy > 0: img_shifted[:sy, :] = 0
        elif sy < 0: img_shifted[sy:, :] = 0
        if sx > 0: img_shifted[:, :sx] = 0
        elif sx < 0: img_shifted[:, sx:] = 0
            
        return img_shifted

    def predict(self, image_data):
        # image_data: flat list or array
        img = np.array(image_data).astype("float32")
        
        # Reshape to 2D for centering
        img_2d = img.reshape(28, 28)
        img_2d = self.center_image(img_2d)
        
        # Flatten back
        img_flat = img_2d.reshape(1, 784)
        _, A1, _, probs = self.forward(img_flat)
        
        return {
            "probabilities": probs[0].tolist(),
            "hidden_activations": A1[0].tolist(),
            "input_centered": img_2d.tolist()
        }
