# Support blind trust of all certificates; useful for testing

import sys
from array import array

from javax.net.ssl import SSLContext, TrustManager, X509TrustManager
from java.net import URL


__all__ = ["trust_all_certificates"]


# Modified from http://tech.pedersen-live.com/2010/10/trusting-all-certificates-in-jython/

class TrustAllX509TrustManager(X509TrustManager):
    """Define a custom TrustManager which will blindly accept all certificates"""
    def checkClientTrusted(self, chain, auth):
        pass

    def checkServerTrusted(self, chain, auth):
        pass

    def getAcceptedIssuers(self):
        return None


_blind_trust = False

def trust_all_certificates():
    """Blindly trusts all certificates; note this is a per-JVM process setting."""
    global _blind_trust

    if not _blind_trust:
        print >> sys.stderr, "Trusting all certificates without verifying them for this process."
        print >> sys.stderr, "It would be best to install certificates in the JVM's trust store."
        print >> sys.stderr, "Currently there is no way to turn this off."
        trust_managers = array(TrustManager, [TrustAllX509TrustManager()])
        trust_all_context = SSLContext.getInstance("SSL")
        trust_all_context.init(None, trust_managers, None)
        SSLContext.setDefault(trust_all_context)
        _blind_trust = True
