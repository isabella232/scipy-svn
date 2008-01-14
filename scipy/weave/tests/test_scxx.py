""" Test refcounting and behavior of SCXX.
"""
import unittest
import time
import os,sys

from scipy.testing import *
set_local_path()
from test_scxx_object import *
from test_scxx_sequence import *
from test_scxx_dict import *


if __name__ == "__main__":
    unittest.main()