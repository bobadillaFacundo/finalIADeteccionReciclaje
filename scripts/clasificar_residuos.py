from pyparsing import Path
import tensorflow as tf
from tensorflow.keras import layers, models

# Parámetros
IMG_HEIGHT = 128
IMG_WIDTH  = 128
BATCH_SIZE = 32
num_classes = 6  # tu número de clases
SCRIPT_DIR = Path(__file__).parent
DATA_DIR   = SCRIPT_DIR.parent / 'dataset'
# 1. Carga de datos (igual que antes)
train_ds = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR,
    validation_split=0.3,
    subset='training',
    seed=123,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
)
val_ds = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR,
    validation_split=0.3,
    subset='validation',
    seed=123,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
)

# 2. Construcción del modelo de Transfer Learning
# ------------------------------------------------
# 2.1 Backbone preentrenado (sin head)
base_model = tf.keras.applications.MobileNetV2(
    input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
    include_top=False,
    weights="imagenet"
)
base_model.trainable = False  # congelamos todo el backbone

# 2.2 Head personalizada
inputs = layers.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3))
# MobileNetV2 ya espera imágenes normalizadas entre -1 y 1
x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.4)(x)                   # regularización
x = layers.Dense(128, activation="relu")(x)  # capa densa intermedia
outputs = layers.Dense(num_classes, activation="softmax")(x)

model = models.Model(inputs, outputs)

# 3. Compilación
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

model.summary()

# 4. Entrenamiento inicial
callbacks = [
    tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", patience=3),
    tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
]
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=10,
    callbacks=callbacks
)

# Guardar el modelo final y convertir a TFLite
model.save('model.h5')
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open('waste_classifier.tflite', 'wb') as f:
    f.write(tflite_model)

print("Modelos guardados: model.h5, best_model.h5 y waste_classifier.tflite")
