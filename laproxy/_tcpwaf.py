from __future__ import annotations
from typing_extensions import override
from asyncio import wait_for
import re
from logging import getLogger
from ._tcp import TCPHandler
from ._http import HTTPHandler
from ._judge import Judge


FLAG_REGEX = b"[A-Z0-9]{31}="

class SmartTCPHandler(TCPHandler):
    """Handler that tries to filter some malicious traffic automatically"""

    __logger = getLogger("laproxy.SmartTCPHandler")
    judge: Judge | None = None

    @override
    def process(self, packet: bytes, inbound: bool, /) -> bytes | None:
        """Automaticaly inserts into connection history all inbound packets. 
        Most importantly, it sumbits outbound packets containing flags to the Judge"""
        packet = self.standard_processing(packet, inbound)
        if packet is None: return packet

        if inbound:
            self.history.append(packet)
            return packet
        
        try:
            if len(re.findall(FLAG_REGEX, packet)) > 0:
                verdict = SmartTCPHandler.judge.verdict([x for x in self.history])

                if not verdict:
                    packet = None              
                
        finally:
            return packet
    
    def standard_processing(self, packet: bytes, inbound: bool, /) -> bytes | None:
        """Override this to process packets manually"""
        return packet
    
class SmartHTTPHandler(HTTPHandler):
    """Not yet implemented"""
    pass
