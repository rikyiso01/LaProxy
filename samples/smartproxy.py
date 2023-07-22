from laproxy import SmartTCPHandler, TCPProxy, Judge

if __name__ == "__main__":
    SmartTCPHandler.judge = Judge("insert.your.ip.address", 4444)
    TCPProxy("0.0.0.0", 1234, "container_name", 1237, SmartTCPHandler).run()
