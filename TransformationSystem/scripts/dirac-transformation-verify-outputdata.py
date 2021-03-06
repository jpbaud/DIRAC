#!/usr/bin/env python
from DIRAC.Core.Base.Script import parseCommandLine
parseCommandLine()
########################################################################
# $HeadURL: svn+ssh://svn.cern.ch/reps/dirac/LHCbDIRAC/trunk/LHCbDIRAC/TransformationSystem/scripts/dirac-transformation-verify-outputdata.py $
########################################################################
__RCSID__ = "$Id: dirac-transformation-verify-outputdata.py 29039 2010-10-05 14:49:58Z acsmith $"

import sys
if len( sys.argv ) < 2:
  print 'Usage: dirac-transformation-verify-outputdata transID [transID] [transID]'
  sys.exit()
else:
  transIDs = [int( arg ) for arg in sys.argv[1:]]

from DIRAC.TransformationSystem.Agent.ValidateOutputDataAgent       import ValidateOutputDataAgent
from DIRAC.TransformationSystem.Client.TransformationClient         import TransformationClient
from DIRAC import gLogger
import DIRAC

agent = ValidateOutputDataAgent( 'Transformation/ValidateOutputDataAgent', 'dirac-transformation-verify-outputdata' )
agent.initialize()

client = TransformationClient()
for transID in transIDs:
  res = client.getTransformationParameters( transID, ['Status'] )
  if not res['OK']:
    gLogger.error( "Failed to determine transformation status" )
    gLogger.error( res['Message'] )
    continue
  status = res['Value']
  if not status in ['ValidatingOutput', 'WaitingIntegrity', 'Active', 'Completed']:
    gLogger.error( "The transformation is in %s status and can not be validated" % status )
    continue
  agent.checkTransformationIntegrity( transID )
