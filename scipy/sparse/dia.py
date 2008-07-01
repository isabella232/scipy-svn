"""Sparse DIAgonal format"""

__docformat__ = "restructuredtext en"

__all__ = ['dia_matrix','isspmatrix_dia']

from numpy import asarray, asmatrix, matrix, zeros, arange, array, \
        empty_like, intc, atleast_1d, atleast_2d, add, multiply, \
        unique

from base import isspmatrix, _formats
from data import _data_matrix
from sputils import isscalarlike, isshape, upcast, getdtype, isdense

from sparsetools import dia_matvec

class dia_matrix(_data_matrix):
    """Sparse matrix with DIAgonal storage

    This can be instantiated in several ways:
        dia_matrix(D)
            with a dense matrix

        dia_matrix(S)
            with another sparse matrix S (equivalent to S.todia())

        dia_matrix((M, N), [dtype])
            to construct an empty matrix with shape (M, N),
            dtype is optional, defaulting to dtype='d'.

        dia_matrix((data, diags), shape=(M, N))
            where the ``data[k,:]`` stores the diagonal entries for
            diagonal ``diag[k]`` (See example below)


    Examples
    --------

    >>> from scipy.sparse import *
    >>> from scipy import *
    >>> dia_matrix( (3,4), dtype=int8).todense()
    matrix([[0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]], dtype=int8)

    >>> data = array([[1,2,3,4]]).repeat(3,axis=0)
    >>> diags = array([0,-1,2])
    >>> dia_matrix( (data,diags), shape=(4,4)).todense()
    matrix([[1, 0, 3, 0],
            [1, 2, 0, 4],
            [0, 2, 3, 0],
            [0, 0, 3, 4]])

    """

    def __init__(self, arg1, shape=None, dtype=None, copy=False):
        _data_matrix.__init__(self)

        if isspmatrix_dia(arg1):
            if copy:
                arg1 = arg1.copy()
            self.data  = arg1.data
            self.diags = arg1.diags
            self.shape = arg1.shape
        elif isspmatrix(arg1):
            if isspmatrix_dia(arg1) and copy:
                A = arg1.copy()
            else:
                A = arg1.todia()
            self.data  = A.data
            self.diags = A.diags
            self.shape = A.shape
        elif isinstance(arg1, tuple):
            if isshape(arg1):
                # It's a tuple of matrix dimensions (M, N)
                # create empty matrix
                self.shape = arg1   #spmatrix checks for errors here
                self.data  = zeros( (0,0), getdtype(dtype, default=float))
                self.diags = zeros( (0), dtype=intc)
            else:
                try:
                    # Try interpreting it as (data, diags)
                    data, diags = arg1
                except:
                    raise ValueError, "unrecognized form for dia_matrix constructor"
                else:
                    if shape is None:
                        raise ValueError,'expected a shape argument'
                    self.data  = atleast_2d(array(arg1[0],dtype=dtype,copy=copy))
                    self.diags = atleast_1d(array(arg1[1],dtype='i',copy=copy))
                    self.shape = shape
        else:
            #must be dense, convert to COO first, then to DIA
            try:
                arg1 = asarray(arg1)
            except:
                raise ValueError, "unrecognized form for" \
                        " %s_matrix constructor" % self.format
            from coo import coo_matrix
            A = coo_matrix(arg1).todia()
            self.data  = A.data
            self.diags = A.diags
            self.shape = A.shape


        #check format
        if self.diags.ndim != 1:
            raise ValueError,'diags array must have rank 1'

        if self.data.ndim != 2:
            raise ValueError,'data array must have rank 2'

        if self.data.shape[0] != len(self.diags):
            raise ValueError,'number of diagonals (%d) ' \
                    'does not match the number of diags (%d)' \
                    % (self.data.shape[0], len(self.diags))

        if len(unique(self.diags)) != len(self.diags):
            raise ValueError,'offset array contains duplicate values'

    def __repr__(self):
        nnz = self.getnnz()
        format = self.getformat()
        return "<%dx%d sparse matrix of type '%s'\n" \
               "\twith %d stored elements (%d diagonals) in %s format>" % \
               ( self.shape +  (self.dtype.type, nnz, self.data.shape[0], \
                 _formats[format][1],) )

    def getnnz(self):
        """number of nonzero values

        explicit zero values are included in this number
        """
        M,N = self.shape
        nnz = 0
        for k in self.diags:
            if k > 0:
                nnz += min(M,N-k)
            else:
                nnz += min(M+k,N)
        return nnz

    nnz = property(fget=getnnz)


    def __mul__(self, other): # self * other
        """ Scalar, vector, or matrix multiplication
        """
        if isscalarlike(other):
            return dia_matrix((other * self.data, self.diags),self.shape)
        else:
            return self.dot(other)

    def matmat(self, other):
        if isspmatrix(other):
            M, K1 = self.shape
            K2, N = other.shape
            if (K1 != K2):
                raise ValueError, "shape mismatch error"

            return self.tocsr() * other
            #TODO handle sparse/sparse matmat here
        else:
            return self.tocsr() * other
            #TODO handle sparse/dense matmat here


    def matvec(self,other):
        x = asarray(other)

        if x.ndim == 1:
            x = x.reshape(-1,1)
        if self.shape[1] != x.shape[0]:
            raise ValueError, "dimension mismatch"

        y = zeros((self.shape[0],x.shape[1]), dtype=upcast(self.dtype,x.dtype))
        temp = empty_like( y )

        L = self.data.shape[1]
        M,N = self.shape

        dia_matvec(M,N, len(self.diags), L, self.diags, self.data, x.ravel(), y.ravel())

        if isinstance(other, matrix):
            y = asmatrix(y)

        if other.ndim == 1:
            # If 'other' was a 1d array, reshape the result
            y = y.reshape(-1)

        return y

    def todia(self,copy=False):
        if copy:
            return self.copy()
        else:
            return self

    def tocsr(self):
        #this could be faster
        return self.tocoo().tocsr(sum_duplicates=False)

    def tocsc(self):
        #this could be faster
        return self.tocoo().tocsc(sum_duplicates=False)

    def tocoo(self):
        num_data = len(self.data)
        len_data = self.data.shape[1]

        row = arange(len_data).reshape(1,-1).repeat(num_data,axis=0)
        col = row.copy()

        for i,k in enumerate(self.diags):
            row[i,:] -= k

        mask  = (row >= 0)
        mask &= (row < self.shape[0])
        mask &= (col < self.shape[1])
        mask &= self.data != 0
        row,col,data = row[mask],col[mask],self.data[mask]
        row,col,data = row.reshape(-1),col.reshape(-1),data.reshape(-1)

        from coo import coo_matrix
        return coo_matrix((data,(row,col)),shape=self.shape)

    # needed by _data_matrix
    def _with_data(self,data,copy=True):
        """Returns a matrix with the same sparsity structure as self,
        but with different data.  By default the structure arrays
        (i.e. .indptr and .indices) are copied.
        """
        if copy:
            return dia_matrix( (data,self.diags.copy()), shape=self.shape)
        else:
            return dia_matrix( (data,self.diags), shape=self.shape)


from sputils import _isinstance

def isspmatrix_dia(x):
    return _isinstance(x, dia_matrix)