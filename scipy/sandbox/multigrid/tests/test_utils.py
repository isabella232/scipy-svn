from scipy.testing import *

import numpy
import scipy
from numpy import matrix,array,diag,zeros,sqrt
from scipy import rand
from scipy.sparse import csr_matrix
from scipy.linalg import norm


from scipy.sandbox.multigrid.utils import approximate_spectral_radius, \
                                          infinity_norm, diag_sparse, \
                                          symmetric_rescaling, \
                                          expand_into_blocks



class TestUtils(TestCase):
    def test_approximate_spectral_radius(self):
        cases = []

        cases.append( matrix([[-4]]) )
        cases.append( array([[-4]]) )
        
        cases.append( array([[2,0],[0,1]]) )
        cases.append( array([[-2,0],[0,1]]) )
      
        cases.append( array([[100,0,0],[0,101,0],[0,0,99]]) )
        
        for i in range(1,5):
            cases.append( rand(i,i) )
       
        # method should be almost exact for small matrices
        for A in cases:
            Asp = csr_matrix(A)     
            assert_almost_equal( approximate_spectral_radius(A), norm(A,2) )
            assert_almost_equal( approximate_spectral_radius(Asp), norm(A,2) )
      
        #TODO test larger matrices
    
    def test_infinity_norm(self):
        A = matrix([[-4]])
        assert_equal(infinity_norm(csr_matrix(A)),4)

        A = matrix([[1,0,-5],[-2,5,0]])
        assert_equal(infinity_norm(csr_matrix(A)),7)

        A = matrix([[0,1],[0,-5]])
        assert_equal(infinity_norm(csr_matrix(A)),5)

        A = matrix([[1.3,-4.7,0],[-2.23,5.5,0],[9,0,-2]])
        assert_equal(infinity_norm(csr_matrix(A)),11)

    def test_diag_sparse(self):
        #check sparse -> array
        A = matrix([[-4]])
        assert_equal(diag_sparse(csr_matrix(A)),[-4])

        A = matrix([[1,0,-5],[-2,5,0]])
        assert_equal(diag_sparse(csr_matrix(A)),[1,5])

        A = matrix([[0,1],[0,-5]])
        assert_equal(diag_sparse(csr_matrix(A)),[0,-5])

        A = matrix([[1.3,-4.7,0],[-2.23,5.5,0],[9,0,-2]])
        assert_equal(diag_sparse(csr_matrix(A)),[1.3,5.5,-2])

        #check array -> sparse
        A = matrix([[-4]])
        assert_equal(diag_sparse(array([-4])).todense(),csr_matrix(A).todense())

        A = matrix([[1,0],[0,5]])
        assert_equal(diag_sparse(array([1,5])).todense(),csr_matrix(A).todense())

        A = matrix([[0,0],[0,-5]])
        assert_equal(diag_sparse(array([0,-5])).todense(),csr_matrix(A).todense())

        A = matrix([[1.3,0,0],[0,5.5,0],[0,0,-2]])
        assert_equal(diag_sparse(array([1.3,5.5,-2])).todense(),csr_matrix(A).todense())


    def test_symmetric_rescaling(self):
        cases = []
        cases.append( diag_sparse(array([1,2,3,4])) )
        cases.append( diag_sparse(array([1,0,3,4])) )

        A = array([ [ 5.5,  3.5,  4.8],
                    [ 2. ,  9.9,  0.5],
                    [ 6.5,  2.6,  5.7]])
        A = csr_matrix( A )
        cases.append(A)
        P = diag_sparse([1,0,1])
        cases.append( P*A*P )
        P = diag_sparse([0,1,0])
        cases.append( P*A*P )
        P = diag_sparse([1,-1,1])
        cases.append( P*A*P )

        for A in cases:
            D_sqrt,D_sqrt_inv,DAD = symmetric_rescaling(A)

            assert_almost_equal( diag_sparse(A) > 0, diag_sparse(DAD) )
            assert_almost_equal( diag_sparse(DAD), D_sqrt*D_sqrt_inv )

            D_sqrt,D_sqrt_inv = diag_sparse(D_sqrt),diag_sparse(D_sqrt_inv)
            assert_almost_equal((D_sqrt_inv*A*D_sqrt_inv).todense(), DAD.todense())

    def test_expand_into_blocks(self):
        cases = []
        cases.append( ( matrix([[1]]), (1,2) ) )
        cases.append( ( matrix([[1]]), (2,1) ) )
        cases.append( ( matrix([[1]]), (2,2) ) )
        cases.append( ( matrix([[1,2]]), (1,2) ) )
        cases.append( ( matrix([[1,2],[3,4]]), (2,2) ) )
        cases.append( ( matrix([[0,0],[0,0]]), (3,1) ) )
        cases.append( ( matrix([[0,1,0],[0,2,3]]), (3,2) ) )
        cases.append( ( matrix([[1,0,0],[2,0,3]]), (2,5) ) )

        for A,shape in cases:
            m,n = shape
            result = expand_into_blocks(csr_matrix(A),m,n).todense()

            expected = zeros((m*A.shape[0],n*A.shape[1]))
            for i in range(m):
                for j in range(n):
                    expected[i::m,j::n] = A

            assert_equal(expected,result)


if __name__ == '__main__':
    unittest.main()