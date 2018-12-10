#!/usr/bin/env python3

''' 
import features DATASET IV 2a either CSP or Riemannian 
select features with fisher score 
'''

import numpy as np
import sys, os
import time
from get_data_IV2a import get_data
from riemannian_multiscale import riemannian_multiscale
from filters import load_filterbank 
from sklearn.model_selection import KFold
from csp import generate_projection,generate_eye,extract_feature

__author__ = "Michael Hersche"
__email__ = "herschmi@ethz.ch"




def load_feature_IV2a(data_path,subject, twind_sel=[],band_sel=[],feat_type='Riemann', encoding='spat', split = 0, nsplits = 4):
	'''	returns features and labels of training and test set 

	Keyword arguments:
	subject -- subject in [1,2,...,9]

	twind_sel -- selection of timewindows use,  if shape = (temp_dim,) : load precalculated features 
												if shape = (temp_dim,2): generate new set of features 
	band_sel  -- selection of frequency bands, shape = (freq_dim,) : load precalculated features 
												
	feat_type -- {"Riemann","Whitened_Euclid","CSP"}
	encoding -- 'single', 'spat'
	


	Return:	train_feat -- numpy array with dimension [trial, temp_wind, bands, CSP/R dim ]
			train_label -- numpy array with entries [1,2,3,4]

			eval_feat -- numpy array with dimension [trial, temp_wind, bands, CSP/R dim ]
			eval_label -- numpy array with entries [1,2,3,4]

	'''

	if twind_sel.ndim == 1: 
		#print("Load precalculated features")
		sub_path = 'S' + str(subject) + '.npy.npz'

		if feat_type == 'CSP':
			path = data_path + 'csp_feat/' + sub_path
		elif feat_type == 'Riemann': 
			path = data_path + 'riem_cov_mat/' + sub_path

		#print(path)

		with np.load(path) as data:
			train_feat = data['train_feature']
			train_label = data['train_label'].astype(int) 
			eval_feat = data['eval_feature']
			eval_label = data['eval_label'].astype(int)

		# get dimensions
		N_tr_trial = train_feat.shape[0] 
		N_ev_trial = eval_feat.shape[0]
		N_bands = len(band_sel)
		N_twind = len(twind_sel)

		# If Riemannian features, apply halfvectorization to covariance matrices 
		if feat_type == 'CSP':	
			train_feat = train_feat[np.ix_(np.arange(N_tr_trial),twind_sel,band_sel)].reshape(N_tr_trial,N_twind,N_bands,24)
			eval_feat = eval_feat[np.ix_(np.arange(N_ev_trial),twind_sel,band_sel)].reshape(N_ev_trial,N_twind,N_bands,24)
			N_feat = 24
		else: 
			# select necessairy bands and twindows
			train_feat = train_feat[np.ix_(np.arange(N_tr_trial),twind_sel,band_sel)].reshape(N_tr_trial,N_twind,N_bands,22,22)
			eval_feat = eval_feat[np.ix_(np.arange(N_ev_trial),twind_sel,band_sel)].reshape(N_ev_trial,N_twind,N_bands,22,22)
			# transform covmat to vector
			train_feat, eval_feat = transform_covmat(train_feat,eval_feat)
			N_feat = 253


	else: # generate new features 
		#print('Generate new set of features')
		if feat_type == 'CSP': 
			train_feat,train_label,eval_feat,eval_label = generate_CSP_feat(data_path,subject,twind_sel ,band_sel,feat_type)
			N_feat = 24
		elif feat_type == 'Riemann': 
			train_feat,train_label,eval_feat,eval_label = generate_Riemann_feat(data_path,subject,twind_sel ,band_sel,feat_type)
			# N_feat = 253
		else: 
			print("invalid feature type")
		
		twind_sel = np.arange(twind_sel.shape[0]) 


	# get dimensions
	N_tr_trial = train_feat.shape[0] 
	N_ev_trial = eval_feat.shape[0]
	N_bands = len(band_sel)
	N_twind = len(twind_sel)
	

	# Normalization of data
	# sigma = np.reshape(np.std(train_feat,axis = 0),(1, N_twind, N_bands,N_feat))

	# # # #sigma[sigma == 0] = 1
	# mean = np.reshape(np.mean(train_feat,axis = 0),(1, N_twind, N_bands,N_feat))
	
	# train_feat = (train_feat - mean)/sigma
	# eval_feat = (eval_feat - mean)/sigma

	# reshape of features 
	if encoding == 'single':

		train_feat = np.reshape(np.transpose(train_feat,(0,2,1,3)),(N_tr_trial,1,-1))
		eval_feat = np.reshape(np.transpose(eval_feat,(0,2,1,3)),(N_ev_trial,1,-1))
		# reshape features for svm 
		svm_train_feat = np.reshape(train_feat,(N_tr_trial,-1))
		svm_eval_feat = np.reshape(eval_feat,(N_ev_trial,-1))

	elif encoding == 'spat':
		# no fisher scoring , just take twind_sel and reshape to 
		train_feat = np.reshape(np.transpose(train_feat,(0,2,1,3)),(N_tr_trial,1,N_bands,-1))
		eval_feat = np.reshape(np.transpose(eval_feat,(0,2,1,3)),(N_ev_trial,1,N_bands,-1))
		# reshape features for svm 
		svm_train_feat = np.reshape(train_feat,(N_tr_trial,-1))
		svm_eval_feat = np.reshape(eval_feat,(N_ev_trial,-1))


	return train_feat,svm_train_feat, train_label, eval_feat,svm_eval_feat, eval_label


def load_XVAL_feature_IV2a(subject, twind_sel=[],band_sel=[],feat_type='Riemann', encoding='spat',split = 0, n_splits = 4):

	# load training features 
	feat,svm_feat,label,_,_,_ = load_feature_IV2a(subject, twind_sel,band_sel,feat_type, encoding, nfisher,split, n_splits)

	kf = KFold(n_splits=n_splits)
	split_cnt = 0 
	for train_index, test_index in kf.split(svm_feat):
		
		if split_cnt == split:
			eval_feat = feat[test_index]
			eval_label = label[test_index]
			train_feat = feat[train_index]
			train_label = label[train_index]
			svm_train_feat = svm_feat[train_index]
			svm_eval_feat = svm_feat[test_index]
		split_cnt += 1 
		
	return train_feat, svm_train_feat,train_label, eval_feat, svm_eval_feat,eval_label



def transform_covmat(train_feat,eval_feat):
	'''	transform covariance matrices to vectors for every band and temp window and trial
	'''
	
	N_tr_trial, N_twind, N_bands,N_channel,_ = train_feat.shape 
	N_ev_trial = eval_feat[:,0,0,0,0].size
	N_Rfeat = int(N_channel*(N_channel+1)/2)



	out_tr_feat = np.zeros((N_tr_trial,N_twind,N_bands,N_Rfeat))
	# Half vectorization training features 
	for trial in range(N_tr_trial):
		for twind in range(N_twind):
			for band in range(N_bands): 
				out_tr_feat[trial,twind,band] = half_vectorization(train_feat[trial,twind,band])

	
	out_eval_feat = np.zeros((N_ev_trial,N_twind,N_bands,N_Rfeat))

	# half vectorization evval features 
	for trial in range(N_ev_trial):
		for twind in range(N_twind):
			for band in range(N_bands): 
				out_eval_feat[trial,twind,band] = half_vectorization(eval_feat[trial,twind,band])

	return out_tr_feat,out_eval_feat

	

def half_vectorization(mat):
	'''	Calculates half vectorization of a matrix

	Keyword arguments:
	mat -- symetric numpy array of size 22 x 22
	
	
	Return:	vectorized matrix 
	'''
	#mat = logm(mat)

	_,N = mat.shape 

	NO_elements = ((N+1)*N/2)
	NO_elements = int(NO_elements)
	out_vec = np.zeros(NO_elements)

	# fill diagonal elements with factor one 
	for diag in range(0,N):
		out_vec[diag] = mat[diag,diag]


	sqrt2 = np.sqrt(2)
	idx = N
	for col in range(1,N):
		for row in range(0,col):
			out_vec[idx] = sqrt2*mat[row,col]
			idx +=1

	return out_vec

def generate_Riemann_feat(data_path,subject,twind,freq_band,riem_settings):

	fs = 250. # sampling frequency 
	NO_channels = 22 # number of EEG channels 
	bw = np.array([2,4,8,16,32]) # bandwidth of filtered signals 
	ftype = 'butter' # 'fir', 'butter'
	forder= 2 # 4
	filter_bank = load_filterbank(bw,fs,order=forder,max_freq=40,ftype = ftype)[freq_band] # get filterbank coeffs 
	time_windows = (twind*fs).astype(int)
	rho = 0.1

	# load data 
	train_data,train_label = get_data(subject,training=True,PATH=data_path)
	train_label = train_label.astype(int)
	test_data,test_label = get_data(subject,training=False,PATH=data_path)
	test_label = test_label.astype(int)

	# 1. calculate features and mean covariance for training 
	riemann = riemannian_multiscale(filter_bank,time_windows,riem_opt =riem_settings,rho = rho,vectorized = False)
	t1 = time.time()
	train_feat = riemann.fit(train_data)
	t2 = time.time()
	#print("Riemann train time {}".format(t2-t1))
	# 2. Testing features 
	test_feat = riemann.features(test_data)
	t3 = time.time()
	#print("Riemann inference time {}".format(t3-t2))


	return train_feat,train_label,test_feat,test_label


def generate_CSP_feat(data_path,subject,twind,freq_band,riem_settings):

	fs = 250. # sampling frequency 
	NO_channels = 22 # number of EEG channels 
	bw = np.array([2,4,8,16,32]) # bandwidth of filtered signals 
	ftype = 'butter' # 'fir', 'butter'
	forder= 2 # 4
	filter_bank = load_filterbank(bw,fs,order=forder,max_freq=40,ftype = ftype)[freq_band] # get filterbank coeffs 
	time_windows = (twind*fs).astype(int)
	NO_csp = 24 # Total number of CSP feature per band and timewindow

	# load data 
	train_data,train_label = get_data(subject,training=True,PATH=data_path)
	train_label = train_label.astype(int)
	test_data,test_label = get_data(subject,training=False,PATH=data_path)
	test_label = test_label.astype(int)

	w = generate_projection(train_data,train_label, NO_csp,filter_bank,time_windows)
	train_feat = extract_feature(train_data,w,filter_bank,time_windows, False)
	test_feat = extract_feature(test_data,w,filter_bank,time_windows, False)

	return train_feat,train_label,test_feat,test_label