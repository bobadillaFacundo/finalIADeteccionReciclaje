import os
import tensorflow as tf
from tensorflow.keras import layers, regularizers, models
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns

# ====================
# Configuración inicial
# ====================

SCRIPT_DIR = Path(__file__).parent
DATA_DIR   = SCRIPT_DIR.parent / 'dataset'

BATCH_SIZE = 32  # EfficientNetB3 pide más RAM. Bajá el batch si falta memoria.
IMG_HEIGHT = 300
IMG_WIDTH = 300
EPOCHS = 10
SEED = 123

# ================
# Dataset y Augment
# ================

raw_train_ds = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR,
    validation_split=0.3,
    subset='training',
    seed=SEED,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
    label_mode='categorical'
)
raw_val_ds = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR,
    validation_split=0.3,
    subset='validation',
    seed=SEED,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
    label_mode='categorical'
)

class_names = raw_train_ds.class_names
num_classes = len(class_names)
print("Clases detectadas:", class_names)

AUTOTUNE = tf.data.AUTOTUNE
train_ds = raw_train_ds.cache().prefetch(buffer_size=AUTOTUNE)
val_ds   = raw_val_ds.cache().prefetch(buffer_size=AUTOTUNE)

data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal_and_vertical"),
    layers.RandomRotation(0.2),
    layers.RandomZoom(0.2),
    layers.RandomTranslation(0.1, 0.1),
    layers.RandomContrast(0.2),
])

# =========================
# Modelo con EfficientNetB3
# =========================

base_model = tf.keras.applications.EfficientNetB3(
    input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
    include_top=False,
    weights="imagenet"
)
base_model.trainable = False  # Fase 1: congelado

inputs = layers.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3))
x = data_augmentation(inputs)
x = tf.keras.applications.efficientnet.preprocess_input(x)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.4)(x)
x = layers.Dense(256, activation="relu", kernel_regularizer=regularizers.l2(1e-5))(x)
x = layers.BatchNormalization()(x)
x = layers.Dropout(0.4)(x)
outputs = layers.Dense(num_classes, activation="softmax")(x)

model = models.Model(inputs, outputs)

model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)
model.summary()

# ================
# Entrenamiento 1
# ================

early_stop = EarlyStopping(
    monitor='val_loss',
    patience=12,
    restore_best_weights=True
)
reduce_lr = ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.5,
    patience=4
)
checkpoint = ModelCheckpoint(
    'best_model.h5',
    monitor='val_loss',
    save_best_only=True
)

history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=[early_stop, reduce_lr, checkpoint]
)

def plot_history(h, title_acc='Precisión', title_loss='Pérdida'):
    epochs = range(len(h.history['accuracy']))
    plt.figure(figsize=(6,4))
    plt.plot(epochs, h.history['accuracy'],    label='Train acc')
    plt.plot(epochs, h.history['val_accuracy'],label='Val acc')
    plt.title(title_acc)
    plt.legend()
    plt.show()
    plt.figure(figsize=(6,4))
    plt.plot(epochs, h.history['loss'],    label='Train loss')
    plt.plot(epochs, h.history['val_loss'],label='Val loss')
    plt.title(title_loss)
    plt.legend()
    plt.show()
plot_history(history)

# ==================
# Fine-tuning phase
# ==================

# 1. Descongelar últimas capas del backbone (20 capas)
fine_tune_at = len(base_model.layers) - 20
for layer in base_model.layers[:fine_tune_at]:
    layer.trainable = False
for layer in base_model.layers[fine_tune_at:]:
    layer.trainable = True

# 2. Recompilar con LR bajo
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# 3. Entrenar fine-tuning
fine_tune_epochs = 10
total_epochs = EPOCHS + fine_tune_epochs

history_fine = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=total_epochs,
    initial_epoch=history.epoch[-1] + 1,
    callbacks=[
        EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2),
        ModelCheckpoint('best_model_finetuned.h5', monitor='val_loss', save_best_only=True)
    ]
)
plot_history(history_fine, title_acc='Precisión (Fine-tuning)', title_loss='Pérdida (Fine-tuning)')

# ======================
# Guardado de modelos
# ======================
model.save('model_finetuned.h5')
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open('waste_classifier_finetuned.tflite', 'wb') as f:
    f.write(tflite_model)
print("Modelos guardados: model_finetuned.h5, best_model_finetuned.h5, waste_classifier_finetuned.tflite")

# ======================
# Evaluación final
# ======================
# 1) Crear loader sin augmentation para obtener X_test, y_test
full_val_ds = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR,
    validation_split=0.3,
    subset='validation',
    seed=SEED,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
    label_mode='categorical'
).cache().prefetch(AUTOTUNE)

# 2) Predecir sobre todo val_ds
y_true = []
y_pred = []
for X_batch, y_batch in full_val_ds:
    preds = model.predict(X_batch)
    y_true.extend(np.argmax(y_batch.numpy(), axis=1))
    y_pred.extend(np.argmax(preds, axis=1))

y_true = np.array(y_true)
y_pred = np.array(y_pred)

# 3) Matriz de confusión
cm = confusion_matrix(y_true, y_pred)
plt.figure(figsize=(8,6))
sns.heatmap(cm, annot=True, fmt="d",
            xticklabels=class_names,
            yticklabels=class_names,
            cmap="Blues")
plt.xlabel("Predicción")
plt.ylabel("Etiqueta real")
plt.title("Matriz de Confusión")
plt.show()

# 4) Classification report
print(classification_report(y_true, y_pred, target_names=class_names, digits=4))
