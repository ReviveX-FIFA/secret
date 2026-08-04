
# Mock audioop module for Python 3.13 compatibility
# This provides basic compatibility for discord.py

def add(data, value):
    """Mock add function"""
    return data

def bias(data, value):
    """Mock bias function"""
    return data

def cross(data, value):
    """Mock cross function"""
    return data

def findmax(data, length):
    """Mock findmax function"""
    return 0

def findfit(data, length):
    """Mock findfit function"""
    return 0

def findmaxfit(data, length):
    """Mock findmaxfit function"""
    return 0

def getsample(data, size, index):
    """Mock getsample function"""
    return 0

def lin2adpcm(data, size, state):
    """Mock lin2adpcm function"""
    return data, state

def lin2alaw(data, size):
    """Mock lin2alaw function"""
    return data

def lin2lin(data, size, size2):
    """Mock lin2lin function"""
    return data

def lin2ulaw(data, size):
    """Mock lin2ulaw function"""
    return data

def mul(data, value):
    """Mock mul function"""
    return data

def ratecv(data, width, nchannels, inrate, outrate, state, weightA, weightB):
    """Mock ratecv function"""
    return data, state

def reverse(data, size):
    """Mock reverse function"""
    return data

def rms(data, size):
    """Mock rms function"""
    return 0

def tomono(data, size, fac1, fac2):
    """Mock tomono function"""
    return data

def tostereo(data, size, fac1, fac2):
    """Mock tostereo function"""
    return data

def ulaw2lin(data, size):
    """Mock ulaw2lin function"""
    return data

def adpcm2lin(data, size, state):
    """Mock adpcm2lin function"""
    return data, state

def alaw2lin(data, size):
    """Mock alaw2lin function"""
    return data

def setsample(data, size, index, value):
    """Mock setsample function"""
    return data
