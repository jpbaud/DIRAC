# $HeadURL$
__RCSID__ = "$Id$"

import types
from DIRAC import S_OK, S_ERROR
from DIRAC.Core.Utilities import Time
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC.AccountingSystem.Client.DataStoreClient import gDataStoreClient

class BaseAccountingType:

  __validDataValues = ( types.IntType, types.LongType, types.FloatType, types.LongType )

  def __init__( self ):
    self.keyFieldsList = []
    self.valueFieldsList = []
    self.valuesList = []
    self.fieldsList = []
    self.startTime = 0
    self.endTime = 0
    self.dataTimespan = 0
    self.bucketsLength = [ ( 604800, 3600 ), #<1w = 1h
                           ( 15552000, 86400 ), #>1w <6m = 1d
                           ( 31104000, 604800 ), #>6m = 1w
                         ]
    self.definitionKeyFields = []
    self.definitionAccountingFields = []

  def checkType( self ):
    """
    Check that everything is defined
    """
    if len( self.definitionKeyFields ) == 0:
      raise Exception( "definitionKeyFields has to be filled prior to utilization" )
    if len( self.definitionAccountingFields ) == 0:
      raise Exception( "definitionAccountingFields has to be filled prior to utilization" )
    for key in self.definitionKeyFields:
      self.keyFieldsList.append( key[0] )
    for value in self.definitionAccountingFields:
      self.valueFieldsList.append( value[0] )
    self.fieldsList = []
    self.fieldsList.extend( self.keyFieldsList )
    self.fieldsList.extend( self.valueFieldsList )
    if len( self.valuesList ) != len( self.fieldsList ):
      self.valuesList = [ None for i in self.fieldsList ]

  def getDataTimespan( self ):
    """
    Get the data timespan for the time. Data older than dataTimespan will be deleted
    """
    return self.dataTimespan

  def setStartTime( self, startTime = False ):
    """
    Give a start time for the report
    By default use now
    """
    if not startTime:
      self.startTime = Time.dateTime()
    else:
      self.startTime = startTime

  def setEndTime( self, endTime = False ):
    """
    Give a end time for the report
    By default use now
    """
    if not endTime:
      self.endTime = Time.dateTime()
    else:
      self.endTime = endTime

  def setNowAsStartAndEndTime( self ):
    """
    Set current time as start and end time of the report
    """
    self.startTime = Time.dateTime()
    self.endTime = self.startTime

  def setValueByKey( self, key, value ):
    """
    Add value for key
    """
    if key not in self.fieldsList:
      return S_ERROR( "Key %s is not defined" % key )
    keyPos = self.fieldsList.index( key )
    self.valuesList[ keyPos ] = value
    return S_OK()

  def setValuesFromDict( self, dataDict ):
    """
    Set values from key-value dictionary
    """
    errKeys = []
    for key in dataDict:
      if not key in self.fieldsList:
        errKeys.append( key )
    if errKeys:
      return S_ERROR( "Key(s) %s are not valid" % ", ".join( errKeys ) )
    for key in dataDict:
      self.setValueByKey( key, dataDict[ key ] )
    return S_OK()

  def checkValues( self ):
    """
    Check that all values are defined and valid
    """
    errorList = []
    for i in range( len( self.valuesList ) ):
      key = self.fieldsList[i]
      if self.valuesList[i] == None:
        errorList.append( "no value for %s" % key )
      if key in self.valueFieldsList and type( self.valuesList[i] ) not in self.__validDataValues:
        errorList.append( "value for key %s is not numerical type" % key )
    if errorList:
      return S_ERROR( "Invalid values: %s" % ", ".join( errorList ) )
    if not self.startTime:
      return S_ERROR( "Start time has not been defined" )
    if type( self.startTime ) != Time._dateTimeType:
      return S_ERROR( "Start time is not a datetime object" )
    if not self.endTime:
      return S_ERROR( "End time has not been defined" )
    if type( self.endTime ) != Time._dateTimeType:
      return S_ERROR( "End time is not a datetime object" )
    return S_OK()

  def getDefinition( self ):
    """
    Get a tuple containing type definition
    """
    return ( self.__class__.__name__,
             self.definitionKeyFields,
             self.definitionAccountingFields,
             self.bucketsLength
           )

  def getValues( self ):
    """
    Get a tuple containing report values
    """
    return ( self.__class__.__name__,
             self.startTime,
             self.endTime,
             self.valuesList
           )

  def getContents( self ):
    """
    Get the contents
    """
    cD = {}
    if self.startTime:
      cD[ 'starTime' ] = self.startTime
    if self.endTime:
      cD[ 'endTime' ] = self.endTime
    for iPos in range( len( self.fieldsList ) ):
      if self.valuesList[ iPos ]:
        cD[ self.fieldsList[ iPos ] ] = self.valuesList[ iPos ]
    return cD

  def registerToServer( self ):
    """
    Register type in server
    """
    rpcClient = RPCClient( "Accounting/DataStore" )
    return rpcClient.registerType( *self.getDefinition() )

  def commit( self ):
    """
    Commit register to server
    """
    retVal = gDataStoreClient.addRegister( self )
    if not retVal[ 'OK' ]:
      return retVal
    return gDataStoreClient.commit()

  def remove( self ):
    """
    Remove a register from server
    """
    return gDataStoreClient.remove( self )
