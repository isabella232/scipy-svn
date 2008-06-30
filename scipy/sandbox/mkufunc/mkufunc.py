""" mkufunc (make U function)


Author: Ilan Schnell (with help from Travis Oliphant and Eric Jones)
"""
import sys
import re
import os, os.path
import cStringIO
from types import FunctionType

import numpy
from scipy import weave

from funcutil import func_hash


def translate(f, argtypes):
    """ Return pypy's C output for a given function and argument types.

    The cache files are in weave's directory.
    """
    cache_file_name = os.path.join(weave.catalog.default_dir(),
                                   'pypy_%s.c' % func_hash(f, salt=argtypes))
    try:
        return open(cache_file_name).read()
    
    except IOError:
        from interactive import Translation
        
        t = Translation(f, backend='c')
        t.annotate(argtypes)
        t.source()
        
        os.rename(t.driver.c_source_filename, cache_file_name)
        
        return translate(f, argtypes)


class Ctype:
    def __init__(self, npy, c):
        self.npy = npy
        self.c = c

typedict = {
    int:    Ctype('NPY_LONG',   'long'  ),
    float:  Ctype('NPY_DOUBLE', 'double'),
}


class Cfunc(object):
    """ C compiled python functions

    >>> def sqr(x):
    ...     return x * x

    >>> signature = [int, int] # only the input arguments are used here
    
    compilation is done upon initialization
    >>> x = Cfunc(sqr, signature, 123)
    <IGNORE_OUTPUT>
    >>> x.nin # number of input arguments
    1
    >>> x.nout # number of output arguments (must be 1 for now)
    1
    >>> x.sig
    [<type 'int'>, <type 'int'>]

    Attributes:
        f           -- the Python function object
        n           -- id number
        sig         -- signature
        nin         -- number of input arguments
        nout        -- number of output arguments
        cname       -- name of the C function

    Methods:

        decl()      -- returns the C declaration for the function
        cfunc()     -- returns the C function (as string)
        ufunc_support_code()
                    -- generate the C support code to make this
                       function part work with PyUFuncGenericFunction
    """
    def __init__(self, f, signature, n):
        self.f = f
        self.n = n
        self.sig = signature
        self.nin = f.func_code.co_argcount
        self.nout = len(self.sig) - self.nin
        assert self.nout == 1                  # for now
        
        src = translate(f, signature[:self.nin])
        
        self._prefix = 'f%i_' % self.n
        self._allCsrc = src.replace('pypy_', self._prefix + 'pypy_')
        self.cname = self._prefix + 'pypy_g_' + f.__name__

    def cfunc(self):
        p = re.compile(r'^\w+[*\s\w]+' + self.cname +
                       r'\s*\([^)]*\)\s*\{.*?[\n\r]\}[\n\r]',
                       re.DOTALL | re.MULTILINE | re.VERBOSE)
        
        found = p.findall(self._allCsrc)
        assert len(found) == 1
        res = found[0]
        res = res.replace(self._prefix + 'pypy_g_ll_math_ll_math_', '')
        return res + '\n'
    
    def decl(self):
        p = re.compile(r'^\w+[*\s\w]+' + self.cname +
                       r'\s*\([^)]*\);',
                       re.DOTALL | re.MULTILINE | re.VERBOSE)
        
        found = p.findall(self._allCsrc)
        assert len(found) == 1
        return found[0]
    
    def ufunc_support_code(self):
        # Unfortunately the code in here is very hard to read.
        # In order to make the code clearer, one would need a real template
        # engine link Cheetah (http://cheetahtemplate.org/).
        # However, somehting like that would be too much overhead for scipy.
        n = self.n
        nin = self.nin
        cname = self.cname

        def varname(i):
            return chr(i + ord('a'))
        
        declargs = ', '.join('%s %s' % (typedict[self.sig[i]].c, varname(i))
                             for i in xrange(self.nin))
        
        args = ', '.join(varname(i) for i in xrange(self.nin))
        
        isn_steps = '\n\t'.join('npy_intp is%i = steps[%i];' % (i, i)
                                for i in xrange(self.nin))
        
        ipn_args = '\n\t'.join('char *ip%i = args[%i];' % (i, i)
                               for i in xrange(self.nin))
        
        body1d_in = '\n\t\t'.join('%s *in%i = (%s *)ip%i;' %
                                  (2*(typedict[self.sig[i]].c, i))
                                  for i in xrange(self.nin))
        
        body1d_add = '\n\t\t'.join('ip%i += is%i;' % (i, i)
                                   for i in xrange(self.nin))
        
        ptrargs = ', '.join('*in%i' % i for i in xrange(self.nin))
        
        rettype = typedict[self.sig[-1]].c
        
        return '''
static %(rettype)s wrap_%(cname)s(%(declargs)s)
{
	return %(cname)s(%(args)s);
}

typedef %(rettype)s Func_%(n)i(%(declargs)s);

static void
PyUFunc_%(n)i(char **args, npy_intp *dimensions, npy_intp *steps, void *func)
{
	npy_intp i, n;
        %(isn_steps)s
	npy_intp os = steps[%(nin)s];
        %(ipn_args)s
	char *op = args[%(nin)s];
	Func_%(n)i *f = (Func_%(n)i *) func;
	n = dimensions[0];
        
	for(i = 0; i < n; i++) {
		%(body1d_in)s
		%(rettype)s *out = (%(rettype)s *)op;
		
		*out = f(%(ptrargs)s);

                %(body1d_add)s
                op += os;
	}
}
''' % locals()


pypyc = os.path.join(weave.catalog.default_temp_dir(), 'pypy.c')

def write_pypyc(cfuncs):
    """ Given a list of Cfunc instances, write the C code containing the
        functions into a file.
    """
    header = open(os.path.join(os.path.dirname(__file__),
                               'pypy_head.h')).read()
    fo = open(pypyc, 'w')
    fo.write(header)
    fo.write('/********************* end header ********************/\n\n')
    for cf in cfuncs:
        fo.write(cf.cfunc())
    fo.close()


def support_code(cfuncs):
    """ Given a list of Cfunc instances, return the support_code for weave.
    """
    fname = cfuncs[0].f.__name__
    
    declarations = ''.join('\t%s\n' % cf.decl() for cf in cfuncs)
    
    func_support = ''.join(cf.ufunc_support_code() for cf in cfuncs)
    
    pyufuncs = ''.join('\tPyUFunc_%i,\n' % cf.n for cf in cfuncs)
    
    data = ''.join('\t(void *) wrap_%s,\n' % cf.cname for cf in cfuncs)
    
    types = ''.join('\t%s  /* %i */\n' %
                    (''.join(typedict[t].npy + ', ' for t in cf.sig), cf.n)
                    for cf in cfuncs)
    return '''
extern "C" {
%(declarations)s}

%(func_support)s

static PyUFuncGenericFunction %(fname)s_functions[] = {
%(pyufuncs)s};

static void *%(fname)s_data[] = {
%(data)s};

static char %(fname)s_types[] = {
%(types)s};
''' % locals()


def code(f, signatures):
    """ Return the code for weave.
    """
    nin = f.func_code.co_argcount
    ntypes = len(signatures)
    fname = f.__name__
    fhash = func_hash(f)
    
    return '''
import_ufunc();

/****************************************************************************
**  function name: %(fname)s
**  signatures: %(signatures)r
**  fhash: %(fhash)s
*****************************************************************************/

return_val = PyUFunc_FromFuncAndData(
    %(fname)s_functions,
    %(fname)s_data,
    %(fname)s_types,
    %(ntypes)i,      /* ntypes */
    %(nin)i,         /* nin */
    1,               /* nout */
    PyUFunc_None,    /* identity */
    "%(fname)s",     /* name */
    "UFunc created by mkufunc", /* doc */
    0);
''' % locals()


def genufunc(f, signatures):
    """ Return the Ufunc Python object for given function and signatures.
    """
    if len(signatures) == 0:
        raise ValueError("At least one signature needed")
    
    signatures.sort(key=lambda sig: [numpy.dtype(typ).num for typ in sig])
    
    cfuncs = [Cfunc(f, sig, n) for n, sig in enumerate(signatures)]
    
    write_pypyc(cfuncs)
    
    ufunc_info = weave.base_info.custom_info()
    ufunc_info.add_header('"numpy/ufuncobject.h"')
    
    return weave.inline(code(f, signatures),
                        verbose=0,
                        support_code=support_code(cfuncs),
                        customize=ufunc_info,
                        sources=[pypyc])


def mkufunc(arg0=[float]):
    """ The actual API function, for use in decorator function.
    
    """
    class Compile(object):
        
        def __init__(self, f):
            nin = f.func_code.co_argcount
            nout = 1
            for i, sig in enumerate(signatures):
                if isinstance(sig, tuple):
                    pass
                elif sig in typedict.keys():
                    signatures[i] = (nin + nout) * (sig,)
                else:
                    raise TypeError("no match for %r" % sig)
                
            for sig in signatures:
                assert isinstance(sig, tuple)
                if len(sig) != nin + nout:
                    raise TypeError("signature %r does not match the "
                                    "number of args of function %s" %
                                    (sig, f.__name__))
                for t in sig:
                    if t not in typedict.keys():
                        raise TypeError("no match for %r" % t)
            
            self.ufunc = genufunc(f, signatures)
            
        def __call__(self, *args):
            return self.ufunc(*args)
        
    if isinstance(arg0, FunctionType):
        f = arg0
        signatures = [float]
        return Compile(f)
    
    elif isinstance(arg0, list):
        signatures = arg0
        return Compile
    
    elif arg0 in typedict.keys():
        signatures = [arg0]
        return Compile
    
    else:
        raise TypeError("first argument has to be a function, a type, or "
                        "a list of signatures")


if __name__ == '__main__':
    import doctest
    doctest.testmod()
