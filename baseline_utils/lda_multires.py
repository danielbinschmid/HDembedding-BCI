#!/usr/bin/env python3

''' 
LDA with variable precision 
'''

import numpy as np

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

__author__ = "Michael Hersche"
__email__ = "herschmi@ethz.ch"

class lda_multires(LinearDiscriminantAnalysis):

	def __init__(self,solver='svd',shrinkage=None,precision=64):		
		'''	LDA with self defined classification using quantized class vectors 
		Parameters
		----------
		sovler : string 
		shrinkage: string 
		precision: int
			{64,32,16}
		'''

		super().__init__(solver=solver,shrinkage=shrinkage)


		if precision==64: # use standard 
			self.score=super().score
		elif precision == 32: 
			self.score = self._quantscore
			self._dtype = np.float32
		elif precision ==16: 
			self.score = self._quantscore
			self._dtype = np.float16
		else :
			raise ValueError('LDA invalid precision') 
			


	def _quantscore(self,X,y,sample_weight=None):


		y_hat = self._quantpredict(X)

		n_samples = y.shape

		score = np.sum(y_hat==y)/n_samples

		return score


	def _quantpredict(self,X):


		coef = self.coef_.astype(self._dtype)
		intercept = self.intercept_.astype(self._dtype)
		X = X.astype(self._dtype)
		est = np.matmul(X,np.transpose(coef,(1,0)))+intercept

		return np.argmax(est,axis=1)+1



		