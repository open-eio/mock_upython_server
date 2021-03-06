import time, socket
import mock_machine as machine

DEBUG = False
DEBUG = True

pins = [machine.Pin(i, machine.Pin.IN) for i in (0, 2, 4, 5, 12, 13, 14, 15)]

#here are some mocked test settings
pins[0].value = True  #sets pin "0" to high
pins[3].value = True  #sets pin "5" to high


doc_template = """<!DOCTYPE html>
<html>
    <head> <title>ESP8266 Pins</title> </head>
    <body> <h1>ESP8266 Pins</h1>
        <table border="1"> <tr><th>Pin</th><th>Value</th></tr> %s </table>
    </body>
</html>"""

current_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

headers = ["HTTP/1.1 200 OK",
           "Date: %s" % current_date,
           "Server: Simple-Python-HTTP-Server",
           "Content-Length: {content_length}",  #hold this place with a formatter
           "Content-Type: text/html",
           #"Connection: close",
           ""  #NOTE blank line needed!
           ]

headers = "\r\n".join(headers)

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
try:
    s.bind(addr)
    s.listen(1)
    print('listening on', addr)

    while True:
        cl, addr = s.accept()
        print('client connected from', addr)
        cl_file = cl.makefile('rwb', 0)
        while True:
            line = cl_file.readline()
            if DEBUG:
                print("CLIENT: %s" % line)
            if not line or line == b'\r\n':
                break
        rows = ['<tr><td>%s</td><td>%d</td></tr>' % (str(p), p.value()) for p in pins]
        doc = doc_template % " ".join(rows)
        doc_bytes = bytes(doc,'utf8')
        headers = headers.format(content_length = len(doc_bytes)) #now assign the content's length
        if DEBUG:
            print(repr(headers))
            print(repr(doc))
        cl.send(bytes(headers,'utf8'))
        cl.send(bytes("\r\n",'utf8'))  #IMPORTANT must have a blank line here
        cl.send(doc_bytes)
        cl_file.close()
        cl.close()
finally:
    s.close()
