import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, regularizers, optimizers
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.optimizers.schedules import CosineDecay
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.utils import compute_class_weight
import seaborn as sns

# ====================
# Configuración GPU
# ====================
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    print(f"Usando {len(gpus)} GPU(s).")
else:
    print("GPU no detectada, usando CPU.")

# ====================
# Configuración inicial
# ====================
SCRIPT_DIR   = Path(__file__).parent
DATA_DIR     = SCRIPT_DIR.parent / 'dataset'
BATCH_SIZE   = 64
IMG_HEIGHT   = 300
IMG_WIDTH    = 300
EPOCHS_HEAD  = 8    # entrenamiento de la cabeza
EPOCHS_FINE  = 12   # fine‑tuning
SEED         = 123

# ======================
# Función para gráficas
# ======================
def plot_history(h, suffix):
    epochs = range(len(h.history['accuracy']))
    plt.figure(figsize=(6,4))
    plt.plot(epochs, h.history['accuracy'],    label='Train acc')
    plt.plot(epochs, h.history['val_accuracy'],label='Val acc')
    plt.title(f'Precisión {suffix}')
    plt.legend()
    plt.show()

    plt.figure(figsize=(6,4))
    plt.plot(epochs, h.history['loss'],    label='Train loss')
    plt.plot(epochs, h.history['val_loss'],label='Val loss')
    plt.title(f'Pérdida {suffix}')
    plt.legend()
    plt.show()

# ================
# Carga de datasets
# ================
raw_train = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR,
    validation_split=0.3,
    subset='training',
    seed=SEED,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
    label_mode='categorical'
)
raw_val = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR,
    validation_split=0.3,
    subset='validation',
    seed=SEED,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
    label_mode='categorical'
)
class_names = raw_train.class_names
num_classes = len(class_names)
print("Clases:", class_names)

AUTOTUNE = tf.data.AUTOTUNE
train_ds = raw_train.cache().prefetch(AUTOTUNE)
val_ds   = raw_val.cache().prefetch(AUTOTUNE)

# ====================
# Class weights
# ====================
y = np.concatenate([np.argmax(y.numpy(),1) for _, y in raw_train])
weights = compute_class_weight('balanced', classes=np.unique(y), y=y)
class_weights = {i: w for i,w in enumerate(weights)}
print("Class weights:", class_weights)

# ====================
# MixUp augmentation
# ====================
def mixup(x, y, alpha=0.2):
    lam = np.random.beta(alpha, alpha)
    idx = tf.random.shuffle(tf.range(tf.shape(x)[0]))
    return lam*x + (1-lam)*tf.gather(x,idx), lam*y + (1-lam)*tf.gather(y,idx)

train_ds = train_ds.map(lambda x,y: mixup(x,y), num_parallel_calls=AUTOTUNE)

# ====================
# Data augmentation
# ====================
augment = tf.keras.Sequential([
    layers.RandomFlip("horizontal_and_vertical"),
    layers.RandomRotation(0.2),
    layers.RandomZoom(0.2),
    layers.RandomTranslation(0.1,0.1),
    layers.RandomContrast(0.2),
])

# ===========================
# Construcción del modelo
# ===========================
base = tf.keras.applications.EfficientNetB3(
    input_shape=(IMG_HEIGHT,IMG_WIDTH,3),
    include_top=False,
    weights='imagenet'
)
base.trainable = False

inp = layers.Input((IMG_HEIGHT,IMG_WIDTH,3))
x = augment(inp)
x = tf.keras.applications.efficientnet.preprocess_input(x)
x = base(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.5)(x)  # dropout aumentado
x = layers.Dense(
    256, activation='relu',
    kernel_regularizer=regularizers.l2(1e-5)
)(x)
x = layers.BatchNormalization()(x)
x = layers.Dropout(0.5)(x)
out = layers.Dense(num_classes, activation='softmax')(x)

model = models.Model(inp, out)

# ====================
# Learning rate schedule
# ====================
steps = tf.data.experimental.cardinality(train_ds).numpy()
decay_steps = steps * (EPOCHS_HEAD + EPOCHS_FINE)
lr_sched = CosineDecay(initial_learning_rate=1e-3, decay_steps=decay_steps)

# ========================================
# Compilación y entrenamiento de la cabeza
# ========================================
model.compile(
    optimizer=optimizers.Adam(learning_rate=lr_sched),
    loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1),
    metrics=['accuracy']
)
model.summary()

common_cbs = [
    EarlyStopping('val_loss', patience=4, restore_best_weights=True),
    ReduceLROnPlateau('val_loss', factor=0.5, patience=2),
    ModelCheckpoint('head_best.h5','val_loss',save_best_only=True)
]

hist_head = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS_HEAD,
    class_weight=class_weights,
    callbacks=common_cbs
)
plot_history(hist_head, '(cabeza)')

# ================================
# Fine‑tuning: descongelar 15 capas
# ================================
for layer in base.layers[-15:]:
    layer.trainable = True

model.compile(
    optimizer=optimizers.Adam(learning_rate=lr_sched * 0.2),  # LR discriminativa
    loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1),
    metrics=['accuracy']
)

ft_cbs = [
    EarlyStopping('val_loss', patience=4, restore_best_weights=True),
    ReduceLROnPlateau('val_loss', factor=0.5, patience=2),
    ModelCheckpoint('ft_best.h5','val_loss',save_best_only=True)
]

hist_ft = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS_HEAD+EPOCHS_FINE,
    initial_epoch=hist_head.epoch[-1]+1,
    class_weight=class_weights,
    callbacks=ft_cbs
)
plot_history(hist_ft, '(fine‑tuning 15 capas)')

# ======================
# Guardado y conversión
# ======================
model.save('model_improved.h5')
tflite = tf.lite.TFLiteConverter.from_keras_model(model).convert()
with open('waste_classifier.tflite','wb') as f:
    f.write(tflite)
print("Guardados: model_improved.h5 y waste_classifier.tflite")

# ======================
# Evaluación final
# ======================
eval_ds = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR, validation_split=0.3, subset='validation',
    seed=SEED, image_size=(IMG_HEIGHT,IMG_WIDTH),
    batch_size=BATCH_SIZE, label_mode='categorical'
).cache().prefetch(AUTOTUNE)

y_true,y_pred = [],[]
for X,y in eval_ds:
    p = model.predict(X)
    y_true += list(np.argmax(y.numpy(),1))
    y_pred += list(np.argmax(p,1))

cm = confusion_matrix(y_true, y_pred)
plt.figure(figsize=(8,6))
sns.heatmap(cm, annot=True, fmt='d', xticklabels=class_names,
            yticklabels=class_names, cmap='Blues')
plt.xlabel("Predicción"); plt.ylabel("Real"); plt.title("Confusion Matrix")
plt.show()

print(classification_report(y_true,y_pred,
      target_names=class_names, digits=4))
