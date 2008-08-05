""" ND Interpolation wrapping using code from NDImage"""

from numpy import array, arange, NaN
import numpy as np
import _nd_image

class InterpolateNd:
    def __init__(self, data, starting_coords =None, spacings = None, 
                        order=3, out=NaN):
        """ data = array or list of lists
            starting_coords = None, list, 1D array or 2D (nx1) array
            spacings = None, list, 1D array or 2D (nx1) array
            out = string in 'nearest', 'wrap', 'reflect', 'mirror', 'constant'
                        or just NaN
        """
        
        # FIXME : include spline filtering
        
        if order < 0 or order > 5:
            raise RuntimeError, 'spline order not supported'
        
        # checking format of input
        data = array(data)
        
        # for proper processing later, starting_coords and spacings must be of shape (data.ndim, 1)
        if starting_coords == None:
            starting_coords = np.zeros(( data.ndim, 1 ))
        else:
            starting_coords = array(starting_coords)
            assert starting_coords.size == data.ndim, "There must be one element of \
                            starting_coords per data dimension.  Size mismatch."
            starting_coords = reshape(starting_coords, (data.ndim, 1))
        if spacings == None:
            spacings = np.zeros(( data.ndim, 1 ))
        else:
            spacings = array(spacings)
            assert starting_coords.size == data.ndim, "There must be one element of \
                            starting_coords per data dimension"
            spacings = reshape(spacings, (data.ndim, 1))
        
        # storing relevant data
        self._data_array = data
        self.ndim = data.ndim
        self._shape = np.shape(data)
        self._spacings = spacings
        self._min_coords = starting_coords
        self._max_coords = self._min_coords + self._shape*self._spacings
        self.out = out
        self.order = order
        
    def __call__(self, coordinates):
        """ coordinates is an n x L array, where n is the dimensionality of the data
            and L is number of points.  That is, each column of coordinates
            indicates a point at which to interpolate.
        """
        
        # format checking
        coordinates = array(coordinates)
        if coordinates.ndim == 1: # passed in a single point
            coordinates = np.reshape(coordinates, ( self.ndim, 1))
        assert coordinates.ndim == 2, "Coordinates must be 1 or 2 dimensional"
        n, num_points = coordinates.shape
        assert n == self.ndim, "The first dimension of the input \
                must be as long as the dimensionality of the space"
        
        # converting from points in ND space to array indices
        indices = (coordinates - self._min_coords)/self._spacings
        
        if self.out in ['nearest', 'wrap', 'reflect', 'mirror', 'constant']:
            # out of bounds can be performed by _interpolate_array_entry
            result = self._interpolate_array_entry(self._data_array, indices, self.order, out = self.out)
        else:
            # need to return NaN when entry is out of bounds
            in_bounds_mask = self._index_in_bounds(indices)
            in_bounds = indices[:, in_bounds_mask]
            out_bounds = indices[:, ~in_bounds_mask]
            
            result = np.zeros(num_points)
            result[in_bounds_mask] = \
                self._interpolate_array_entry(self._data_array, indices[:,in_bounds_mask], self.order)
            result[~in_bounds_mask] = NaN
            
        return result
        
    
    def _interpolate_array_entry(self, data_array, indices, order, out='nearest'):
        """ indices is nxL matrix, where n is data_array.ndim
            returns array of length L giving interpolated entries.
        """
        
        extrap_code_register = { 'nearest':0,
                                        'wrap': 1,
                                        'reflect':2,
                                        'mirror':3,
                                        'constant':4,
                                        }
        
        n, L = np.shape(indices)
        
        output = np.zeros( L , dtype=np.float64 ) # place to store the data

        # geometric transform takes data_array, interpolates its values at indices, and
        # stores those values in output.  Other parameters give details of interpolation method.
        _nd_image.geometric_transform(data_array, None, indices, None, None, \
               output, order, extrap_code_register[out], 0.0, None, None)
               
        return output
        
    def _index_in_bounds(self, indices):
        """ return an array of bools saying which
            points are in interpolation bounds
        """
        shape_as_column_vec = np.reshape(self._shape, (self.ndim, 1))
        
        # entry is 1 if that coordinate of a point is in its bounds
        index_in_bounds = (0 <= indices) & \
                                    (indices <= shape_as_column_vec)
        
        # for each point, number of coordinates that are in bounds
        num_indices_in_bounds = np.sum(index_in_bounds, axis=0)
        
        # True if each coordinate for the point is in bounds
        return num_indices_in_bounds == self.ndim
        
    def _coord_in_bounds(self, coordinates):
        """ return an array of bools saying which
            points are in interpolation bounds
        """
        # entry is 1 if that coordinate of a point is in its bounds
        coord_in_bounds = (self._min_coords <= coordinates) & \
                                    (coordinates <= self._max_coords)
        
        # for each point, number of coordinates that are in bounds
        num_coords_in_bounds = np.sum(coord_in_bounds, axis=0)
        
        # True if each coordinate for the point is in bounds
        return num_coords_in_bounds == self.ndim
        
    
        
    
        
        
        
    
    