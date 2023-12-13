import numpy as np
from tensorflow.keras.models import load_model
from matplotlib import pyplot as plt

def detect_fen(images):
    label_list = ['E', 'N', 'p', 'B', 'b', 'Q', 'R', 'P', 'q', 'n', 'k', 'K', 'r']
    model = load_model('model.h5')

    # preprocess image
    np_images = np.array(images)

    # resize image
    np_images = np_images.reshape(-1, 50, 50, 3)

    # normalize image
    np_images = np_images / 255.0

    # predict
    pred = model.predict(np_images, verbose=None)
    pred = np.argmax(pred, axis=1)

    FEN = ""
    for i in range(8):
        E_count = 0
        for j in range(8):
            if label_list[pred[8*i+j]] == 'E':
                E_count += 1
            else:
                if E_count != 0:
                    FEN += str(E_count)
                    E_count = 0
                FEN += label_list[pred[8*i+j]]

        if E_count != 0:
            FEN += str(E_count)
            E_count = 0

        FEN += '/' if i != 7 else ''

    return FEN