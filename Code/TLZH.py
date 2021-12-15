import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from PyEMD import EEMD, EMD,CEEMDAN
from keras.models import Sequential
from keras.callbacks import ModelCheckpoint
from keras.layers import Dense, Activation, Conv1D, LSTM, Dropout, Reshape, Bidirectional
from evaluate_data import *
import keras
from keras.optimizers import *


def data_split(data, train_len, lookback_window):

    X_all = []
    Y_all = []
    data = data.reshape(-1, )
    for i in range(lookback_window, len(data)):
        X_all.append(data[i - lookback_window:i])
        Y_all.append(data[i])

    X_train = X_all[:train_len]
    X_test = X_all[train_len:]

    Y_train = Y_all[:train_len]
    Y_test = Y_all[train_len:]

    return [np.array(X_train), np.array(Y_train), np.array(X_test), np.array(Y_test)]


def data_split_LSTM(data_regular):  # data split f
	X_train = data_regular[0].reshape(data_regular[0].shape[0], data_regular[0].shape[1], 1)
	Y_train = data_regular[1].reshape(data_regular[1].shape[0], 1)
	X_test = data_regular[2].reshape(data_regular[2].shape[0], data_regular[2].shape[1], 1)
	y_test = data_regular[3].reshape(data_regular[3].shape[0], 1)
	return [X_train, Y_train, X_test, y_test]


def load_data(file):
	dataset = pd.read_csv(file, header=0, index_col=0, parse_dates=True)

	df = pd.DataFrame(dataset)  # 整体数据的全部字典类型
	do = df['all_time_change']  # 返回all_time_change那一列，用字典的方式
	print(do)
	full_data = []
	for i in range(0, len(do)):
		full_data.append([do[i]])

	scaler_data = MinMaxScaler(feature_range=(0, 1))
	full_data = scaler_data.fit_transform(full_data)   #归一化
	print('Size of the Dataset: ', full_data.shape)

	return full_data, scaler_data

def imf_data(data, lookback_window):
	X1 = []
	for i in range(lookback_window, len(data)):
		X1.append(data[i - lookback_window:i])
	X1.append(data[len(data) - 1:len(data)])
	X_train = np.array(X1)
	return X_train

def model_LSTM(step_num):
	model = Sequential()
	model.add(LSTM(50, input_shape=(step_num, 1)))   #已经确定10步长
	model.add(Dense(1))
	model.compile(loss='mse', optimizer='adam')
	return model

def EEMD_LSTM_Model(X_train, Y_train,i):
	filepath = 'res/' + str(i) + '-{epoch:02d}-{val_acc:.2f}.h5'
	checkpoint = ModelCheckpoint(filepath, monitor='loss',verbose=1,save_best_only=False,mode='auto',period=10)
	callbacks_list = [checkpoint]
	model = Sequential()
	# model.add(Bidirectional(LSTM(50,activation='tanh', input_shape=(X_train.shape[1], X_train.shape[2]))))
	model.add(LSTM(50, activation='tanh', input_shape=(X_train.shape[1], X_train.shape[2])))
	model.add(Dense(50, activation='tanh'))
	model.add(Dense(1))
	model.compile(loss='mse', optimizer='adam')
	model.fit(X_train, Y_train, epochs=20, batch_size=1, validation_split=0.1, verbose=2, shuffle=True)
	return model

def main():
	temp = [
		"180",
		"181",
		"182",
		"183",
		"184",
		"185",
		"186",
		"187",
		"188",
		"189",
		"190",
		"191",
		"192",
		"193",
		"194",
		"195",
		"200",
		"201",
		"205",
		"210",
		"215",
		"220",
		"225",
		"230",
		"235",
		"240",
		]
	for j in range(len(temp)):
		print("************" + temp[j])

		full_data, scaler = load_data("E:\Code\CEEMDAN-LSTM--master\csv\ZH\data-" + temp[j] + "-1.csv")

		training_set_split = int(len(full_data) * 0.6)
		lookback_window = 2

		global result
		result = '\nEvaluation.'

		# #数组划分为不同的数据集
		data_regular = data_split(full_data, training_set_split, lookback_window)
		y_real = scaler.inverse_transform(data_regular[3].reshape(-1, 1)).reshape(-1, )

		# # CEEMDAN-LSTM
		ceemdan = CEEMDAN()
		ceemdan_imfs = ceemdan.ceemdan(full_data.reshape(-1), None, 8)
		ceemdan_imfs_prediction = []

		test = np.zeros([len(full_data) - training_set_split - lookback_window, 1])

		i = 1
		for imf in ceemdan_imfs:
			print('-' * 45)
			print('This is  ' + str(i) + '  time(s)')
			print('*' * 45)

			data_imf = data_split_LSTM(data_split(imf_data(imf, 1), training_set_split, lookback_window))
			test += data_imf[3]
			model = EEMD_LSTM_Model(data_imf[0][:], data_imf[1][:], i)  # [X_train, Y_train, X_test, y_test][60/;35/69]

			prediction_Y = model.predict(data_imf[2])
			ceemdan_imfs_prediction.append(prediction_Y)
			i += 1

		ceemdan_imfs_prediction = np.array(ceemdan_imfs_prediction)

		ceemdan_prediction = [0.0 for i in range(len(test))]
		ceemdan_prediction = np.array(ceemdan_prediction)
		for i in range(len(test)):
			t = 0.0
			for imf_prediction in ceemdan_imfs_prediction:
				t += imf_prediction[i][0]
			ceemdan_prediction[i] = t

		ceemdan_prediction = scaler.inverse_transform(ceemdan_prediction.reshape(-1, 1)).reshape(-1, )

		result += '\n\nMAE_ceemdan_lstm: {}'.format(MAE1(y_real, ceemdan_prediction))
		result += '\nRMSE_ceemdan_lstm: {}'.format(RMSE1(y_real, ceemdan_prediction))
		result += '\nMAPE_ceemdan_lstm: {}'.format(MAPE1(y_real, ceemdan_prediction))
		result += '\nR2_ceemdan_lstm: {}'.format(R2(y_real, ceemdan_prediction))

		# # TLCEEMDAN-LSTM
		ceemdan = CEEMDAN()
		tlceemdan_imfs = ceemdan.ceemdan(full_data.reshape(-1), None, 8)
		tlceemdan_imfs_prediction = []

		test = np.zeros([len(full_data) - training_set_split - lookback_window, 1])

		i = 1
		for imf in tlceemdan_imfs:
			print('-' * 45)
			print('This is  ' + str(i) + '  time(s)')
			print('*' * 45)

			data_imf = data_split_LSTM(data_split(imf_data(imf, 1), training_set_split, lookback_window))
			test += data_imf[3]

			model = keras.models.load_model("E:/Code/CEEMDAN-LSTM--master/ModelSave/ZH1/CEEMDAN-LSTM-imf" + str(i) + ".h5")
			# for l in model.layers:
			# 	print(l.name)
			# 	print(l.get_config())
			for layer in model.layers[:1]:
				layer.trainable = False
			model.compile(optimizer=Adam(lr=0.0001), loss='mse')
			print(data_imf[0].shape,data_imf[1].shape,data_imf[2].shape)
			model.fit(data_imf[0][:], data_imf[1][:],epochs=20, batch_size=1, validation_split=0.1, verbose=2, shuffle=True)
			prediction_tl = model.predict(data_imf[2])
			tlceemdan_imfs_prediction.append(prediction_tl)
			i += 1

		tlceemdan_imfs_prediction = np.array(tlceemdan_imfs_prediction)

		tlceemdan_prediction = [0.0 for i in range(len(test))]
		tlceemdan_prediction = np.array(tlceemdan_prediction)
		for i in range(len(test)):
			t = 0.0
			for tlimf_prediction in tlceemdan_imfs_prediction:
				t += tlimf_prediction[i][0]
			tlceemdan_prediction[i] = t

		tlceemdan_prediction = scaler.inverse_transform(tlceemdan_prediction.reshape(-1, 1)).reshape(-1, )

		result += '\n\nMAE_tlceemdan_lstm: {}'.format(MAE1(y_real, tlceemdan_prediction))
		result += '\nRMSE_tlceemdan_lstm: {}'.format(RMSE1(y_real, tlceemdan_prediction))
		result += '\nMAPE_tlceemdan_lstm: {}'.format(MAPE1(y_real, tlceemdan_prediction))
		result += '\nR2_tlceemdan_lstm: {}'.format(R2(y_real, tlceemdan_prediction))

		real = pd.DataFrame(y_real[:], columns=["TRUE"])
		predict_ceemdan_lstm = pd.DataFrame(ceemdan_prediction[:], columns=["predict_ceemdan"])
		predict_tl_ceemdan_lstm = pd.DataFrame(tlceemdan_prediction[:], columns=["predict_tl_ceemdan"])
		all = pd.concat([real, predict_ceemdan_lstm, predict_tl_ceemdan_lstm], axis=1)

		all.to_csv('E:/Code/CEEMDAN-LSTM--master/csv/TLPrediction2/' + temp[j] + '.csv', index=False)



		##################################################evaluation

		# print(result)

		# ###===============画图===========================
		# plt.rc('font', family='Times New Roman')
		# plt.figure(1, figsize=(4, 3))
		# plt.plot(y_real , 'black', label='True', linewidth=1, linestyle='-', marker='.')
		# plt.plot(ceemdan_prediction, 'blue', label='CEEMDAN-LSTM', linewidth=1, linestyle='-', markersize=1)
		# plt.plot(tlceemdan_prediction, 'red', label='TLCEEMDAN-LSTM', linewidth=1, linestyle='-', marker='^', markersize=1)
		# plt.xlabel('time(days)', fontsize=15)
		# plt.ylabel('height(mm)', fontsize=15)
		# plt.title('180')
		# plt.legend(loc='best')
		#
		# plt.show()



if __name__ == '__main__':

	main()
