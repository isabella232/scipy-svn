import scipy.sandbox.models as S
import unittest
import numpy.random as R
import numpy as N
from numpy.testing import *
from scipy.sandbox.models.glm import Model

W = R.standard_normal


class test_Regression(ScipyTestCase):

    def check_Logistic(self):
        X = W((40,10))
        Y = N.greater(W((40,)), 0)
        family = S.family.Binomial()
        model = Model(design=X, family=S.family.Binomial())
        results = model.fit(Y)
        self.assertEquals(results.df_resid, 30)

    def check_Logisticdegenerate(self):
        X = W((40,10))
        X[:,0] = X[:,1] + X[:,2]
        Y = N.greater(W((40,)), 0)
        family = S.family.Binomial()
        model = Model(design=X, family=S.family.Binomial())
        results = model.fit(Y)
        self.assertEquals(results.df_resid, 31)


def suite():
    suite = unittest.makeSuite(RegressionTest)
    return suite
        
if __name__ == "__main__":
    ScipyTest().run()
