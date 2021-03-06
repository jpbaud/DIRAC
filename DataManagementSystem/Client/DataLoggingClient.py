""" Client for DataLoggingDB
"""
from DIRAC                              import gLogger, S_OK, S_ERROR
from DIRAC.Core.DISET.RPCClient         import RPCClient
from DIRAC.ConfigurationSystem.Client   import PathFinder
import types

class DataLoggingClient:
  """ Client for DataLoggingDB
  """
  def __init__(self,url=False,useCertificates=False):
    """ Constructor of the DataLogging client
    """
    try:
      if not url:
        self.url = PathFinder.getServiceURL('DataManagement/DataLogging')
      else:
        self.url = url
    except Exception, x:
      errStr = "DataLoggingClient.__init__: Exception while obtaining service URL."
      gLogger.exception(errStr,lException=x)

  def addFileRecords(self,fileTuples):
    try:
      client = RPCClient(self.url,timeout=120)
      return client.addFileRecords(fileTuples)
    except Exception, x:
      errStr = "DataLoggingClient.addFileRecords: Exception while adding file records."
      gLogger.exception(errStr,lException=x)
      return S_ERROR(errStr)

  def addFileRecord(self,lfn,status,minor,date,source):
    try:
      client = RPCClient(self.url,timeout=120)
      return client.addFileRecord(lfn,status,minor,date,source)
    except Exception, x:
      errStr = "DataLoggingClient.addFileRecord: Exception while adding file record."
      gLogger.exception(errStr,lException=x)
      return S_ERROR(errStr)