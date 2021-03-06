""" Clients Invoker is the invoker for commands to be executed on clients
"""

class ClientsInvoker:
  
  def setCommand(self, c):
    """ Set command to c
    """
    self.command = c
    
  def doCommand(self):
    """ Call command.doCommand 
    """
    return self.command.doCommand()