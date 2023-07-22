import sys
from backend import main

if __name__ == "__main__":

    try:
        port = int(sys.argv[1])
    except:
        print("Usage: python3 backend.py <port>")
        sys.exit(1)

    main(port)