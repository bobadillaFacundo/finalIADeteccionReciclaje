import tensorflow as tf

# 1. Carga tu modelo Keras desde el archivo .h5
model = tf.keras.models.load_model('model_finetuned.h5')

# 2. Crea el conversor de TFLite a partir del modelo cargado
converter = tf.lite.TFLiteConverter.from_keras_model(model)

# (Opcional) Habilita optimizaciones, e.g. cuantización:
# converter.optimizations = [tf.lite.Optimize.DEFAULT]

# 3. Convierte el modelo a formato TFLite
tflite_model = converter.convert()

# 4. Guarda el modelo convertido en un archivo .tflite
with open('waste_classifier.tflite', 'wb') as f:
    f.write(tflite_model)

print("Modelo TFLite guardado en model.tflite")
