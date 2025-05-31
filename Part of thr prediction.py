import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input

# --- 外部数据处理 ---
external_df = pd.read_csv('pm25_final_external.csv', parse_dates=['Timestamp'], index_col='Timestamp')
external_df["PM2.5"] = pd.to_numeric(external_df["PM2.5"], errors='coerce')
external_df.dropna(subset=["PM2.5"], inplace=True)
scaler_external = MinMaxScaler()
external_df["PM2.5_scaled"] = scaler_external.fit_transform(external_df[["PM2.5"]])

# --- 内部数据处理 ---
internal_df = pd.read_csv('_____PM2_5_____Updated_Station_.csv', parse_dates=['Timestamp'])
internal_df = internal_df.dropna(subset=["PM2.5", "Timestamp"])
internal_df.set_index("Timestamp", inplace=True)
internal_station = internal_df[internal_df["Station"] == "Baker Street"].copy()
scaler_internal = MinMaxScaler()
internal_station["PM2.5_scaled"] = scaler_internal.fit_transform(internal_station[["PM2.5"]])

# 序列创建函数
def create_sequences(data, seq_length, future_steps):
    X, y = [], []
    for i in range(len(data) - seq_length - future_steps):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length:i+seq_length+future_steps])
    return np.array(X), np.array(y)

sequence_length_external = 24 * 7  # 外部数据用一周
sequence_length_internal = 24      # 内部数据只用一天
future_steps = 24

# 外部数据序列创建
X_ext, y_ext = create_sequences(external_df["PM2.5_scaled"].values, sequence_length_external, future_steps)
X_ext = X_ext.reshape(X_ext.shape[0], sequence_length_external, 1)
y_ext = y_ext.reshape(y_ext.shape[0], future_steps)

# 内部数据序列创建
X_int, y_int = create_sequences(internal_station["PM2.5_scaled"].values, sequence_length_internal, future_steps)
X_int = X_int.reshape(X_int.shape[0], sequence_length_internal, 1)
y_int = y_int.reshape(y_int.shape[0], future_steps)

# 构建模型函数
def build_and_train_model(X, y, epochs=10, batch_size=32):
    model = Sequential([
        Input(shape=(X.shape[1], 1)),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(64),
        Dropout(0.2),
        Dense(y.shape[1])
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=epochs, batch_size=batch_size)
    return model

# 训练外部数据模型
batch_size_ext = min(32, X_ext.shape[0])
model_ext = build_and_train_model(X_ext, y_ext, epochs=10, batch_size=batch_size_ext)

# 训练内部数据模型
batch_size_int = min(32, X_int.shape[0])
model_int = build_and_train_model(X_int, y_int, epochs=10, batch_size=batch_size_int)

# 分别预测
predicted_ext = model_ext.predict(X_ext[-1].reshape(1, sequence_length_external, 1)).flatten()
predicted_ext = scaler_external.inverse_transform(predicted_ext.reshape(-1, 1))

predicted_int = model_int.predict(X_int[-1].reshape(1, sequence_length_internal, 1)).flatten()
predicted_int = scaler_internal.inverse_transform(predicted_int.reshape(-1, 1))

# 绘制预测结果
plt.figure(figsize=(14, 6))
plt.plot(predicted_ext, marker='o', label='External PM2.5')
plt.plot(predicted_int, marker='x', label='Internal PM2.5')
plt.axhline(y=50, color='r', linestyle='--')
plt.title('Next 24 Hours PM2.5 Predictions')
plt.xlabel('Hour Ahead')
plt.ylabel('PM2.5 (µg/m³)')
plt.legend()
plt.grid(True)
plt.show()

# 输出规避小时
avoid_hours_ext = np.where(predicted_ext.flatten() > 50)[0]
avoid_hours_int = np.where(predicted_int.flatten() > 50)[0]

print("外部需规避小时段:", avoid_hours_ext)
print("内部需规避小时段:", avoid_hours_int)