#!/usr/bin/env python
########################################################################
# $HeadURL$
# File :    dirac-proxy-init.py
# Author :  Adrian Casajus
########################################################################
__RCSID__ = "$Id$"

import sys
import datetime
import DIRAC
from DIRAC import gLogger, S_OK, S_ERROR
from DIRAC.Core.Base import Script
from DIRAC.FrameworkSystem.Client import ProxyGeneration, ProxyUpload
from DIRAC.Core.Security import X509Chain, ProxyInfo, Properties, VOMS
from DIRAC.ConfigurationSystem.Client.Helpers import Registry

class Params( ProxyGeneration.CLIParams ):

  uploadProxy = False
  uploadPilot = False
  addVOMSExt = False

  def setUploadProxy( self, arg ):
    self.uploadProxy = True
    return S_OK()

  def setUploadPilotProxy( self, arg ):
    self.uploadPilot = True
    return S_OK()

  def addVOMSExt( self, arg ):
    self.addVOMSExt = True
    return S_OK()

  def registerCLISwitches( self ):
    ProxyGeneration.CLIParams.registerCLISwitches( self )
    Script.registerSwitch( "U", "upload", "Upload a long lived proxy to the ProxyManager", self.setUploadProxy )
    Script.registerSwitch( "P", "uploadPilot", "Upload a long lived pilot proxy to the ProxyManager", self.setUploadPilotProxy )
    Script.registerSwitch( "M", "VOMS", "Add voms extension", self.addVOMSExt )

class ProxyInit:

  def __init__( self, piParams ):
    self.__piParams = piParams
    self.__issuerCert = False
    self.__proxyGenerated = False
    self.__uploadedInfo = {}
    self.__proxiesUploaded = []

  def __checkParams( self ):
    #Check if the proxy needs to be uploaded
    if not self.__piParams.uploadProxy:
      self.__piParams.uploadProxy = Registry.getGroupOption( self.__piParams.diracGroup, "AutoUploadProxy", False )
    if self.__piParams.uploadProxy:
      gLogger.verbose( "Proxy will be uploaded to ProxyManager" )

  def getIssuerCert( self ):
    if self.__issuerCert:
      return self.__issuerCert
    proxyChain = X509Chain.X509Chain()
    result = proxyChain.loadChainFromFile( self.__piParams.certLoc )
    if not result[ 'OK' ]:
      gLogger.error( "Could not load the proxy: %s" % result[ 'Message' ] )
      sys.exit( 1 )
    result = proxyChain.getIssuerCert()
    if not result[ 'OK' ]:
      gLogger.error( "Could not load the proxy: %s" % result[ 'Message' ] )
      sys.exit( 1 )
    self.__issuerCert = result[ 'Value' ]
    return self.__issuerCert

  def getPilotGroupsToUpload( self ):
    pilotUpload = Registry.getGroupOption( self.__piParams.diracGroup, "AutoUploadPilotProxy", self.__piParams.uploadPilot )
    if not pilotUpload:
      return []

    issuerCert = self.getIssuerCert()
    userDN = issuerCert.getSubjectDN()[ 'Value' ]

    result = Registry.getGroupsForDN( userDN )
    if not result[ 'OK' ]:
      gLogger.error( "No groups defined for DN %s" % userDN )
      return []
    availableGroups = result[ 'Value' ]

    pilotGroups = []
    for group in availableGroups:
      groupProps = Registry.getPropertiesForGroup( group )
      if Properties.PILOT in groupProps or Properties.GENERIC_PILOT in groupProps:
        pilotGroups.append( group )
    return pilotGroups

  def addVOMSExtIfNeeded( self ):
    addVOMS = Registry.getGroupOption( self.__piParams.diracGroup, "AutoAddVOMS", self.__piParams.addVOMSExt )
    if not addVOMS:
      return

    vomsAttr = Registry.getVOMSAttributeForGroup( self.__piParams.diracGroup )
    if not vomsAttr:
      gLogger.error( "Requested adding a VOMS extension but no VOMS attribute defined for group %s" % self.__piParams.diracGroup )
      return

    result = VOMS.VOMS().setVOMSAttributes( vomsAttr, vo = Registry.getVOForGroup( self.__piParams.diracGroup ) )
    if not result[ 'OK' ]:
      gLogger.error( "Failed adding VOMS attribute:", result[ 'Message' ] )
      return False
    else:
      gLogger.notice( "Added VOMS attribute %s" % vomsAttr )

  def createProxy( self ):
    gLogger.notice( "Generating proxy..." )
    result = ProxyGeneration.generateProxy( piParams )
    if not result[ 'OK' ]:
      gLogger.error( result[ 'Message' ] )
      sys.exit( 1 )
    self.__proxyGenerated = result[ 'Value' ]
    return result

  def uploadProxy( self, userGroup = False ):
    issuerCert = self.getIssuerCert()
    userDN = issuerCert.getSubjectDN()[ 'Value' ]
    if not userGroup:
      userGroup = self.__piParams.diracGroup
    gLogger.notice( "Uploading proxy for %s..." % userGroup )
    if userGroup in self.__proxiesUploaded:
      gLogger.info( "Proxy already uploaded" )
      return S_OK()
    if userDN in self.__uploadedInfo:
      expiry = self.__uploadedInfo[ userDN ].get( userGroup )
      if expiry:
        if issuerCert.getNotAfterDate()[ 'Value' ] - datetime.timedelta( minutes = 10 ) < expiry:
          gLogger.info( "SKipping upload for group %s. Already uploaded" % userGroup )
          return S_OK()
    gLogger.info( "Uploading %s proxy to ProxyManager..." % self.__piParams.diracGroup )
    upParams = ProxyUpload.CLIParams()
    upParams.onTheFly = True
    upParams.proxyLifeTime = issuerCert.getRemainingSecs()[ 'Value' ] - 300
    upParams.diracGroup = userGroup
    for k in ( 'certLoc', 'keyLoc', 'userPasswd' ):
      setattr( upParams, k , getattr( self.__piParams, k ) )

    result = ProxyUpload.uploadProxy( upParams )
    if not result[ 'OK' ]:
      gLogger.error( result[ 'Message' ] )
      sys.exit( 1 )
    self.__uploadedInfo = result[ 'Value' ]
    self.__proxiesUploaded.append( userGroup )
    gLogger.info( "Proxy uploaded" )
    return S_OK()

  def printInfo( self ):
    gLogger.notice( "Proxy generated:" )
    gLogger.notice( ProxyInfo.getProxyInfoAsString( self.__proxyGenerated )[ 'Value' ] )
    if self.__uploadedInfo:
      gLogger.notice( "\nProxies uploaded:" )
      maxDNLen = 0
      maxGroupLen = 0
      for userDN in self.__uploadedInfo:
        maxDNLen = max( maxDNLen, len( userDN ) )
        for group in self.__uploadedInfo[ userDN ]:
          maxGroupLen = max( maxGroupLen, len( group ) )
      gLogger.notice( " %s | %s | Until (GMT)" % ( "DN".ljust( maxDNLen ), "Group".ljust( maxGroupLen ) ) )
      for userDN in self.__uploadedInfo:
        for group in self.__uploadedInfo[ userDN ]:
          gLogger.notice( " %s | %s | %s" % ( userDN.ljust( maxDNLen ),
                                                  group.ljust( maxGroupLen ),
                                                  self.__uploadedInfo[ userDN ][ group ].strftime( "%Y/%m/%d %H:%M" ) ) )



if __name__ == "__main__":
  piParams = Params()
  piParams.registerCLISwitches()

  Script.disableCS()
  Script.parseCommandLine( ignoreErrors = True )

  pI = ProxyInit( piParams )
  result = pI.createProxy()
  if not result[ 'OK' ]:
    gLogger.error( result[ 'Message' ] )
    sys.exit( 1 )

  pI.addVOMSExtIfNeeded()

  if piParams.uploadProxy:
    result = pI.uploadProxy()
    if not result[ 'OK' ]:
      gLogger.error( result[ 'Message' ] )
      sys.exit( 1 )

  for pilotGroup in pI.getPilotGroupsToUpload():
    result = pI.uploadProxy( userGroup = pilotGroup )
    if not result[ 'OK' ]:
      gLogger.error( result[ 'Message' ] )
      sys.exit( 1 )

  pI.printInfo()



  sys.exit( 0 )
